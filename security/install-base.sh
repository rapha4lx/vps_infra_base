#!/usr/bin/env bash
# Baseline packages + SSH fail2ban jail. Does NOT change SSH access or firewall.
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Must run as root" >&2; exit 1; }
[[ -f /etc/debian_version ]] || { echo "Ubuntu/Debian only" >&2; exit 1; }
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends sudo fail2ban python3-systemd openssh-server ufw auditd unattended-upgrades ca-certificates
install -D -m 0644 "$SCRIPT_DIR/fail2ban-sshd.conf" /etc/fail2ban/jail.d/90-vps-panel-sshd.local
fail2ban-client -t
systemctl enable --now fail2ban
systemctl try-restart fail2ban
fail2ban-client status sshd
echo "Installed baseline security packages. No SSH, UFW, sudoers or port settings changed."
echo "IMPORTANT: Firewall/SSH lockdown require separate preflight and verified console/SSH-key access."
