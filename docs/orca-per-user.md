# Orca Remote Server in VPS Control

Official sources:
- https://www.onorca.dev/docs/install
- https://www.onorca.dev/docs/remote-servers
- https://www.onorca.dev/docs/cli/reference
- https://github.com/stablyai/orca/blob/main/docs/reference/headless-linux-server.md

## Multiuser architecture

The Orca application executable is a **host-level prerequisite** installed from the
vendor's official Linux .deb (or a carefully managed AppImage) and is named
`orca-ide`, never `orca` on Linux. Do not install one systemwide desktop
binary independently through npm for each account.

Each selected Linux user has a separate Orca profile, repositories,
agent credentials, runtime, and **systemd --user** service. This matches
the official `orca-ide serve service install --port PORT` flow.

The catalog entry **Orca Remote Server (por usuário)** configures the selected
user's service after the host application is installed. It does **not**
automatically download or install an arbitrary vendor release:
this requires a version-pinned, integrity-verified installer.
The UI job fails clearly when `orca-ide` is missing.

Each UID 1000..9999 gets a unique private service port `20000 + UID`
(e.g. UID 1001 => 21001), not the default 6768. This is a project-specific
assignment and is **not** an Orca official port convention. Inspect existing
listeners before using it. The installer enables `loginctl enable-linger`
and runs Orca's documented per-user service install command as that user.

## Manual first-time binary prerequisite

Install a verified .deb from Orca's official Downloads or tagged GitHub
release, then verify `command -v orca-ide` and `orca-ide --version`.
Do not reuse a download link with an unknown checksum.

In Security > Applications choose Orca, choose the Linux user, preview,
then install. Track progress in **Instalações**. In **Usuários** use
**Orca status** to inspect the individual service.

Verify from shell as the relevant account:
```bash
sudo loginctl user-status alice
sudo -iu alice orca-ide serve service status --json
```

Pairing and account sign-in must be performed securely in the *user's*
context. The official docs describe `orca-ide serve --pairing-address ...`
and `--mobile-pairing` for interactive pairing. Do **not** expose any
per-user runtime port publicly; use a private SSH tunnel or other authenticated
private connection and an address reachable by the client. Pairing tokens
must never be logged or stored by the control panel. Managed Claude/Codex
accounts and other CLIs must also be configured per user on the VPS.

### Not yet supported

Version-pinned binary download, live pairing UI, automatic port conflict
detection, host firewall access, service upgrades, and a zero-downtime
migration/rollback process. Running agent terminals might be interrupted
by restarting Orca; do not reinstall/upgrade an active runtime without
checking for running terminal sessions.

The current privileged panel executor has not completed security isolation
and must be validated only on a disposable test VPS.
