# Global vs per-user software catalog

VPS Control now includes a catalog view in Security. An administrator selects
a tool and, for user-scoped tools, enters target usernames separated by commas.

| Tool | Scope | Mechanism |
| --- | --- | --- |
| Node.js/npm | global | apt packages nodejs npm |
| Podman | global | apt packages podman uidmap slirp4netns |
| Claude Code | selected users | npm -g @anthropic-ai/claude-code under target UID |
| OpenCode | selected users | npm -g @opencode/cli under target UID |
| Antigravity CLI | selected users | planning only; native vendor installer not approved |

Global installation provides binaries on the system PATH. Podman requires
additional rootless per-user setup (subuid/subgid, linger and user services)
to operate automatically after reboot. APT's Node.js version varies by distro;
check supported Node versions before attempting to install CLI agents.

For user-scoped npm installs, the process runs as the target non-root UID,
with `NPM_CONFIG_PREFIX=/home/USER/.local`. Ensure this user directory exists
and `~/.local/bin` is on that account's PATH. Provider logins, API keys and
payment accounts are configured separately by each user; they are never
shared by this catalog.

## Safety and deployment limitations
- All operations accept only exact catalog IDs. Arbitrary package names,
  URLs, shell commands, system paths and root/system accounts are rejected.
- The web service currently runs as root for other legacy host operations.
  This is **not production-safe**; separate a least-privileged executor
  before enabling this administrative interface outside a disposable VM.
- npm package postinstall scripts run as the target account. Review supply
  chain risk; pin versions and package integrity in the production design.
- The installer is synchronous and can time out or hold a request open.
  Later use a queued audited job executor with progress and cancellation.
- This implementation does not enable the Google Antigravity remote
  installer. See official docs for vendor install and authentication.
- Installing Podman globally **does not** automatically enable rootless
  storage, Quadlets or lingering for every Linux user.

Official references:
- https://support.claude.com/en/articles/14552382-your-first-day-in-claude-code
- https://opencode.ai/v2/docs
- https://www.antigravity.google/docs/cli/install/
