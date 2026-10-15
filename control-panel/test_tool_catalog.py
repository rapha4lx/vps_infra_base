import unittest
from unittest.mock import patch
from types import SimpleNamespace
import tool_catalog
import tool_executor

class CatalogTests(unittest.TestCase):
    def test_global_tools(self):
        for tool in ("node","podman"):
            self.assertEqual(tool_catalog.plan(tool,[])["scope"],"global")
            with self.assertRaises(ValueError):
                tool_catalog.plan(tool,["alice"])
    def test_selected_users(self):
        mock=SimpleNamespace(pw_uid=1001,pw_dir="/home/alice",pw_name="alice")
        with patch.object(tool_catalog.pwd,"getpwnam",return_value=mock):
            self.assertEqual(tool_catalog.plan("claude",["alice"])["users"],["alice"])
            self.assertFalse(tool_catalog.plan("antigravity",["alice"])["supported"])
            with self.assertRaises(ValueError):
                tool_catalog.plan("opencode",["alice","alice"])
    def test_reject_system_users(self):
        with patch.object(tool_catalog.pwd,"getpwnam",return_value=SimpleNamespace(
            pw_uid=0,pw_dir="/root")):
            with self.assertRaises(ValueError):
                tool_catalog.plan("claude",["root"])
    def test_exec_uses_user_identity(self):
        account=SimpleNamespace(pw_uid=1001,pw_dir="/home/alice")
        with patch.object(tool_catalog.pwd,"getpwnam",return_value=account):
            with patch.object(tool_executor,"safe_user",return_value=account):
                with patch.object(tool_executor.subprocess,"run") as runner:
                    tool_executor.execute("opencode",["alice"])
        args=runner.call_args.args[0]
        self.assertEqual(args[:4],["/usr/sbin/runuser","-u","alice","--"])
        self.assertNotIn("bash",args)
        self.assertIn("@opencode/cli",args)

if __name__=="__main__":
    unittest.main()
