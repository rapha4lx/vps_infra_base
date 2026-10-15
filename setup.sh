#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run: sudo bash setup.sh" >&2; exit 1; }
[[ -f /etc/debian_version ]] || { echo "Ubuntu/Debian with systemd required" >&2; exit 1; }
cd "$(dirname "$0")"
bash control-panel/install.sh
echo "Panel installed on 127.0.0.1:8083. No Docker networks or legacy services touched."
echo "Grant trusted admin: sudo usermod -aG vps-panel-admins EXISTING_USER"
echo "From workstation: ssh -L 8083:127.0.0.1:8083 EXISTING_USER@VPS"
