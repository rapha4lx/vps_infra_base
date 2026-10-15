"""Validation of requested Traefik HTTP publication. No file writes or side effects."""
import re
from urllib.parse import urlsplit

ROUTER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,62}$")
HOST_RULE = re.compile(r"^Host\(`([a-zA-Z0-9.-]+)`\)$")
DOMAIN = re.compile(r"^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$")


def validate_publication(*, uid, container_id, labels, allowed_suffixes):
    """Translate a restricted subset of docker-style labels to a route intent.

    Endpoint intentionally absent: must be supplied by a trusted host-network
    allocator after firewall and connectivity validation.
    """
    if not isinstance(uid, int) or uid < 1000:
        raise ValueError("Only managed unprivileged users")
    if not isinstance(container_id, str) or not re.fullmatch(r"[0-9a-f]{12,64}", container_id):
        raise ValueError("Invalid container identity")
    if not isinstance(labels, dict) or labels.get("traefik.enable") != "true":
        raise ValueError("Container is not opted in")
    prefix = "traefik.http.routers."
    names = set()
    for key in labels:
        if key.startswith(prefix):
            name = key[len(prefix):].split(".", 1)[0]
            names.add(name)
    if len(names) != 1:
        raise ValueError("Exactly one router required")
    name = names.pop()
    if not ROUTER.fullmatch(name):
        raise ValueError("Invalid router name")
    rp = prefix + name + "."
    allowed_router_keys = {rp + x for x in ("rule", "entrypoints", "tls.certresolver", "service")}
    allowed = {"traefik.enable", "traefik.docker.network"} | allowed_router_keys
    service_prefix = "traefik.http.services."
    ports = {k: v for k,v in labels.items() if k.startswith(service_prefix)}
    if len(ports) != 1:
        raise ValueError("Exactly one service port required")
    portkey, portvalue = next(iter(ports.items()))
    m = re.fullmatch(r"traefik\.http\.services\.([a-zA-Z0-9_-]+)\.loadbalancer\.server\.port", portkey)
    if not m:
        raise ValueError("Only internal service ports allowed")
    service_name = m.group(1)
    if not ROUTER.fullmatch(service_name):
        raise ValueError("Invalid service name")
    if labels.get(rp+"service", service_name) != service_name:
        raise ValueError("Router must reference its local service")
    if set(labels) - (allowed | {portkey}):
        raise ValueError("Unsupported labels")
    rule = labels.get(rp+"rule", "")
    match = HOST_RULE.fullmatch(rule)
    if not match:
        raise ValueError("Only a single literal Host is allowed")
    hostname = match.group(1).lower()
    if not DOMAIN.fullmatch(hostname):
        raise ValueError("Invalid hostname")
    suffixes = tuple("." + suffix.strip(".").lower() for suffix in allowed_suffixes)
    if not suffixes or not any(hostname.endswith(s) for s in suffixes):
        raise ValueError("Domain outside managed zones")
    if labels.get(rp+"entrypoints") != "websecure":
        raise ValueError("Only websecure allowed")
    if labels.get(rp+"tls.certresolver") != "letsencrypt":
        raise ValueError("Only letsencrypt resolver allowed")
    try:
        port = int(portvalue)
    except (ValueError, TypeError):
        raise ValueError("Invalid port") from None
    if str(port) != str(portvalue) or not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    return {
        "id": f"u{uid}-{container_id[:12]}",
        "uid": uid,
        "container_id": container_id,
        "hostname": hostname,
        "container_port": port,
        "router_label": name,
        "status": "awaiting-approved-backend",
    }


def render_file_provider(intent, backend_url):
    """Render a Traefik fragment after an independent trusted backend approval.

    The caller must enforce unique hostname ownership and ensure the backend is
    reachable only from the central Traefik network before writing this output.
    """
    url = urlsplit(backend_url)
    if url.scheme != "http" or not url.hostname or not url.port:
        raise ValueError("Expected approved internal http backend")
    if url.username or url.password or url.path or url.query or url.fragment:
        raise ValueError("Unexpected backend URL fields")
    name = intent["id"]
    return {
        "http": {
            "routers": {name: {
                "rule": "Host(`" + intent["hostname"] + "`)",
                "entryPoints": ["websecure"],
                "tls": {"certResolver": "letsencrypt"},
                "service": name,
            }},
            "services": {name: {
                "loadBalancer": {"servers": [{"url": backend_url}]}
            }}
        }
    }
