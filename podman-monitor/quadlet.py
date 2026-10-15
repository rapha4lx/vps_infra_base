"""Safe Quadlet definition generator for NEW rootless services only."""
import re

NAME = re.compile(r"[a-z][a-z0-9-]{0,47}")
IMAGE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:@-]{0,220}")


def generate_quadlet(*, name, image, port=None, restart=True):
    if not isinstance(name, str) or not NAME.fullmatch(name):
        raise ValueError("Invalid service name")
    if not isinstance(image, str) or not IMAGE.fullmatch(image) or "/" not in image:
        raise ValueError("Use a fully qualified image name")
    # No arbitrary host port mappings. Internal-only workloads are default.
    if port is not None:
        raise ValueError("Direct published ports require admin-approved network allocation")
    lines = [
        "[Unit]", "Description=VPS managed " + name,
        "[Container]", "Image=" + image,
        "ContainerName=vps-" + name,
        "NoNewPrivileges=true",
        "[Service]",
        "Restart=" + ("on-failure" if restart else "no"),
        "RestartSec=5",
        "[Install]", "WantedBy=default.target", "",
    ]
    return "\n".join(lines)
