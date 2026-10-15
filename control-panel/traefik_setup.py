"""Traefik deployment preflight and staging of the approved repository.

Never changes ports, Docker containers or existing deployment on stage.
"""
from pathlib import Path
import shutil
import subprocess

REPO = "https://github.com/rapha4lx/traefik.git"
TARGET = Path("/opt/vps-infra-base/traefik")
SOURCE_BRANCH = "main"


def run(*args, timeout=15):
    return subprocess.run(args, capture_output=True, text=True,
                          timeout=timeout, check=False)


def status():
    docker = shutil.which("docker")
    result = {"docker_installed": bool(docker), "docker_running": False,
              "compose_available": False, "repo_staged": (TARGET / "docker-compose.yml").is_file(),
              "config_ready": (TARGET / ".env").is_file(), "safe_to_launch": False}
    if docker:
        result["docker_running"] = run(docker, "info").returncode == 0
        result["compose_available"] = run(docker, "compose", "version").returncode == 0
    if result["repo_staged"]:
        result["compose_file"] = str(TARGET / "docker-compose.yml")
    result["warning"] = "Staging never exposes ports. Deployment requires manual review of existing services, secrets, ports and firewall."
    return result


def plan():
    return {"repository": REPO, "branch": SOURCE_BRANCH, "directory": str(TARGET),
            "ports_to_review": [80, 443, 8443, 8080, 5433, 5673, 6381],
            "required_secrets": ["LE_EMAIL", "DOMAIN", "DASHBOARD_USERS"],
            "steps": ["Verify Docker Engine and Compose", "Clone into an unused root-owned directory",
                      "Review .env credentials", "Review existing ports and network",
                      "Validate docker compose config", "Deploy with separate approval"],
            "automatically_deploy": False}


def stage():
    info = status()
    if not shutil.which("git"):\n        raise ValueError("Git must be installed before Traefik staging")\n    if not (info["docker_running"] and info["compose_available"]):
        raise ValueError("Docker Engine and Compose must be running first")
    if TARGET.exists():
        raise ValueError("Traefik directory already exists; refusing to overwrite")
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    clone = run("/usr/bin/git", "clone", "--depth", "1", "--branch",
                SOURCE_BRANCH, REPO, str(TARGET), timeout=120)
    if clone.returncode:
        raise RuntimeError("Repository clone failed; check git and network")
    return {"staged": True, "directory": str(TARGET),
            "deployed": False, "next": "Review .env, network and ports before deployment"}
