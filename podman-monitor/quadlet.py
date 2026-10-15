"""Safe Quadlet definition generator for new rootless workloads."""
import re

NAME = re.compile(r"[a-z][a-z0-9-]{0,47}")
IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:@-]{0,220}")


def generate_quadlet(*, name, image, port=None, restart=True, approved_loopback_port=None):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Invalid service name")
    if not isinstance(image, str) or not IMAGE.fullmatch(image) or "/" not in image:
        raise ValueError("Use a fully qualified image name")
    if port is not None and approved_loopback_port is None:
        raise ValueError("Direct published ports require admin-approved network allocation")
    if approved_loopback_port is not None:
        if type(approved_loopback_port) is not int or not 1024 <= approved_loopback_port <= 65535:
            raise ValueError("Invalid approved loopback port")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Internal container port required")
    lines = [
        "[Unit]", "Description=VPS managed " + name,
        "[Container]", "Image=" + image,
        "ContainerName=vps-" + name,
        "NoNewPrivileges=true",
    ]
    if approved_loopback_port is not None:
        lines.append(f"PublishPort=127.0.0.1:{approved_loopback_port}:{port}")
    lines += [
        "[Service]",
        "Restart=" + ("on-failure" if restart else "no"),
        "RestartSec=5",
        "[Install]", "WantedBy=default.target", "",
    ]
    return "\n".join(lines)
