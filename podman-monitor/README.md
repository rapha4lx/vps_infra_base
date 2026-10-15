# Rootless Podman monitor (prototype)

The agent runs once per managed account. It discovers user-owned rootless containers via
`podman ps --all --format json`, watches Podman container events, and reconciles
periodically. It never issues create/start/stop/remove commands, never needs root, and
does not expose Podman sockets.

## Install (Ubuntu/Debian, per managed account)

Administrator:
```sh
sudo install -D -m 0755 podman-monitor/monitor.py /opt/vps-infra-base/podman-monitor/monitor.py
sudo loginctl enable-linger USER
```

As USER, in a valid user systemd session:
```sh
bash podman-monitor/install.sh
systemctl --user daemon-reload
systemctl --user enable --now vps-podman-monitor.service
systemctl --user status vps-podman-monitor.service
```

Inspect `~/.local/state/vps-panel/containers.json`. This is a local cache, not
an access-control boundary. The web panel must not blindly trust these files:
future ingestion must authenticate the account and verify filesystem ownership.

### Limitations
- Discovery only; no adoption automation, Quadlet migration or integrated web UI yet.
- `boot_status=unverified` is intentional, not an assertion that autostart is disabled.
- Event streams vary by Podman version/configuration; periodic scans recover missed events.
- On hosts without a user-session bus, start via a proper systemd user session;
  `sudo -u USER systemctl --user` alone may not work.
- Monitor state is user-controlled and must be treated as untrusted if read centrally.
