# VPS host security baseline

## Safe initial installer

For Ubuntu/Debian, `sudo bash security/install-base.sh` installs
`sudo`, `fail2ban`, `python3-systemd`, `openssh-server`, `ufw`,
`auditd`, `unattended-upgrades` and `ca-certificates`.
It configures a Fail2ban `sshd` jail using the systemd journal and validates
configuration with `fail2ban-client -t`.

**This is not an access-lockdown script**: the baseline does not enable UFW,
change SSH port/authentication, add sudoers rules, or activate automatic upgrades.
Some packages may start systemd services during installation; review apt plans
before applying in production.

## Phase 2: guarded host hardening
- Verify an admin SSH public key login from a **separate connection**, cloud console fallback,
  actual SSH listen port, cloud firewall rules and live sshd effective configuration.
- Write SSH drop-in `PermitRootLogin no`, `PasswordAuthentication no`,
  `KbdInteractiveAuthentication no` only after checking for previous conflicting
  settings and `sshd -t`; verify with `sshd -T` and a second live session.
- Stage UFW/nftables rules with the actual SSH port and Traefik entrypoints
  (80/443; 8443 only if still needed). Respect Docker's separate firewall chain
  handling; blocking ports with UFW alone may **not** block Docker-published ports.
- Block external DB/message ports; keep Traefik API 8080 and panel 8083 loopback
  or access through secure tunnel. Explicit admin approval for extra public ports.
- Constrain sudo through exact-command sudoers policies validated with
  `visudo -cf`, avoid broad NOPASSWD and never automatically grant new users sudo.
- Add audit rules for high-impact account/group/sudoers/sshd modifications and
  controlled log retention. Set per-user Podman resource limits and avoid giving
  container users privileged Docker group membership.
- Optional app-level protection: Traefik rate limiting, middleware auth and a
  dedicated panel auth-failure integration (not solely Fail2ban sshd).
- Ensure automatic security updates are compatible with service availability and
  maintenance/reboot policy. Add monitoring for disk, failed systemd services,
  CPU/memory pressure, certificates and Fail2ban ban events.
- Maintain encrypted off-host backups, restore rehearsals and recovery console.

## Validate initial security state
```sh
sudo fail2ban-client -t
sudo fail2ban-client status sshd
sudo systemctl status fail2ban
sudo ss -lntup
sudo sshd -T | grep -E '^(permitrootlogin|passwordauthentication|kbdinteractiveauthentication)'
```

Do not deploy changes to a VPS without a backup and reliable out-of-band access.
