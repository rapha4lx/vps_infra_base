"""Allowlisted installation plan for global and per-user tools.

No shell pipelines and no remotely downloaded install scripts.
"""
import pwd
import re
import shutil

CATALOG = {
    "node": {"title": "Node.js + npm", "scope": "global", "packages": ["nodejs", "npm"]},
    "docker": {"title": "Docker Engine + Compose (distribuição)", "scope": "global", "packages": ["docker.io", "docker-compose-v2"]},
    "podman": {"title": "Podman rootless", "scope": "global", "packages": ["podman", "uidmap", "slirp4netns"]},
    "claude": {"title": "Claude Code CLI", "scope": "user", "npm": "@anthropic-ai/claude-code"},
    "opencode": {"title": "OpenCode CLI", "scope": "user", "npm": "@opencode/cli"},
    "orca-host": {"title":"Orca IDE (binário oficial verificado)", "scope":"global", "packages":["orca-ide","xvfb"], "managed":"orca-host"},
    "orca": {"title": "Orca Remote Server (por usuário)", "scope": "user", "managed": "orca",
             "details": "Requer binário orca-ide instalado no host. Configura serviço systemd user independente; pareamento feito pelo usuário."},
    "antigravity": {"title": "Google Antigravity CLI", "scope": "user", "manual": True,
                    "details": "Native vendor installer requires review; not executed from admin web UI."},
}
USERNAME = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")


def safe_user(name):
    if not isinstance(name, str) or not USERNAME.fullmatch(name):
        raise ValueError("Invalid username")
    u = pwd.getpwnam(name)
    if u.pw_uid < 1000 or u.pw_uid >= 65534 or u.pw_dir != "/home/" + name or name == "ubuntu":
        raise ValueError("Not a managed regular account")
    return u


def available_tools():
    return [{"id": name, **value} for name,value in CATALOG.items()]


def plan(tool, users):
    if tool not in CATALOG:
        raise ValueError("Unknown catalog tool")
    item = CATALOG[tool]
    if item["scope"] == "global":
        if users:
            raise ValueError("Global install cannot target individual users")
        return {"tool": tool, "scope": "global", "packages": item["packages"],
                "users": [], "approval_required": True, "supported": True}
    if not isinstance(users, list) or not 1 <= len(users) <= 30:
        raise ValueError("Select 1 to 30 users")
    if len(users) != len(set(users)):
        raise ValueError("Duplicate target user")
    for user in users:
        safe_user(user)
    return {"tool": tool, "scope": "user", "users": users,
            "npm": item.get("npm"), "approval_required": True,
            "supported": not item.get("manual", False),
            "message": item.get("details", "User-scoped npm prefix ~/.local; no root npm execution")}
