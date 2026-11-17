import tempfile,unittest
from payloadforge.conflicts import validate_state,validate_resources
from payloadforge.engine import Engine
from test_dependencies import pkg,dep

def res(t,v):return {"type":t,"value":v}
def meta(resources=(),conflicts=(),version="1"):
    return {"version":version,"resources":list(resources),"conflicts":list(conflicts)}
def pack(id,resources=(),conflicts=(),version="1"):
    raw,h,m=pkg(id,version);m.update(schema_version=3,resources=list(resources),conflicts=list(conflicts));return raw,h,m
class ConflictTests(unittest.TestCase):
    def test_port(self):
        with self.assertRaisesRegex(ValueError,"resource conflict"):validate_state({"a":meta([res("tcp",8080)])},{"b":meta([res("tcp",8080)])})
    def test_tcp_udp(self):
        self.assertEqual(validate_state({"a":meta([res("tcp",8080)])},{"b":meta([res("udp",8080)])}),["a","b"])
    def test_path_prefix(self):
        with self.assertRaisesRegex(ValueError,"resource conflict"):validate_state({"a":meta([res("path","/data/demo")])},{"b":meta([res("path","/data/demo/item")])})
    def test_path_siblings(self):
        self.assertEqual(validate_state({"a":meta([res("path","/data/demo")])},{"b":meta([res("path","/data/demo2")])}),["a","b"])
    def test_declared_conflict(self):
        with self.assertRaisesRegex(ValueError,"version conflict"):validate_state({"a":meta(conflicts=[dep("b",">=2")])},{"b":meta(version="2")})
    def test_conflict_version_not_matched(self):
        self.assertEqual(validate_state({"a":meta(conflicts=[dep("b",">=2")])},{"b":meta(version="1")}),["a","b"])
    def test_invalid_resource(self):
        for item in (res("path","/data/../x"),res("path","/system"),res("tcp",0),res("tcp",True),res("udp",65536)):
            with self.subTest(item=item),self.assertRaises(ValueError):validate_resources([item])
    def test_engine_block(self):
        with tempfile.TemporaryDirectory() as d:
            e=Engine(d);e.install(*pack("a",[res("tcp",8080)]))
            with self.assertRaisesRegex(ValueError,"resource conflict"):e.install(*pack("b",[res("tcp",8080)]))
            self.assertEqual(e.status("a")["resources"],[res("tcp",8080)])
    def test_upgrade_own_claim(self):
        with tempfile.TemporaryDirectory() as d:
            e=Engine(d);e.install(*pack("a",[res("tcp",8080)]))
            self.assertEqual(e.install(*pack("a",[res("tcp",8080)],version="2"))["version"],"2")
