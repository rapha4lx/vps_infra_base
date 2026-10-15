import unittest
from gateway import validate_config

VALID={"schema":1,"bridge_cidr":"172.30.85.0/24","listen_ip":"172.30.85.1",
       "traefik_ip":"172.30.85.2","routes":[{"listen_port":20001,"target_port":18001}]}
class Tests(unittest.TestCase):
 def test_valid(self):
  self.assertEqual(validate_config(VALID)[2],[(20001,18001)])
 def test_reject_bad_endpoints(self):
  invalid=[
   {"listen_ip":"0.0.0.0"},
   {"traefik_ip":"10.0.0.1"},
   {"routes":[{"listen_port":20001,"target_port":18001},{"listen_port":20001,"target_port":18002}]},
   {"routes":[{"listen_port":443,"target_port":18001}]},
   {"routes":[{"listen_port":20001,"target_port":18001,"host":"evil"}]},
  ]
  for patch in invalid:
   with self.subTest(patch=patch),self.assertRaises(ValueError):
    validate_config({**VALID,**patch})
if __name__=="__main__":unittest.main()
