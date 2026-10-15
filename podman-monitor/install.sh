#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -u) -eq 0 ]]; then echo "Run as intended rootless user, not root" >&2; exit 1; fi
command -v podman >/dev/null || { echo "podman missing" >&2; exit 1; }
mkdir -p "$HOME/.config/systemd/user" "$HOME/.local/state/vps-panel"
chmod 700 "$HOME/.local/state/vps-panel"
install -m 0644 "$(dirname "$0")/vps-podman-monitor.service" "$HOME/.config/systemd/user/"
echo "Install monitor.py as root to /opt/vps-infra-base/podman-monitor/monitor.py (mode 0755) first."
echo "Then run: systemctl --user daemon-reload && systemctl --user enable --now vps-podman-monitor.service"
echo "An administrator should run: sudo loginctl enable-linger $(id -un)"
