"""Read-only host observability, with bounded subprocesses and no shell."""
import os
import shutil
import subprocess

CATALOG = {
    "podman": ("Podman rootless runtime", "podman"),
    "fail2ban": ("SSH abuse prevention", "fail2ban-client"),
    "sudo": ("Privilege delegation", "sudo"),
    "ufw": ("Firewall management", "ufw"),
    "auditd": ("Kernel audit daemon", "auditctl"),
}

def catalogue():
    return [{"id": key, "description": value[0], "installed": shutil.which(value[1]) is not None}
            for key, value in CATALOG.items()]

def host_metrics():
    def mem():
        with open("/proc/meminfo", encoding="ascii") as f:
            entries = dict((line.split(":")[0], int(line.split(":")[1].split()[0]))
                           for line in f if ":" in line)
        return {"total_kib": entries.get("MemTotal", 0), "available_kib": entries.get("MemAvailable", 0)}
    st = os.statvfs("/")
    return {"loadavg": [round(x, 2) for x in os.getloadavg()],
            "memory": mem(),
            "disk": {"total_bytes": st.f_blocks * st.f_frsize,
                     "free_bytes": st.f_bavail * st.f_frsize}}

def security_status():
    services = {}
    for name in ("fail2ban", "auditd", "ssh"):
        try:
            r = subprocess.run(["/usr/bin/systemctl", "is-active", name],
                               capture_output=True, text=True, timeout=3, check=False)
            services[name] = r.stdout.strip() if r.returncode == 0 else "inactive-or-unknown"
        except (OSError, subprocess.TimeoutExpired):
            services[name] = "unavailable"
    return {"services": services, "firewall": "not-audited",
            "note": "The panel does not certify firewall or SSH hardening."}
