"""Allowlisted administrator tool executor.

Use only in a controlled staging environment until privileged operations are
moved into a separate daemon. Never pass arbitrary commands from the browser.
"""
import os
import subprocess

from tool_catalog import CATALOG, plan, safe_user


def execute(tool, users, progress=None):
    progress = progress or (lambda message: None)
    selection=plan(tool, users)
    if not selection["supported"]:
        raise ValueError("This tool requires a separately reviewed vendor installer")
    common_env={"PATH":"/usr/sbin:/usr/bin:/sbin:/bin","DEBIAN_FRONTEND":"noninteractive"}
    if selection["scope"] == "global":
        packages=CATALOG[tool]["packages"]
        progress("Installing system packages: " + ", ".join(packages))
        subprocess.run(["/usr/bin/apt-get","install","-y","--no-install-recommends",*packages],
                       check=True, capture_output=True, timeout=600, env=common_env)
        progress("Global packages installed")
        return {"tool":tool,"scope":"global","installed":True,"users":"all"}
    results=[]
    for username in users:
        progress("Installing " + tool + " for " + username)
        account=safe_user(username)
        home=account.pw_dir
        # Run npm as the target user, never root. User owns all artifacts.
        env={**common_env,"HOME":home,"USER":username,"LOGNAME":username,
             "NPM_CONFIG_PREFIX":home+"/.local",
             "NPM_CONFIG_CACHE":home+"/.npm"}
        command=["/usr/sbin/runuser","-u",username,"--",
                 "/usr/bin/npm","install","--global",CATALOG[tool]["npm"]]
        subprocess.run(command,check=True,capture_output=True,timeout=600,env=env)
        results.append(username)
        progress("Completed " + username)
    return {"tool":tool,"scope":"user","installed":True,"users":results,
            "bin_path":"~/.local/bin"}
