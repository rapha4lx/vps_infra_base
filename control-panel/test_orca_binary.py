import unittest
from unittest.mock import patch
import orca_binary
import tool_executor

class OrcaBinaryTests(unittest.TestCase):
    def test_pinned_checksums(self):
        self.assertEqual(orca_binary.VERSION,"1.4.226")
        self.assertEqual(set(orca_binary.ASSETS),{"x86_64","aarch64"})
        for arch,digest in orca_binary.ASSETS.values():
            self.assertIn(arch,("amd64","arm64"))
            self.assertEqual(len(digest),64)
            int(digest,16)

    def test_no_redownload_when_installed(self):
        with patch.object(tool_executor.tool_status,"installed",return_value=True):
            with patch.object(orca_binary,"install") as binary:
                result=tool_executor.execute("orca-host",[])
        binary.assert_not_called()
        self.assertTrue(result["already_installed"])

    def test_invalid_arch_rejected_without_network(self):
        with patch.object(orca_binary.platform,"machine",return_value="mips64"):
            with patch.object(orca_binary.urllib.request,"urlopen") as download:
                with self.assertRaises(ValueError):
                    orca_binary.install()
                download.assert_not_called()

if __name__=="__main__":
    unittest.main()
