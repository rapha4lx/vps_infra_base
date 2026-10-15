import unittest
from unittest.mock import patch
from types import SimpleNamespace
import orca_setup
import tool_catalog

class OrcaTests(unittest.TestCase):
    def test_port_isolated_by_uid(self):
        self.assertEqual(orca_setup.port_for(1001),21001)
        self.assertNotEqual(orca_setup.port_for(1001),orca_setup.port_for(1002))
        with self.assertRaises(ValueError):orca_setup.port_for(0)

    def test_orca_selected_user_scope(self):
        user=SimpleNamespace(pw_uid=1001,pw_dir="/home/alice",pw_name="alice")
        with patch.object(tool_catalog.pwd,"getpwnam",return_value=user):
            p=tool_catalog.plan("orca",["alice"])
        self.assertEqual(p["scope"],"user")
        self.assertTrue(p["supported"])
        with self.assertRaises(ValueError):tool_catalog.plan("orca",[])

    def test_missing_binary_fails_closed(self):
        user=SimpleNamespace(pw_uid=1001,pw_dir="/home/alice")
        with patch.object(orca_setup,"safe_user",return_value=user):
            with patch.object(orca_setup.shutil,"which",return_value=None):
                with self.assertRaisesRegex(ValueError,"not installed"):
                    orca_setup.configure("alice")

    def test_service_uses_target_linux_user(self):
        user=SimpleNamespace(pw_uid=1001,pw_dir="/home/alice")
        with patch.object(orca_setup,"safe_user",return_value=user):
            with patch.object(orca_setup.shutil,"which",return_value="/usr/bin/orca-ide"):
                with patch.object(orca_setup.os.path,"isdir",return_value=True):
                    with patch.object(orca_setup.subprocess,"run") as runner:
                        orca_setup.configure("alice")
        cmd=runner.call_args.args[0]
        self.assertEqual(cmd[:4],["/usr/sbin/runuser","-u","alice","--"])
        self.assertIn("21001",cmd)

if __name__=="__main__":unittest.main()
