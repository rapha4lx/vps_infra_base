#!/usr/bin/env bash
set -euo pipefail
if [[ $(id -u) -ne 0 ]]; then echo "Run as root" >&2; exit 1; fi
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-dev libpam0g-dev build-essential
install -d -m 0755 /opt/vps-infra-base/control-panel
cp "$(dirname "$0")/app.py" "$(dirname "$0")/index.html" "$(dirname "$0")/requirements.txt" /opt/vps-infra-base/control-panel/
python3 -m venv /opt/vps-infra-base/control-panel/.venv
/opt/vps-infra-base/control-panel/.venv/bin/pip install --no-cache-dir -r /opt/vps-infra-base/control-panel/requirements.txt
groupadd -f vps-panel-admins
install -m 0644 "$(dirname "$0")/vps-panel.service" /etc/systemd/system/vps-panel.service
systemctl daemon-reload
systemctl enable --now vps-panel
echo "Grant an EXISTING non-root administrator access with: usermod -aG vps-panel-admins USER"
echo "Access through SSH tunnel: ssh -L 8083:127.0.0.1:8083 USER@YOUR_VPS"
