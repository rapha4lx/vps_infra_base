import unittest
from unittest.mock import patch
from types import SimpleNamespace
import tool_status
import tool_executor

class InstalledTests(unittest.TestCase):
    def test_global_all_packages_required(self):
        def fake(args,**kwargs):
            return SimpleNamespace(returncode=0,stdout="install ok installed" if args[-1]!="npm" else "not-installed")
        with patch.object(tool_status,"_run",side_effect=fake):
            self.assertFalse(tool_status.installed("node"))
        with patch.object(tool_status,"_run",return_value=SimpleNamespace(returncode=0,stdout="install ok installed")):
            self.assertTrue(tool_status.installed("node"))

    def test_global_reinstall_skipped(self):
        with patch.object(tool_executor.tool_status,"installed",return_value=True):
            with patch.object(tool_executor.subprocess,"run") as run:
                out=tool_executor.execute("node",[])
        self.assertTrue(out["already_installed"])
        run.assert_not_called()

    def test_per_user_npm_detects_package(self):
        u=SimpleNamespace(pw_dir="/home/alice",pw_uid=1001)
        p=SimpleNamespace(returncode=0,stdout='{"dependencies":{"@anthropic-ai/claude-code":{"version":"1.0.0"}}}')
        with patch.object(tool_status,"safe_user",return_value=u):
            with patch.object(tool_status.shutil,"which",return_value="/usr/bin/npm"):
                with patch.object(tool_status,"_run",return_value=p):
                    self.assertTrue(tool_status.installed("claude","alice"))
                    self.assertFalse(tool_status.installed("opencode","alice"))

if __name__=="__main__": unittest.main()
