"""Narrow Fail2ban SSH jail configuration editor; no arbitrary paths/commands."""
import configparser
import os
from pathlib import Path
import re
import subprocess
import tempfile

JAIL = Path("/etc/fail2ban/jail.d/90-vps-panel-sshd.local")
RETRY = range(2, 11)
BANTIME = re.compile(r"^(?:[1-9][0-9]{0,3})(?:m|h|d)$")
FINDTIME = re.compile(r"^(?:[1-9][0-9]{0,3})(?:m|h)$")


def validate(data):
    if not isinstance(data, dict) or set(data) != {"enabled", "maxretry", "findtime", "bantime"}:
        raise ValueError("Unexpected fields")
    if type(data["enabled"]) is not bool or type(data["maxretry"]) is not int or data["maxretry"] not in RETRY:
        raise ValueError("Invalid jail settings")
    for key, pattern in (("findtime", FINDTIME), ("bantime", BANTIME)):
        if not isinstance(data[key], str) or not pattern.fullmatch(data[key]):
            raise ValueError("Invalid " + key)
    return data


def read():
    p = configparser.ConfigParser(interpolation=None)
    p.read_string("[sshd]\nenabled=true\nmaxretry=5\nfindtime=10m\nbantime=1h\n")
    if JAIL.exists():
        p.read(JAIL)
    return {"enabled": p.getboolean("sshd", "enabled"),
            "maxretry": p.getint("sshd", "maxretry"),
            "findtime": p.get("sshd", "findtime"),
            "bantime": p.get("sshd", "bantime")}


def render(data):
    data = validate(data)
    return ("# Managed by VPS Control; sshd jail only\n[sshd]\n"
            f"enabled = {'true' if data['enabled'] else 'false'}\n"
            "backend = systemd\n"
            f"maxretry = {data['maxretry']}\n"
            f"findtime = {data['findtime']}\n"
            f"bantime = {data['bantime']}\n")


def apply(data):
    contents = render(data)
    if not JAIL.parent.is_dir() or JAIL.is_symlink():
        raise RuntimeError("Unsafe Fail2ban config location")
    previous = JAIL.read_bytes() if JAIL.exists() else None
    if JAIL.exists() and (JAIL.stat().st_uid != 0 or JAIL.stat().st_mode & 0o022):
        raise RuntimeError("Unsafe file permissions")
    fd, name = tempfile.mkstemp(prefix=".vps-jail-", dir=JAIL.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as stream:
            stream.write(contents)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, JAIL)
        subprocess.run(["/usr/bin/fail2ban-client", "-t"], check=True, timeout=15,
                       capture_output=True)
        subprocess.run(["/usr/bin/systemctl", "reload-or-restart", "fail2ban"],
                       check=True, timeout=25, capture_output=True)
    except (OSError, subprocess.SubprocessError):
        if previous is None:
            JAIL.unlink(missing_ok=True)
        else:
            JAIL.write_bytes(previous)
            JAIL.chmod(0o600)
        subprocess.run(["/usr/bin/systemctl", "try-restart", "fail2ban"],
                       timeout=25, check=False, capture_output=True)
        raise RuntimeError("Validation or reload failed; previous file restored")
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return {"updated": True, "jail": "sshd"}
