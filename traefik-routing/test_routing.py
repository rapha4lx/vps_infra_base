import unittest
from routing import validate_publication, render_file_provider

BASE = {
    "traefik.enable": "true",
    "traefik.docker.network": "traefik_proxy",
    "traefik.http.routers.api.rule": "Host(`api.example.com`)",
    "traefik.http.routers.api.entrypoints": "websecure",
    "traefik.http.routers.api.tls.certresolver": "letsencrypt",
    "traefik.http.services.api.loadbalancer.server.port": "9000",
}

def check(labels):
    return validate_publication(uid=1001, container_id="a"*64, labels=labels, allowed_suffixes=["example.com"])

class RoutingTests(unittest.TestCase):
    def test_valid(self):
        route = check(BASE)
        self.assertEqual(route["status"], "awaiting-approved-backend")
        self.assertEqual(route["container_port"], 9000)
        cfg = render_file_provider(route, "http://10.2.0.1:18400")
        self.assertEqual(cfg["http"]["routers"][route["id"]]["entryPoints"], ["websecure"])

    def test_reject_invalid_and_privileged(self):
        changes = [
            {"traefik.http.routers.api.rule": "Host(`evil.net`)"},
            {"traefik.http.routers.api.rule": "HostRegexp(`{host:.+}`)"},
            {"traefik.http.routers.api.middlewares": "dashboard-auth"},
            {"traefik.http.routers.api.entrypoints": "api"},
            {"traefik.http.services.api.loadbalancer.server.port": "0"},
            {"traefik.http.routers.api.service": "api@internal"},
        ]
        for patch in changes:
            with self.subTest(patch=patch), self.assertRaises(ValueError):
                check({**BASE, **patch})
        with self.assertRaises(ValueError):
            validate_publication(uid=0, container_id="a"*64, labels=BASE, allowed_suffixes=["example.com"])

if __name__ == "__main__":
    unittest.main()
