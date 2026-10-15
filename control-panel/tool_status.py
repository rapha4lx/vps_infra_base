"""Actual installation checks, per global package or target Linux account."""
import os
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
        # dpkg state, not executable presence: a binary on PATH may be unrelated.
        for pkg in item["packages"]:
            p=_run(["/usr/bin/dpkg-query","-W","-f=${Status}",pkg])
            if p is None or p.returncode or p.stdout.strip()!="install ok installed":
                return False
        return True
    if not user:return False
    account=safe_user(user)
    if tool=="orca":
        from orca_setup import status
        state=status(user)
        return state.get("configured",False) is True
    if item.get("manual"):return False
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
