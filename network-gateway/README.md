# Private Traefik → Podman bridge prototype

The deployed `rapha4lx/traefik` currently listens publicly on ports 80,
443 and 8443, while 8080 is bound to 127.0.0.1 and is **not** an application
entrypoint. The Docker provider cannot automatically discover rootless Podman
containers owned by other Linux users.

## Proposed data path

Internet :443 → central Traefik (Docker) → dedicated bridge gateway
172.30.85.1:20001 → localhost 127.0.0.1:18001 → Podman rootless workload's
internal port (for example 3000).

In this design, the Podman application publishes **only a host-loopback port**
(127.0.0.1:18001:3000), not a public host port. The privileged allocator
will assign the loopback port and produce the approved Quadlet or Compose
configuration for the user. If a user creates arbitrary Podman containers from
a terminal, labels alone are insufficient: the container has to be adopted or
recreated with a private loopback port before publication.

The gateway listens only on the operator-managed Docker bridge host IP and
accepts connections exclusively from the static Traefik source IP. It never
executes Podman or mounts sockets. This **does not substitute for firewall
rules** and is not intended to be exposed before isolation has been tested.

## Suggested dedicated Docker network (not yet applied)

Create a dedicated network using Docker with a known nonoverlapping subnet
(example 172.30.85.0/24; inspect existing networks to avoid collisions).
Bridge host gateway: 172.30.85.1. Assign Traefik a static IPv4 172.30.85.2
on this dedicated network, in addition to existing `traefik_proxy`.

In the Traefik repository, only after verifying routes and TLS:
- Add the dedicated network to Traefik and mount a new file provider directory
  containing the existing `omnidev.yml` unchanged and generated route fragments.
- Keep Docker provider and `traefik_proxy` for legacy containers.
- Generate route backend `http://172.30.85.1:20001` in File Provider.
- Rootless Podman workload binds host loopback `127.0.0.1:18001`, not 0.0.0.0.
- Operator-managed gateway maps 172.30.85.1:20001 to 127.0.0.1:18001.
- Implement host firewall INPUT rules allowing **only** dedicated Traefik IP
  to bridge relay ports. Explicitly deny other sources, verify no forwarding
  path to user's loopback listener, enforce Docker published-port exceptions,
  and test IPv4/IPv6.
- Pin Traefik's network IP and ensure only the root admin can join or modify
  this network. Rootless users must not be in the docker group.
- Use uid-based quotas and explicit admin approval before adding routes.

## Example gateway configuration (illustrative)

```json
{
 "schema":1,
 "bridge_cidr":"172.30.85.0/24",
 "listen_ip":"172.30.85.1",
 "traefik_ip":"172.30.85.2",
 "routes":[{"listen_port":20001,"target_port":18001}]
}
```

Save as root-owned `/etc/vps-panel/gateway.json`, mode 0600. Run
`python3 network-gateway/gateway.py --config /etc/vps-panel/gateway.json`
only in a test network after firewall checks. This sample is not a deployment
script. Do not use untrusted labels to set `target_port` directly.

## Acceptance checks BEFORE production
1. Traefik container reaches gateway port; unknown Docker containers and
   remote hosts cannot reach it.
2. Podman process is rootless and app port is accessible only at
   127.0.0.1 on the VPS.
3. Validate hostname ownership, backend allocation, firewall and route in one
   auditable transaction; revocation removes route and listener safely.
4. Test WebSockets, long-lived requests, large uploads, timeouts, failures,
   application restarts and reboot without login.
5. Confirm existing Docker routes, ACME challenge, dashboard and 8443 TCP
   routing remain functional.
6. No public app port responds via IPv4 or IPv6.
7. Traefik's Docker socket privilege and bridge firewall isolation receive
   separate security review.
