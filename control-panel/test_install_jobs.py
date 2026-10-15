import tempfile
from pathlib import Path
import time
import unittest
from unittest.mock import patch
import install_jobs

class JobsTests(unittest.TestCase):
    def test_complete_and_persist(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(install_jobs,"ROOT",Path(folder)):
                job=install_jobs.submit("node",[],"admin",lambda t,u,p:p("Installing packages"))
                for _ in range(100):
                    result=install_jobs.get(job["id"])
                    if result["status"] in ("completed","failed"):break
                    time.sleep(.01)
                self.assertEqual(result["status"],"completed")
                self.assertEqual(result["step"],"Installation completed")
                self.assertEqual(install_jobs.list_jobs()[0]["id"],job["id"])

    def test_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(install_jobs,"ROOT",Path(folder)):
                def broken(t,u,p):
                    raise RuntimeError("sensitive details")
                job=install_jobs.submit("podman",[],"admin",broken)
                for _ in range(100):
                    result=install_jobs.get(job["id"])
                    if result["status"] == "failed":break
                    time.sleep(.01)
                self.assertEqual(result["status"],"failed")
                self.assertNotIn("sensitive details",str(result))

    def test_restart_marks_running_as_interrupted(self):
        with tempfile.TemporaryDirectory() as folder:
            with patch.object(install_jobs,"ROOT",Path(folder)):
                install_jobs._save({"id":"job_123","status":"running","created":1,"updated":1})
                install_jobs.mark_interrupted()
                self.assertEqual(install_jobs.get("job_123")["status"],"interrupted")

if __name__=="__main__":
    unittest.main()
