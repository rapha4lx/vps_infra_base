"""Actual installation checks, per global package or target Linux account."""
import os
from pathlib import Path
import shutil
import subprocess
from tool_catalog import CATALOG,safe_user

def _run(args,timeout=12,env=None):
    try:
        return subprocess.run(args,capture_output=True,text=True,timeout=timeout,check=False,env=env)
    except (OSError,subprocess.TimeoutExpired):
        return None

def installed(tool,user=None):
    item=CATALOG[tool]
    if item["scope"]=="global":
        # Accept official/vendor installations too, not only distro package names.
        binaries={"node": ["node","npm"], "podman":["podman"],
                  "docker":["docker"], "orca-host":["orca-ide","Xvfb"]}
        if tool in binaries and all(shutil.which(b) for b in binaries[tool]):
            if tool=="docker":
                p=_run([shutil.which("docker"),"compose","version"])
                return p is not None and p.returncode==0
            return True
        # Otherwise verify distro package status:
        for pkg in item["packages"]:
            p=_run(["/usr/bin/dpkg-query","-W","-f=${Status}",pkg])
            if p is None or p.returncode or p.stdout.strip()!="install ok installed":
                return False
        return True
    if not user:return False
    account=safe_user(user)
    if tool=="orca":
        from orca_setup import status
        try:
            state=status(user)
            return state.get("configured",False) is True
        except (ValueError,OSError,subprocess.SubprocessError):
            return False
    if item.get("manual"):return False
    # Native per-user CLI installs may not be registered in npm.
    # Resolve links and require the executable to remain inside the account HOME.
    binary={"claude":"claude","opencode":"opencode"}.get(tool)
    if binary:
        candidate=Path(account.pw_dir)/".local/bin"/binary
        try:
            target=candidate.resolve(strict=True)
            if target.is_relative_to(Path(account.pw_dir).resolve()) and target.is_file() and target.stat().st_uid==account.pw_uid and bool(target.stat().st_mode & 0o111):
                return True
        except (OSError,ValueError):
            pass
    npm=shutil.which("npm")
    if not npm:return False
    env={"HOME":account.pw_dir,"USER":user,"LOGNAME":user,
         "NPM_CONFIG_PREFIX":account.pw_dir+"/.local",
         "PATH":"/usr/local/bin:/usr/bin:/bin"}
    p=_run(["/usr/sbin/runuser","-u",user,"--",npm,"list","--global","--depth=0","--json"],env=env)
    if p is None:return False
    try:
        import json
        packages=json.loads(p.stdout).get("dependencies",{})
        return item["npm"] in packages
    except (ValueError,KeyError,TypeError):
        return False

def overview(users):
    result=[]
    for key,item in CATALOG.items():
        if item["scope"]=="global":
            result.append({"id":key,"scope":"global","installed":installed(key),"users":[]})
        else:
            result.append({"id":key,"scope":"user","installed":False,
                           "users":[u for u in users if installed(key,u)]})
    return result
