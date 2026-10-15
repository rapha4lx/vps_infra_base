import unittest
from unittest.mock import patch
import session_inventory

class SessionsTests(unittest.TestCase):
    def test_root_logind_is_included(self):
        def fake(*args):
            if args[0] == "loginctl" and args[1] == "list-sessions":
                return "3 0 root seat0 tty1\n4 1000 ubuntu - -"
            if args[0] == "loginctl" and args[1] == "show-session":
                return "Name=root\nUser=0\nService=sshd\nState=active\nRemote=yes\nRemoteHost=10.0.0.1\n"
            return ""
        with patch.object(session_inventory,"_run",side_effect=fake):
            info=session_inventory.host_sessions()
        self.assertEqual(info["logind"][0]["user"],"root")
        self.assertEqual(info["logind"][0]["uid"],"0")

    def test_ssh_process_without_tty(self):
        with patch.object(session_inventory,"_run",side_effect=lambda *args:
            "42 root sshd: root@notty\n" if args[0]=="ps" else ""):
            info=session_inventory.host_sessions()
        self.assertEqual(info["ssh_processes"][0]["owner"],"root")

if __name__=="__main__":
    unittest.main()
