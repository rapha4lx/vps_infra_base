#!/usr/bin/env python3
"""Explicit admin CLI for installing a small allowlist of user-scoped pipx apps.

Deliberately NOT callable from the web API. Requires operator's shell and review.
"""
import argparse
import os
import pwd
import re
import shutil
import subprocess
import sys

ALLOWED = {"httpie": "httpie", "poetry": "poetry", "ansible": "ansible"}
USER_RE = re.compile(r"^[a-z_][a-z0-9_-]{0,30}$")


def plan(user, package):
    if not USER_RE.fullmatch(user) or package not in ALLOWED:
        raise ValueError("Unsupported user or package")
    info = pwd.getpwnam(user)
    if info.pw_uid < 1000 or info.pw_uid >= 65534 or user == "root":
        raise ValueError("Regular users only")
    if info.pw_dir != "/home/" + user or not os.path.isdir(info.pw_dir):
        raise ValueError("Unexpected home directory")
    return ["/usr/sbin/runuser", "-u", user, "--", "/usr/bin/pipx",
            "install", "--", ALLOWED[package]]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--user", required=True)
    parser.add_argument("--app", choices=sorted(ALLOWED), required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Root required for provisioning other users")
    if not shutil.which("pipx"):
        parser.error("Install the global apt package pipx first")
    try:
        cmd = plan(args.user, args.app)
    except (KeyError, ValueError) as exc:
        parser.error(str(exc))
    if not args.apply:
        print("Dry run (run with --apply after review): " + " ".join(cmd))
        return
    subprocess.run(cmd, check=True, timeout=600)


if __name__ == "__main__":
    main()
