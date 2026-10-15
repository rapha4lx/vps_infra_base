"""Generate Traefik dynamic config from explicitly approved routes.

Never accepts arbitrary URLs from Podman labels. Network/firewall provisioning
and endpoint attestation are out of scope; publishing remains fail-closed.
"""
import argparse
import ipaddress
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

from routing import validate_publication, render_file_provider

MAX_MANIFEST = 1_048_576


def load_manifest(path):
    """Trusted admin-owned manifest, never a file writable by application users."""
    path = Path(path)
    st = path.stat()
    if st.st_uid != 0 or (st.st_mode & 0o022):
        raise ValueError("Approval manifest must be root-owned and not group/world writable")
    if st.st_size > MAX_MANIFEST:
        raise ValueError("Manifest exceeds size limit")
    obj = json.loads(path.read_text())
    if obj.get("schema") != 1 or not isinstance(obj.get("routes"), list):
        raise ValueError("Invalid manifest")
    return obj["routes"]


def approved_backend(url, cidr):
    parsed = urlsplit(url)
    if parsed.scheme != "http" or not parsed.hostname or not parsed.port:
        raise ValueError("Only approved HTTP backends")
    if parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
        raise ValueError("Backend URL contains forbidden attributes")
    try:
        addr = ipaddress.ip_address(parsed.hostname)
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        raise ValueError("Backend must use numeric address in managed subnet") from exc
    if addr not in network or addr.is_loopback or addr.is_multicast or addr.is_unspecified:
        raise ValueError("Backend outside dedicated managed subnet")
    return url


def compile_routes(routes, *, allowed_suffixes, backend_cidr):
    """Route approval is exact container ID + UID + hostname + container port."""
    result = {"http": {"routers": {}, "services": {}}}
    domains = set()
    for entry in routes:
        if not isinstance(entry, dict) or entry.get("approved") is not True:
            continue
        if not isinstance(entry.get("uid"), int) or not isinstance(entry.get("labels"), dict):
            raise ValueError("Malformed approved record")
        intent = validate_publication(uid=entry["uid"],
                                      container_id=entry.get("container_id"),
                                      labels=entry["labels"],
                                      allowed_suffixes=allowed_suffixes)
        if (entry.get("hostname") != intent["hostname"]
                or entry.get("container_port") != intent["container_port"]):
            raise ValueError("Approval does not match requested labels")
        if intent["hostname"] in domains:
            raise ValueError("Duplicate hostname: " + intent["hostname"])
        domains.add(intent["hostname"])
        backend = approved_backend(entry.get("backend_url", ""), backend_cidr)
        fragment = render_file_provider(intent, backend)
        for section in ("routers", "services"):
            names = fragment["http"][section]
            if set(names) & set(result["http"][section]):
                raise ValueError("Duplicate generated route ID")
            result["http"][section].update(names)
    return result


def atomic_write(path, result):
    """Only operator-controlled paths. Ensure output dir is root-owned."""
    path = Path(path)
    st = path.parent.stat()
    if st.st_uid != 0 or (st.st_mode & 0o022):
        raise ValueError("Output directory must be root-owned and not writable by others")
    fd, temp = tempfile.mkstemp(prefix=".traefik-", dir=path.parent)
    try:
        os.fchmod(fd, 0o644)
        with os.fdopen(fd, "w") as handle:
            json.dump(result, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", required=True)
    parser.add_argument("--domains", nargs="+", required=True)
    parser.add_argument("--backend-cidr", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--apply", action="store_true",
                        help="Write result only after independently testing network ACLs")
    args = parser.parse_args()
    if os.geteuid() != 0:
        parser.error("Operator-owned configuration requires root")
    result = compile_routes(load_manifest(args.manifest),
                            allowed_suffixes=args.domains,
                            backend_cidr=args.backend_cidr)
    if args.apply:
        atomic_write(args.output, result)
    else:
        print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
