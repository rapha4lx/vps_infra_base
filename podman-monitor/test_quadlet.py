import unittest
from quadlet import generate_quadlet

class QuadletTests(unittest.TestCase):
 def test_boot_enabled_by_default(self):
  out=generate_quadlet(name="web",image="docker.io/library/nginx:alpine")
  self.assertIn("WantedBy=default.target",out)
  self.assertIn("Restart=on-failure",out)
  self.assertNotIn("PublishPort",out)
 def test_reject_host_port(self):
  with self.assertRaises(ValueError):
   generate_quadlet(name="web",image="docker.io/library/nginx:alpine",port=8080)
 def test_approved_private_publication(self):
  out=generate_quadlet(name="web",image="docker.io/library/nginx:alpine",port=80,approved_loopback_port=18001)
  self.assertIn("PublishPort=127.0.0.1:18001:80",out)
  self.assertNotIn("PublishPort=0.0.0.0",out)
 def test_reject_injection(self):
  for name in ("web\n[Service]", "../root","-bad"):
   with self.assertRaises(ValueError):
    generate_quadlet(name=name,image="docker.io/library/nginx:alpine")

if __name__=="__main__": unittest.main()
