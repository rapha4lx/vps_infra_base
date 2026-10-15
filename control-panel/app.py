"""VPS control plane API. Host-only admin daemon; bind to loopback."""
import asyncio
import grp
import json
import os
from pathlib import Path
import pwd
import re
import secrets
import subprocess
import time

import pam
from observability import catalogue, host_metrics, security_status
from session_inventory import host_sessions
import fail2ban_config
import user_lifecycle
import tool_catalog
import tool_executor
from fastapi import Cookie, Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

app = FastAPI(title="VPS Control", docs_url=None, redoc_url=None, openapi_url=None)
ROOT = Path(__file__).resolve().parent
SESSIONS = {}
FAILURES = {}
SESSION_SECONDS = 1800
ACCOUNT = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")
ADMIN_GROUP = "vps-panel-admins"
MAX_LOGIN_ATTEMPTS = 5
FAILURE_WINDOW = 300


def command(*args, timeout=15):
    try:
        return subprocess.run(list(args), check=True, capture_output=True, text=True,
                              timeout=timeout).stdout.strip()
    except (subprocess.SubprocessError, OSError) as exc:
        raise HTTPException(400, "Operation failed; review system journal") from exc


def is_admin(name):
    try:
        info = pwd.getpwnam(name)
        if info.pw_uid < 1000 or name == "root":
            return False
        group = grp.getgrnam(ADMIN_GROUP)
        return name in group.gr_mem or info.pw_gid == group.gr_gid
    except KeyError:
        return False


def current(request: Request, vps_session: str | None = Cookie(default=None)):
    record = SESSIONS.get(vps_session or "")
    if not record or record["expires"] < time.monotonic() or not is_admin(record["user"]):
        if vps_session:
            SESSIONS.pop(vps_session, None)
        raise HTTPException(401, "Authentication required")
    if request.method not in ("GET", "HEAD", "OPTIONS"):
        if not secrets.compare_digest(record["csrf"], request.headers.get("X-CSRF-Token", "")):
            raise HTTPException(403, "Invalid CSRF")
        origin = request.headers.get("origin")
        if origin and origin != str(request.base_url).rstrip("/"):
            raise HTTPException(403, "Invalid origin")
    record["expires"] = time.monotonic() + SESSION_SECONDS
    return record


def require_account(name):
    if not ACCOUNT.fullmatch(name):
        raise HTTPException(422, "Invalid account name")
    return name


class Login(BaseModel):
    user: str = Field(max_length=31)
    password: str = Field(min_length=1, max_length=1024)


class Named(BaseModel):
    name: str


class Member(BaseModel):
    user: str
    group: str


@app.get("/")
def home():
    return FileResponse(ROOT / "index.html", headers={"Cache-Control": "no-store",
        "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' ws:; object-src 'none'; frame-ancestors 'none'",
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer"})


@app.post("/api/login")
def login(body: Login, request: Request, response: Response):
    # With loopback+SSH tunneling all clients share a proxy address: throttle
    # both by submitted user and remotely-observed address, without exposing it.
    ip = request.client.host if request.client else "unknown"
    keys = ("ip:" + ip, "user:" + body.user)
    now = time.monotonic()
    for key in keys:
        FAILURES[key] = [t for t in FAILURES.get(key, []) if now - t < FAILURE_WINDOW]
        if len(FAILURES[key]) >= MAX_LOGIN_ATTEMPTS:
            raise HTTPException(429, "Too many attempts")
    if not is_admin(body.user) or not pam.pam().authenticate(body.user, body.password, service="login"):
        for key in keys:
            FAILURES[key].append(now)
        raise HTTPException(401, "Invalid credentials")
    for key in keys:
        FAILURES.pop(key, None)
    sid, csrf = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
    SESSIONS[sid] = {"user": body.user, "csrf": csrf, "expires": now + SESSION_SECONDS}
    response.set_cookie("vps_session", sid, httponly=True, secure=os.getenv("VPS_PANEL_TLS") == "1",
                        samesite="strict", max_age=SESSION_SECONDS, path="/")
    return {"csrf": csrf}


@app.get("/api/me")
def me(session=Depends(current)):
    return {"user": session["user"], "csrf": session["csrf"]}


@app.post("/api/logout")
def logout(response: Response, request: Request, session=Depends(current)):
    value = request.cookies.get("vps_session")
    SESSIONS.pop(value, None)
    response.delete_cookie("vps_session", path="/")
    return {"ok": True}


@app.get("/api/users")
def users(session=Depends(current)):
    output = []
    for u in pwd.getpwall():
        if u.pw_uid < 1000 or u.pw_name == "nobody":
            continue
        groups = [g.gr_name for g in grp.getgrall() if u.pw_name in g.gr_mem or g.gr_gid == u.pw_gid]
        output.append({"name": u.pw_name, "uid": u.pw_uid, "groups": sorted(set(groups))})
    return output


@app.get("/api/groups")
def groups(session=Depends(current)):
    return [{"name": g.gr_name, "gid": g.gr_gid} for g in grp.getgrall() if g.gr_gid >= 1000]


@app.post("/api/users", status_code=201)
def create_user(body: Named, session=Depends(current)):
    name = require_account(body.name)
    if name == "root":
        raise HTTPException(403, "Reserved")
    command("/usr/sbin/useradd", "--create-home", "--shell", "/bin/bash", "--user-group", name)
    # No password, sudo membership or SSH access is granted automatically.
    command("/usr/sbin/usermod", "--lock", name)
    return {"name": name, "created": True, "password_locked": True}


@app.post("/api/groups", status_code=201)
def create_group(body: Named, session=Depends(current)):
    name = require_account(body.name)
    if not name.startswith("vps-") or name == ADMIN_GROUP:
        raise HTTPException(403, "Only non-privileged vps-* groups may be created")
    command("/usr/sbin/groupadd", name)
    return {"name": name}


@app.post("/api/groups/member")
def add_member(body: Member, session=Depends(current)):
    user, group = require_account(body.user), require_account(body.group)
    if not group.startswith("vps-") or group == ADMIN_GROUP:
        raise HTTPException(403, "Privileged groups require out-of-band approval")
    try:
        info = pwd.getpwnam(user)
        grp.getgrnam(group)
    except KeyError as exc:
        raise HTTPException(404, "Not found") from exc
    if info.pw_uid < 1000:
        raise HTTPException(403, "System account")
    command("/usr/sbin/usermod", "-aG", group, user)
    return {"ok": True}


@app.get("/api/sessions")
def sessions(session=Depends(current)):
    # Never expose session cookies or bearer values.
    return {"panel": [{"user": v["user"], "expires_in": max(0, int(v["expires"]-time.monotonic()))}
                      for v in SESSIONS.values()], "host": host_sessions()}


@app.get("/api/tools")
def tools(session=Depends(current)):
    return catalogue()


@app.post("/api/tools/install")
def install_tool(session=Depends(current)):
    # Installation must be brokered by an audited, separately reviewed executor.
    raise HTTPException(501, "Installer requires approved privileged executor")


@app.get("/api/containers")
def containers(session=Depends(current)):
    # Return discovery cache only; user-controlled cache is untrusted and read-only.
    result = []
    for u in pwd.getpwall():
        if not 1000 <= u.pw_uid < 60000:
            continue
        path = Path(u.pw_dir) / ".local/state/vps-panel/containers.json"
        try:
            if not path.is_file() or path.stat().st_uid != u.pw_uid or path.stat().st_size > 8_000_000:
                continue
            data = json.loads(path.read_text())
            if data.get("schema") != 1 or not isinstance(data.get("containers"), list):
                continue
            result.append({"user": u.pw_name, "uid": u.pw_uid,
                           "containers": data["containers"][:200]})
        except (OSError, ValueError, TypeError):
            continue
    return result


@app.get("/api/metrics")
def metrics(session=Depends(current)):
    return host_metrics()


@app.get("/api/security/status")
def security(session=Depends(current)):
    return security_status()

@app.get("/api/security/setup-guide")
def setup_guide(session=Depends(current)):
    return {
        "baseline_command": "sudo bash security/install-base.sh",
        "baseline_packages": ["sudo", "fail2ban", "ufw", "auditd", "unattended-upgrades"],
        "important": "Firewall and SSH restrictions are intentionally not auto-applied.",
        "checks": ["sudo fail2ban-client status sshd", "sudo sshd -T",
                   "sudo ss -lntup", "sudo ufw status verbose"],
    }


@app.get("/api/tools/install-plan")
def install_plan(user: str, tool: str, session=Depends(current)):
    """Informational plan only; no side effects, no arbitrary command execution."""
    catalog = {
       "pipx": ("pipx", "apt host package; user apps require separate executor"),
       "podman": ("podman uidmap", "rootless runtime requiring per-user provisioning"),
       "git": ("git", "system-wide apt package"),
       "fail2ban": ("fail2ban", "host security package, admin-only"),
    }
    if tool not in catalog:
        raise HTTPException(422, "Unsupported tool")
    try:
        record = pwd.getpwnam(require_account(user))
    except KeyError as exc:
        raise HTTPException(404, "No such user") from exc
    if record.pw_uid < 1000 or record.pw_name == "root":
        raise HTTPException(403, "Cannot target system accounts")
    return {"tool":tool,"target":record.pw_name,"package":catalog[tool][0],
            "description":catalog[tool][1],"executable":False,
            "reason":"Requires privileged audited installer and user-scoped allowlist"}

class Fail2banSettings(BaseModel):
    enabled: bool
    maxretry: int = Field(ge=2, le=10)
    findtime: str = Field(pattern=r"^[1-9][0-9]{0,3}[mh]$")
    bantime: str = Field(pattern=r"^[1-9][0-9]{0,3}[mhd]$")


@app.get("/api/security/fail2ban/config")
def get_fail2ban_config(session=Depends(current)):
    try:
        return fail2ban_config.read()
    except (ValueError, OSError) as exc:
        raise HTTPException(503, "Cannot read Fail2ban configuration") from exc


@app.post("/api/security/fail2ban/config")
def save_fail2ban_config(body: Fail2banSettings, session=Depends(current)):
    try:
        return fail2ban_config.apply(body.model_dump())
    except (ValueError, RuntimeError, OSError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/security/fail2ban/install")
def install_fail2ban(request: Request, session=Depends(current)):
    """Exact, allowlisted package installation; no client-supplied command."""
    if request.headers.get("X-Confirm-Operation") != "install-fail2ban":
        raise HTTPException(400, "Explicit confirmation required")
    try:
        result = subprocess.run(
            ["/usr/bin/apt-get", "install", "-y", "--no-install-recommends",
             "fail2ban", "python3-systemd"], check=True, timeout=240,
            capture_output=True, text=True,
            env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                 "DEBIAN_FRONTEND": "noninteractive"})
        subprocess.run(["/usr/bin/systemctl", "enable", "--now", "fail2ban"],
                       check=True, timeout=30, capture_output=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(500, "Installation failed; review system journal") from exc
    return {"installed": True, "service": "fail2ban"}

class DeleteAccount(BaseModel):
    confirmation: str
    cleanup_home: bool = True


@app.get("/api/users/{name}/delete-preview")
def account_delete_preview(name: str, session=Depends(current)):
    try:
        if name == session["user"]:
            raise HTTPException(403, "Cannot delete your own active admin account")
        return user_lifecycle.preview_delete(name)
    except (ValueError, KeyError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/users/{name}/ssh-key")
def issue_ssh_key(name: str, response: Response, session=Depends(current)):
    try:
        value = user_lifecycle.provision_key(name)
        response.headers["Cache-Control"] = "no-store"
        response.headers["Pragma"] = "no-cache"
        return value
    except (ValueError, KeyError, OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(400, "Could not generate SSH key for this user") from exc


@app.delete("/api/users/{name}")
def remove_account(name: str, body: DeleteAccount, session=Depends(current)):
    if name == session["user"]:
        raise HTTPException(403, "Cannot delete your own active admin account")
    if body.confirmation != "DELETE " + name or body.cleanup_home is not True:
        raise HTTPException(400, "Explicit account and home cleanup confirmation required")
    try:
        return user_lifecycle.delete_user(name)
    except (ValueError, KeyError) as exc:
        raise HTTPException(409, str(exc)) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(500, "Deletion failed: inspect system state before retrying") from exc

class ToolSelection(BaseModel):
    tool: str = Field(min_length=1, max_length=40)
    users: list[str] = Field(default_factory=list, max_length=30)


@app.get("/api/catalog")
def get_catalog(session=Depends(current)):
    return tool_catalog.available_tools()


@app.post("/api/catalog/plan")
def catalog_plan(body: ToolSelection, session=Depends(current)):
    try:
        return tool_catalog.plan(body.tool, body.users)
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/catalog/install")
def catalog_install(body: ToolSelection, request: Request, session=Depends(current)):
    # Explicit confirmation with matching tool. Only fixed catalog operations,
    # never arbitrary package IDs, commands, file paths or URLs.
    if request.headers.get("X-Confirm-Operation") != "install:" + body.tool:
        raise HTTPException(400, "Explicit tool confirmation required")
    try:
        details = tool_catalog.plan(body.tool, body.users)
        if not details["supported"]:
            raise HTTPException(409, "Vendor installation not yet safely supported")
        return tool_executor.execute(body.tool, body.users)
    except (ValueError, KeyError) as exc:
        raise HTTPException(422, str(exc)) from exc
    except (OSError, subprocess.SubprocessError) as exc:
        raise HTTPException(500, "Installation failed; check administrator service logs") from exc
