import unittest
from unittest.mock import patch
import tool_catalog
import traefik_setup

class DockerTraefikTests(unittest.TestCase):
 def test_docker_global(self):
  p=tool_catalog.plan("docker",[])
  self.assertEqual(p["scope"],"global")
  self.assertIn("docker.io",p["packages"])
  with self.assertRaises(ValueError):
   tool_catalog.plan("docker",["alice"])
 def test_traefik_plan_is_non_deploying(self):
  p=traefik_setup.plan()
  self.assertFalse(p["automatically_deploy"])
  self.assertIn(443,p["ports_to_review"])
 def test_stage_will_not_overwrite(self):
  with patch.object(traefik_setup,"status",return_value={"docker_running":True,"compose_available":True}):
   with patch.object(traefik_setup.TARGET.__class__,"exists",return_value=True):
    with self.assertRaisesRegex(ValueError,"already exists"):
     traefik_setup.stage()

if __name__=="__main__":unittest.main()
