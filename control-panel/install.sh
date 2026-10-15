#!/usr/bin/env bash
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run as root" >&2; exit 1; }
[[ -f /etc/debian_version ]] || { echo "Ubuntu/Debian only" >&2; exit 1; }
DIR="$(cd "$(dirname "$0")" && pwd)"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends python3 python3-venv python3-dev libpam0g-dev build-essential
install -d -m 0755 /opt/vps-infra-base/control-panel
for file in app.py observability.py session_inventory.py user_lifecycle.py fail2ban_config.py tool_catalog.py tool_executor.py install_jobs.py orca_setup.py traefik_setup.py index.html requirements.txt; do
  install -m 0644 "$DIR/$file" "/opt/vps-infra-base/control-panel/$file"
done
if [[ ! -x /opt/vps-infra-base/control-panel/.venv/bin/python ]]; then
  python3 -m venv /opt/vps-infra-base/control-panel/.venv
fi
/opt/vps-infra-base/control-panel/.venv/bin/pip install --no-cache-dir -r /opt/vps-infra-base/control-panel/requirements.txt
/opt/vps-infra-base/control-panel/.venv/bin/python -m compileall -q /opt/vps-infra-base/control-panel
groupadd -f vps-panel-admins
install -m 0644 "$DIR/vps-panel.service" /etc/systemd/system/vps-panel.service
systemctl daemon-reload
systemctl enable --now vps-panel
systemctl restart vps-panel
systemctl is-active --quiet vps-panel || { journalctl -u vps-panel -n 40 --no-pager; exit 1; }
echo "Panel listening only at http://127.0.0.1:8083"
echo "Add one EXISTING trusted account to group: usermod -aG vps-panel-admins USER"
echo "Connect with: ssh -L 8083:127.0.0.1:8083 USER@VPS"
