"""Session inventory from logind and process table. No destructive operations."""
import json
import subprocess

def _run(*cmd):
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=4,check=False)
        return p.stdout if p.returncode == 0 else ""
    except (OSError,subprocess.TimeoutExpired):
        return ""

def host_sessions():
    sessions=[]
    for line in _run("loginctl","list-sessions","--no-legend","--no-pager").splitlines():
        parts=line.split()
        if not parts or not parts[0].isdigit():
            continue
        sid=parts[0]
        raw=_run("loginctl","show-session",sid,"--property=Name,User,Remote,RemoteHost,Service,Type,State,Leader,TTY","--no-pager")
        props=dict(row.split("=",1) for row in raw.splitlines() if "=" in row)
        sessions.append({"id":sid,"user":props.get("Name",""),"uid":props.get("User",""),
                         "remote":props.get("Remote",""),"remote_host":props.get("RemoteHost",""),
                         "service":props.get("Service",""),"state":props.get("State",""),
                         "tty":props.get("TTY",""),"leader":props.get("Leader","")})
    # A root SSH tunnel without a PTY may not show in who or loginctl.
    # Present potential sshd connections separately without claiming they are sessions.
    ssh_connections=[]
    for line in _run("ps","-eo","pid=,user=,args=").splitlines():
        parts=line.strip().split(maxsplit=2)
        if len(parts)<3: continue
        pid,user,args=parts
        if args.startswith("sshd:") and "[priv]" not in args and "[net]" not in args:
            ssh_connections.append({"pid":pid,"owner":user,"process":args[:180]})
    return {"logind":sessions,"ssh_processes":ssh_connections,
            "note":"SSH forwarding without a TTY can be absent from logind/who; process entries are indicative only."}
