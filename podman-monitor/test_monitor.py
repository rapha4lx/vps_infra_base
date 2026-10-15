import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).with_name("monitor.py")
spec = importlib.util.spec_from_file_location("vps_monitor", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class MonitorTests(unittest.TestCase):
    def test_inventory_labels_and_no_boot_assumption(self):
        source = [
            {"Id": "b", "Names": ["external"], "Image": "nginx", "State": "running"},
            {"Id": "a", "Names": ["panel"], "Labels": {"io.vps-panel.managed": "true"}},
        ]
        result = module.snapshot(source)
        self.assertEqual([r["id"] for r in result], ["a", "b"])
        self.assertEqual(result[0]["origin"], "panel")
        self.assertEqual(result[1]["origin"], "external")
        self.assertTrue(all(r["boot_status"] == "unverified" for r in result))

    def test_reconcile_writes_inventory(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "containers.json"
            with patch.object(module, "podman_list", return_value=[{"Id": "abc"}]):
                self.assertEqual(module.reconcile(path), 1)
            self.assertEqual(json.loads(path.read_text())["containers"][0]["id"], "abc")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)

    def test_reject_invalid_json_structure(self):
        with patch.object(module.subprocess, "run") as run:
            run.return_value.stdout = "{}"
            with self.assertRaises(ValueError):
                module.podman_list()


if __name__ == "__main__":
    unittest.main()
