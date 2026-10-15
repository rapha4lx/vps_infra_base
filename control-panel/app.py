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
    command("/usr/sbin/groupadd", require_account(body.name))
    return {"name": body.name}


@app.post("/api/groups/member")
def add_member(body: Member, session=Depends(current)):
    user, group = require_account(body.user), require_account(body.group)
    if group in ("root", "sudo", "docker", "adm", "shadow", "systemd-journal", ADMIN_GROUP):
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
                      for v in SESSIONS.values()], "host": command("/usr/bin/who").splitlines()}


@app.get("/api/tools")
def tools(session=Depends(current)):
    return [{"id": "podman", "description": "Podman rootless (admin install only)"},
            {"id": "fail2ban", "description": "Host protection (admin install only)"},
            {"id": "sudo", "description": "Privileged package (admin install only)"}]


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
