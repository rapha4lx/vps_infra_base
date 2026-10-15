import unittest
from unittest.mock import patch
import observability

class ObservabilityTests(unittest.TestCase):
    def test_catalogue(self):
        items=observability.catalogue()
        self.assertIn("podman", {x["id"] for x in items})
        self.assertTrue(all(type(x["installed"]) is bool for x in items))
    def test_metrics_shape(self):
        m=observability.host_metrics()
        self.assertGreater(m["memory"]["total_kib"], 0)
        self.assertGreaterEqual(m["disk"]["total_bytes"], m["disk"]["free_bytes"])
    def test_services_fail_closed(self):
        with patch("observability.subprocess.run", side_effect=OSError):
            s=observability.security_status()
        self.assertEqual(s["services"]["fail2ban"], "unavailable")

if __name__ == "__main__": unittest.main()
