"""Restricted account lifecycle operations used by VPS Control.

WARNING: privileged operations; invoke only from an authenticated admin route.
No arbitrary filesystem paths are accepted from callers.
"""
import os
from pathlib import Path
import pwd
import re
import shutil
import subprocess
import tempfile

NAME = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")
PROTECTED = {"root", "ubuntu", "nobody"}
ADMIN_GROUP = "vps-panel-admins"


def target(name):
    if not isinstance(name, str) or not NAME.fullmatch(name) or name in PROTECTED:
        raise ValueError("Protected or invalid user")
    account = pwd.getpwnam(name)
    if not 1000 <= account.pw_uid < 65534 or account.pw_dir != "/home/" + name:
        raise ValueError("Only ordinary accounts with standard home directories")
    home = Path(account.pw_dir)
    if home.is_symlink() or not home.is_dir() or home.stat().st_uid != account.pw_uid:
        raise ValueError("Untrusted home path")
    return account


def run(*args, timeout=30, check=True):
    return subprocess.run(args, check=check, capture_output=True,
                          text=True, timeout=timeout)


def preview_delete(name):
    user = target(name)
    sessions = run("/usr/bin/loginctl", "list-sessions", "--no-legend",
                   "--no-pager", check=False).stdout
    active = any(parts[2] == name for line in sessions.splitlines()
                 if len(parts := line.split()) >= 3)
    home = Path(user.pw_dir)
    return {"user": name, "uid": user.pw_uid, "home": str(home),
            "active_login_detected": active,
            "removes": ["Linux account", "home directory", "user-specific Podman local storage",
                        "user systemd/Quadlet definitions under home"],
            "not_removed": ["shared storage outside the user's home",
                            "external volumes or remote images", "Traefik routes"],
            "requires_route_review": True}


def delete_user(name):
    details = preview_delete(name)
    if details["active_login_detected"]:
        raise ValueError("Account has an active session; end it before deletion")
    user = target(name)
    # Never delete an account while it still owns running containers/processes.
    probe = run("/usr/bin/pgrep", "-u", str(user.pw_uid), check=False)
    if probe.returncode == 0:
        raise ValueError("User still owns processes; stop services and sessions first")
    if probe.returncode not in (0, 1):
        raise RuntimeError("Could not inspect user processes")
    run("/usr/bin/loginctl", "disable-linger", name, check=False)
    # userdel -r removes home and mail spool, including rootless Podman data under home.
    run("/usr/sbin/userdel", "--remove", name, timeout=60)
    return {"deleted": name, "home_removed": True,
            "warning": "Routes and resources outside the home require separate cleanup"}


def provision_key(name):
    account = target(name)
    ssh = Path(account.pw_dir) / ".ssh"
    if ssh.is_symlink():
        raise ValueError("Unsafe SSH directory")
    ssh.mkdir(mode=0o700, exist_ok=True)
    if ssh.stat().st_uid not in (0, account.pw_uid):
        raise ValueError("SSH directory owned by another user")
    os.chown(ssh, account.pw_uid, account.pw_gid)
    ssh.chmod(0o700)
    authorized = ssh / "authorized_keys"
    if authorized.is_symlink():
        raise ValueError("Unsafe authorized_keys")
    with tempfile.TemporaryDirectory(prefix="vps-ssh-") as tmp:
        private_file = Path(tmp) / "id_ed25519"
        run("/usr/bin/ssh-keygen", "-q", "-t", "ed25519",
            "-C", "vps-" + name, "-N", "", "-f", str(private_file))
        private = private_file.read_text()
        public = (private_file.with_suffix(".pub")).read_text().strip()
        if len(private) > 8192 or not public.startswith("ssh-ed25519 "):
            raise RuntimeError("Invalid generated key")
        # Append using no-follow semantics, with a distinct file descriptor.
        flags = os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(authorized, flags, 0o600)
        try:
            st = os.fstat(fd)
            if st.st_uid not in (0, account.pw_uid) or not __import__("stat").S_ISREG(st.st_mode):
                raise ValueError("Unsafe authorized_keys ownership/type")
            os.fchown(fd, account.pw_uid, account.pw_gid)
            os.fchmod(fd, 0o600)
            os.write(fd, (public + "\n").encode())
            os.fsync(fd)
        finally:
            os.close(fd)
    return {"user": name, "private_key": private, "public_key": public,
            "note": "Save the private key now: it is not retained by the service."}
