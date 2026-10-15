#!/usr/bin/env bash
set -euo pipefail
[[ "$EUID" -eq 0 ]] || { echo "Run: sudo bash setup.sh" >&2; exit 1; }
[[ -f /etc/debian_version ]] || { echo "Ubuntu/Debian with systemd required" >&2; exit 1; }
cd "$(dirname "$0")"

# Count interactive human accounts, not daemon/service accounts.
# On Debian/Ubuntu UID_MIN is usually 1000, but read the configured value.
uid_min="$(awk '$1=="UID_MIN"{print $2;exit}' /etc/login.defs)"
uid_min="${uid_min:-1000}"
mapfile -t humans < <(getent passwd | awk -F: -v min="$uid_min" '
  $3 >= min && $3 < 65534 && $1 != "nobody" && $1 != "ubuntu" && $7 !~ /(nologin|false)$/ { print $1 }
')

if (( ${#humans[@]} == 0 )); then
  echo "No non-ubuntu regular login-capable Linux user found. A first administrator is required."
  [[ -t 0 && -t 1 ]] || { echo "Interactive terminal required to create the first account." >&2; exit 1; }
  while true; do
    read -r -p "New Linux administrator username: " new_user
    if [[ "$new_user" =~ ^[a-z_][a-z0-9_-]{0,30}$ ]] && [[ "$new_user" != root ]] && ! getent passwd "$new_user" >/dev/null; then
      break
    fi
    echo "Invalid username or account already exists."
  done
  while true; do
    read -r -s -p "New Linux user password: " password; echo
    read -r -s -p "Confirm password: " confirm; echo
    if (( ${#password} >= 12 )) && [[ "$password" == "$confirm" ]]; then
      break
    fi
    echo "Passwords must match and contain at least 12 characters."
  done
  unset confirm
  useradd --create-home --shell /bin/bash --user-group "$new_user"
  if ! printf '%s:%s\n' "$new_user" "$password" | chpasswd; then
    passwd -l "$new_user" || true
    echo "Password setup failed; account locked. Resolve manually." >&2
    unset password
    exit 1
  fi
  unset password
  groupadd -f vps-panel-admins
  usermod -aG vps-panel-admins "$new_user"
  echo "Created Linux admin '$new_user' and granted panel administration."
  echo "SSH password login is not enabled by this setup. Configure an SSH public key or use provider console."
else
  printf "Found existing non-ubuntu regular account(s): %s\n" "${humans[*]}"
  echo "No account created. To authorize an existing user: sudo usermod -aG vps-panel-admins USER"
fi

bash control-panel/install.sh
echo "Panel installed on 127.0.0.1:8083; no Docker networks or legacy services touched."
echo "From workstation: ssh -L 8083:127.0.0.1:8083 USER@VPS (SSH key access required)"
