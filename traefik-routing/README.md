# Traefik route approval workflow (prototype, fail-closed)

The existing Traefik in `rapha4lx/traefik` uses Docker provider plus a
single `omnidev.yml` file. This component prepares **additional** dynamic
configuration without rewriting that configuration or opening any network
ports. The deployment/ACL component is **not implemented yet**.

## Inputs
Only an administrator-controlled JSON manifest, root-owned and mode 0640 or
0600, may authorize publication. The user-provided Podman labels are *intent*,
not an authorization decision.

Example (`/etc/vps-panel/routes.json`):

```json
{
  "schema": 1,
  "routes": [
    {
      "approved": true,
      "uid": 1001,
      "container_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
      "hostname": "service.example.com",
      "container_port": 3000,
      "backend_url": "http://10.27.0.12:20001",
      "labels": {
        "traefik.enable": "true",
        "traefik.http.routers.app.rule": "Host(`service.example.com`)",
        "traefik.http.routers.app.entrypoints": "websecure",
        "traefik.http.routers.app.tls.certresolver": "letsencrypt",
        "traefik.http.services.app.loadbalancer.server.port": "3000"
      }
    }
  ]
}
```

Example `backend_url` is **illustrative, not a ready network configuration**.
A separate trusted allocator will verify container ownership, reserve the host
backend port and provision Traefik-only firewall access before setting
`approved=true`. The compiler alone does not provide this verification.

## Dry run
```sh
sudo python3 traefik-routing/reconcile.py \
  --manifest /etc/vps-panel/routes.json \
  --domains example.com \
  --backend-cidr 10.27.0.0/24 \
  --output /var/lib/vps-panel/traefik-routes/panel.json
```

Dry run prints JSON to stdout; nothing is changed. `--apply` writes an
atomic configuration fragment but should **not** be used before independent
backend network validation and Traefik file-provider directory integration.

## Safety invariants
- A route must be preapproved, and match its immutable UID/container ID,
  hostname and target port.
- Hostname must belong to allowed zones; no duplicate hostname within the
  generated manifest. Cross-provider conflict validation still required.
- Backend URL must be an IP inside a dedicated operator-specified subnet.
  This by itself does not guarantee the IP is truly an approved target.
- No socket sharing with rootless Podman, no user-written provider fragments.
- Traefik Docker and existing `omnidev.yml` remain untouched until an
  audited migration and reboot tests in staging.
