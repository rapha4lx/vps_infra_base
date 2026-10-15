"""Orca remote server: per-user systemd service setup after vendor package install.

Port allocations fixed by Linux UID; no public listener/firewall changes here.
"""
import os
import json
import shutil
import subprocess
from tool_catalog import safe_user

def port_for(uid):
    if not 1000 <= uid <= 9999:
        raise ValueError("UID outside managed Orca port range")
    return 20000 + uid

def status(user):
    record=safe_user(user)
    port=port_for(record.pw_uid)
    binary=shutil.which("orca-ide")
    if not binary:
        return {"user":user,"installed":False,"service":"not-configured","port":port,
                "note":"Install official Orca .deb or AppImage with CLI first."}
    result=subprocess.run(["/usr/sbin/runuser","-u",user,"--",binary,"serve","service","status","--json"],
                          capture_output=True,text=True,timeout=12,check=False,
                          env={"HOME":record.pw_dir,"USER":user,"LOGNAME":user,"PATH":"/usr/local/bin:/usr/bin:/bin",
                               "XDG_RUNTIME_DIR":"/run/user/"+str(record.pw_uid)})
    try:
        data=json.loads(result.stdout) if result.returncode==0 else {}
        configured=(data.get("installed") is True or (isinstance(data.get("service"),dict) and data["service"].get("installed") is True)) if isinstance(data,dict) else False
    except (ValueError,TypeError):
        configured=False
    return {"user":user,"installed":True,"configured":configured,"port":port,"service":"queried" if result.returncode==0 else "unavailable",
            "details":result.stdout[:3000] if result.returncode==0 else "",
            "note":"Pairing requires interactive Orca CLI; do not expose runtime port publicly."}

def configure(user, progress=None):
    progress=progress or (lambda _:None)
    record=safe_user(user)
    port=port_for(record.pw_uid)
    binary=shutil.which("orca-ide")
    if not binary:
        raise ValueError("Orca vendor Linux application is not installed; install signed/reviewed .deb first")
    if not shutil.which("Xvfb"):
        raise ValueError("Orca headless requires Xvfb: install xvfb and Electron Linux libraries first")
    if not os.path.isdir("/run/systemd/system"):
        raise ValueError("systemd host required")
    progress("Enable systemd lingering for "+user)
    subprocess.run(["/usr/bin/loginctl","enable-linger",user],check=True,capture_output=True,timeout=15)
    progress("Install Orca per-user service on port "+str(port))
    env={"HOME":record.pw_dir,"USER":user,"LOGNAME":user,
         "XDG_RUNTIME_DIR":"/run/user/"+str(record.pw_uid),
         "PATH":"/usr/local/bin:/usr/bin:/bin"}
    subprocess.run(["/usr/sbin/runuser","-u",user,"--",binary,"serve","service","install",
                    "--port",str(port)],check=True,capture_output=True,timeout=90,env=env)
    progress("Service installed. Pair clients via authenticated private SSH tunnel.")
    return {"user":user,"port":port,"configured":True}
