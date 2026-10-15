"""Private TCP forwarding from a dedicated Docker bridge to rootless Podman loopback.

NOT a public listener. Requires fixed Traefik source IP and host firewall rules,
validated before activation. Intended to be run as a locked-down systemd service.
"""
import asyncio
import ipaddress
import json
from pathlib import Path

MAX_CONFIG_BYTES = 65536

def validate_config(data):
    if data.get("schema") != 1:
        raise ValueError("Unsupported schema")
    network = ipaddress.ip_network(data["bridge_cidr"], strict=True)
    if not isinstance(network, ipaddress.IPv4Network) or network.prefixlen < 24:
        raise ValueError("Dedicated bridge subnet required (at least /24)")
    bind = ipaddress.ip_address(data["listen_ip"])
    source = ipaddress.ip_address(data["traefik_ip"])
    if bind not in network or source not in network or bind == source:
        raise ValueError("Invalid bridge addresses")
    if bind.is_loopback or bind.is_unspecified or bind.is_multicast:
        raise ValueError("Invalid bind address")
    routes = data.get("routes")
    if not isinstance(routes, list) or len(routes) > 128:
        raise ValueError("Invalid routes")
    result = []
    used = set()
    for route in routes:
        if not isinstance(route, dict) or set(route) != {"listen_port", "target_port"}:
            raise ValueError("Invalid route attributes")
        a, b = route["listen_port"], route["target_port"]
        if type(a) is not int or type(b) is not int or not 1024 <= a <= 65535 or not 1024 <= b <= 65535:
            raise ValueError("Unprivileged ports only")
        if a in used:
            raise ValueError("Duplicate gateway port")
        used.add(a)
        result.append((a, b))
    return str(bind), str(source), result


async def relay(reader, writer, target_port):
    peer = writer.get_extra_info("peername")
    try:
        upstream_reader, upstream_writer = await asyncio.wait_for(
            asyncio.open_connection("127.0.0.1", target_port), timeout=5
        )
        async def pump(src, dest):
            try:
                while data := await src.read(65536):
                    dest.write(data)
                    await dest.drain()
            finally:
                if dest.can_write_eof():
                    dest.write_eof()
        tasks = [asyncio.create_task(pump(reader, upstream_writer)),
                 asyncio.create_task(pump(upstream_reader, writer))]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
    except (OSError, asyncio.TimeoutError):
        pass
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except OSError:
            pass
        if "upstream_writer" in locals():
            upstream_writer.close()
            await upstream_writer.wait_closed()


async def serve(data):
    bind, allowed, routes = validate_config(data)
    servers = []
    try:
        for listen_port, target_port in routes:
            async def accept(reader, writer, p=target_port):
                peer = writer.get_extra_info("peername")
                if not peer or peer[0] != allowed:
                    writer.close()
                    await writer.wait_closed()
                    return
                await relay(reader, writer, p)
            servers.append(await asyncio.start_server(accept, bind, listen_port))
        await asyncio.gather(*(server.serve_forever() for server in servers))
    finally:
        for server in servers:
            server.close()
        await asyncio.gather(*(server.wait_closed() for server in servers))


def main():
    import argparse
    import os
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    path = Path(args.config)
    st = path.stat()
    if st.st_uid != 0 or st.st_mode & 0o022 or st.st_size > MAX_CONFIG_BYTES:
        parser.error("Configuration must be trusted, root-owned, mode 0640 or stricter")
    data = json.loads(path.read_text())
    asyncio.run(serve(data))

if __name__ == "__main__":
    main()
