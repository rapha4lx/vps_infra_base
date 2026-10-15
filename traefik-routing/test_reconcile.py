import unittest
from reconcile import compile_routes

LABELS = {
 "traefik.enable":"true",
 "traefik.http.routers.app.rule":"Host(`service.example.com`)",
 "traefik.http.routers.app.entrypoints":"websecure",
 "traefik.http.routers.app.tls.certresolver":"letsencrypt",
 "traefik.http.services.app.loadbalancer.server.port":"3000",
}
ENTRY={"approved":True,"uid":1001,"container_id":"a"*64,"labels":LABELS,
       "hostname":"service.example.com","container_port":3000,
       "backend_url":"http://10.27.0.12:20001"}

def compile_(*routes):
 return compile_routes(list(routes),allowed_suffixes=["example.com"],
                       backend_cidr="10.27.0.0/24")

class Tests(unittest.TestCase):
 def test_approved(self):
  got=compile_(ENTRY)
  self.assertIn("u1001-aaaaaaaaaaaa",got["http"]["routers"])
 def test_pending_omitted(self):
  self.assertEqual(compile_({**ENTRY,"approved":False})["http"]["routers"],{})
 def test_domain_conflict(self):
  with self.assertRaisesRegex(ValueError,"Duplicate hostname"):
   compile_(ENTRY,{**ENTRY,"uid":1002,"container_id":"b"*64})
 def test_approval_mutation(self):
  with self.assertRaisesRegex(ValueError,"Approval does not match"):
   compile_({**ENTRY,"container_port":1234})
 def test_arbitrary_endpoint_rejected(self):
  for endpoint in ("http://127.0.0.1:3000","http://169.254.169.254:80",
                   "http://10.27.0.12:20001/admin","http://evil.com:3000"):
   with self.subTest(endpoint=endpoint),self.assertRaises(ValueError):
    compile_({**ENTRY,"backend_url":endpoint})
 def test_unsupported_labels(self):
  with self.assertRaises(ValueError):
   compile_({**ENTRY,"labels":{**LABELS,"traefik.http.routers.app.middlewares":"bad"}})

if __name__=="__main__":
 unittest.main()
