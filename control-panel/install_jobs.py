"""Bounded persistent job history and progress for allowlisted installs."""
import json
import os
from pathlib import Path
import secrets
import threading
import time

ROOT=Path("/var/lib/vps-panel/jobs")
LOCK=threading.RLock()
MAX_JOBS=100
TERMINAL={"completed","failed","interrupted"}

def _save(job):
    ROOT.mkdir(mode=0o700,parents=True,exist_ok=True)
    p=ROOT/(job["id"]+".json")
    tmp=p.with_suffix(".tmp")
    with open(tmp,"w") as f:
        os.fchmod(f.fileno(),0o600)
        json.dump(job,f)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp,p)

def _load():
    if not ROOT.exists(): return []
    items=[]
    for p in ROOT.glob("*.json"):
        try:
            if not p.name.startswith("job_") or p.stat().st_size>32768:continue
            data=json.loads(p.read_text())
            if isinstance(data,dict) and data.get("id")==p.stem:items.append(data)
        except (OSError,ValueError):continue
    return sorted(items,key=lambda d:d.get("created",0),reverse=True)[:MAX_JOBS]

def list_jobs():
    with LOCK:return _load()

def get(job_id):
    if not job_id.startswith("job_") or len(job_id)>100:raise ValueError("Bad job ID")
    return next((j for j in list_jobs() if j["id"]==job_id),None)

def submit(tool,users,actor,runner):
    with LOCK:
        if sum(j["status"] in ("queued","running") for j in _load())>=2:
            raise ValueError("Maximum concurrent installations reached")
        job={"id":"job_"+secrets.token_hex(12),"tool":tool,"users":users,
             "actor":actor,"status":"queued","step":"Awaiting worker",
             "created":time.time(),"updated":time.time(),"error":None}
        _save(job)
    def worker():
        def progress(message):
            with LOCK:
                job["step"]=str(message)[:160]
                job["updated"]=time.time()
                _save(job)
        try:
            with LOCK:
                job["status"]="running";_save(job)
            runner(tool,users,progress)
            with LOCK:job["status"]="completed";job["step"]="Installation completed"
        except Exception as exc:
            with LOCK:
                job["status"]="failed";job["error"]=type(exc).__name__
                job["step"]="Installation failed. Review server journal."
        finally:
            with LOCK:
                job["updated"]=time.time();_save(job)
    threading.Thread(target=worker,name=job["id"],daemon=True).start()
    return job

def mark_interrupted():
    with LOCK:
        for job in _load():
            if job["status"] in ("queued","running"):
                job["status"]="interrupted";job["step"]="Panel restarted while this job was running"
                job["updated"]=time.time();_save(job)
