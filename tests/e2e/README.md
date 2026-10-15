# Integration tests

`bash tests/e2e/smoke.sh` starts a disposable Traefik v3.7 and nginx
backend and checks TLS entrypoint routing with Host(app.test), plus rejection
of an unknown domain. It does not require the private Traefik repository
or the production VPS.

**Scope**: Traefik File Provider and proxy-to-backend path only. The backend
is a Docker Compose fixture, **not Podman rootless**. This check does not
verify the host bridge gateway, nftables, account isolation, certificate
issuance, auto-restart at boot or the production settings in rapha4lx/traefik.
Those require separate privileged integration tests on a disposable Ubuntu/
Debian VM with systemd, Docker, Podman and reboot support.
