#!/usr/bin/env bash
# Configure an existing unprivileged Linux account for persistent rootless Podman.
set -euo pipefail
if [[ $EUID -ne 0 || $# -ne 1 ]]; then
  echo "Usage: sudo bash provision-user.sh USER" >&2; exit 2
fi
user="$1"
[[ "$user" =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] || { echo "Bad username" >&2; exit 2; }
uid="$(id -u "$user")"
[[ "$uid" -ge 1000 && "$uid" -lt 60000 ]] || { echo "Only regular users" >&2; exit 2; }
home="$(getent passwd "$user" | cut -d: -f6)"
[[ -d "$home" && "$home" == /home/* ]] || { echo "Unexpected home directory" >&2; exit 2; }
command -v podman >/dev/null || { echo "Install podman first (apt install podman uidmap)" >&2; exit 1; }
if ! grep -qE "^$user:[0-9]+:[0-9]+$" /etc/subuid; then
  echo "No /etc/subuid range for $user; configure non-overlapping subuids first" >&2; exit 1
fi
if ! grep -qE "^$user:[0-9]+:[0-9]+$" /etc/subgid; then
  echo "No /etc/subgid range for $user; configure non-overlapping subgids first" >&2; exit 1
fi
loginctl enable-linger "$user"
install -d -m 0700 -o "$user" -g "$(id -gn "$user")" "$home/.config" "$home/.config/systemd" "$home/.config/systemd/user" "$home/.config/containers" "$home/.config/containers/systemd" "$home/.local" "$home/.local/state" "$home/.local/state/vps-panel"
echo "Linger enabled for $user; user Quadlets in $home/.config/containers/systemd"
echo "Systemd user manager starts after boot; each Quadlet must have [Install] WantedBy=default.target."
echo "Start a proper user session to enable the per-user monitor; do not run Podman as root."
