import unittest
from unittest.mock import patch
from types import SimpleNamespace
import user_lifecycle

class UserLifecycleTests(unittest.TestCase):
    def test_protected_account_rejected(self):
        for name in ("root", "ubuntu", "nobody", "../root", "user;rm"):
            with self.subTest(name=name), self.assertRaises(ValueError):
                user_lifecycle.target(name)

    def test_preview_blocks_active_user(self):
        account=SimpleNamespace(pw_uid=1001,pw_dir="/home/alice",pw_name="alice")
        with patch.object(user_lifecycle,"target",return_value=account):
            with patch.object(user_lifecycle,"run",return_value=SimpleNamespace(stdout="7 1001 alice - pts/0",returncode=0)):
                result=user_lifecycle.preview_delete("alice")
        self.assertTrue(result["active_login_detected"])
        self.assertIn("Traefik routes", result["not_removed"])

    def test_deletion_does_not_kill_processes(self):
        with patch.object(user_lifecycle,"preview_delete",return_value={"active_login_detected":False}):
            with patch.object(user_lifecycle,"target",return_value=SimpleNamespace(pw_uid=1001)):
                with patch.object(user_lifecycle,"run",return_value=SimpleNamespace(returncode=0)) as run:
                    with self.assertRaisesRegex(ValueError,"processes"):
                        user_lifecycle.delete_user("alice")
                    self.assertEqual(run.call_count,1)

if __name__=="__main__":
    unittest.main()
