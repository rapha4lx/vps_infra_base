#!/usr/bin/env python3
"""Rootless per-user Podman discovery agent. Read-only: never modifies containers."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time

INTERVAL = 60
MAX_BYTES = 8 * 1024 * 1024


def podman_list():
    result = subprocess.run(
        ["podman", "ps", "--all", "--format", "json"],
        capture_output=True, text=True, timeout=30, check=True,
    )
    if len(result.stdout) > MAX_BYTES:
        raise ValueError("Podman inventory exceeds size limit")
    data = json.loads(result.stdout)
    if not isinstance(data, list):
        raise ValueError("Unexpected Podman output")
    return data


def snapshot(rows):
    """Do not infer boot status from --restart: systemd boot wiring is distinct."""
    out = []
    for item in rows:
        cid = item.get("Id") or item.get("ID") or ""
        if not isinstance(cid, str) or not cid:
            continue
        labels = item.get("Labels") or {}
        if not isinstance(labels, dict):
            labels = {}
        out.append({
            "id": cid,
            "name": (item.get("Names") or [""])[0] if isinstance(item.get("Names"), list)
                else (item.get("Names") or ""),
            "image": item.get("Image", ""),
            "state": item.get("State") or item.get("Status") or "unknown",
            "created": item.get("CreatedAt") or item.get("Created") or "",
            "origin": "panel" if labels.get("io.vps-panel.managed") == "true" else "external",
            "boot_status": "unverified",
        })
    return sorted(out, key=lambda x: x["id"])


def atomic_save(path, data):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".inventory-", text=True)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"schema": 1, "updated_at": time.time(), "containers": data}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def reconcile(path):
    items = snapshot(podman_list())
    atomic_save(path, items)
    return len(items)


def watch(path, stop=None, interval=INTERVAL):
    """Events trigger reconciliation. Polling repairs missed events."""
    stop = stop or threading.Event()
    last = 0.0
    process = None
    try:
        while not stop.is_set():
            now = time.monotonic()
            if now - last >= interval:
                try:
                    reconcile(path)
                except (OSError, ValueError, subprocess.SubprocessError) as exc:
                    print(f"reconcile failed: {exc}", flush=True)
                last = now
            if process is None or process.poll() is not None:
                if process is not None:
                    process.stdout.close()
                    process.wait()
                try:
                    process = subprocess.Popen(
                        ["podman", "events", "--filter", "type=container",
                         "--format", "json", "--stream=true"],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                        text=True, bufsize=1,
                    )
                except OSError as exc:
                    print(f"events unavailable: {exc}", flush=True)
                    process = None
                # Polling continues even when event stream is unavailable.
            # Event reading lives in a helper thread to avoid blocking periodic scan.
            if process is not None and not getattr(process, "_reader_started", False):
                def reader(proc):
                    try:
                        for line in proc.stdout:
                            if stop.is_set():
                                break
                            try:
                                evt = json.loads(line)
                                if evt.get("Type", "").lower() == "container":
                                    reconcile(path)
                            except (ValueError, OSError, subprocess.SubprocessError) as exc:
                                print(f"event scan failed: {exc}", flush=True)
                    finally:
                        pass
                threading.Thread(target=reader, args=(process,), daemon=True).start()
                process._reader_started = True
            stop.wait(min(5, interval))
    finally:
        if process is not None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=INTERVAL)
    args = parser.parse_args()
    if os.geteuid() == 0:
        parser.error("Run as the Podman rootless user, never as root")
    if args.interval < 5:
        parser.error("--interval must be at least 5 seconds")
    path = Path.home() / ".local/state/vps-panel/containers.json"
    if args.once:
        print(f"Discovered {reconcile(path)} containers; {path}")
    else:
        watch(path, interval=args.interval)


if __name__ == "__main__":
    main()
