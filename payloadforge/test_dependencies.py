import tempfile,unittest
from payloadforge.dependencies import dependency_order,satisfies
from payloadforge.engine import Engine
from test_engine import package

def dep(id,constraint="*"):return {"id":id,"constraint":constraint}
def meta(version="1.0.0",deps=()):return {"version":version,"dependencies":list(deps)}
def pkg(id,version,deps=()):
    raw,h,m=package(version,[("a.txt",b"data","replace-with-backup")])
    m.update(schema_version=2,id=id,dependencies=list(deps))
    return raw,h,m

class DependencyTests(unittest.TestCase):
    def test_comparisons(self):
        self.assertTrue(satisfies("v1.4",">=1.2,<2"))
        self.assertFalse(satisfies("v2",">=1.2,<2"))
    def test_prerelease(self):
        self.assertTrue(satisfies("1.0.0-beta.2","<1.0.0"))
        self.assertTrue(satisfies("1.0.0-beta.10",">1.0.0-beta.2"))
    def test_unknown_operator(self):
        with self.assertRaises(ValueError):satisfies("1","^1")
    def test_order(self):
        self.assertEqual(dependency_order({},{"a":meta(deps=[dep("b")]),"b":meta(deps=[dep("c")]),"c":meta()}),["c","b","a"])
    def test_missing(self):
        with self.assertRaisesRegex(ValueError,"missing dependency"):dependency_order({},{"a":meta(deps=[dep("b")])})
    def test_cycle(self):
        with self.assertRaisesRegex(ValueError,"cycle"):dependency_order({},{"a":meta(deps=[dep("b")]),"b":meta(deps=[dep("a")])})
    def test_self_cycle(self):
        with self.assertRaisesRegex(ValueError,"cycle"):dependency_order({},{"a":meta(deps=[dep("a")])})
    def test_reverse_dependency(self):
        with self.assertRaisesRegex(ValueError,"incompatible"):dependency_order({"a":meta(deps=[dep("b","<2")]),"b":meta()},{"b":meta("2")})
    def test_duplicate_dep(self):
        with self.assertRaises(ValueError):dependency_order({},{"a":meta(deps=[dep("b"),dep("b")]),"b":meta()})
    def test_install_dependency(self):
        with tempfile.TemporaryDirectory() as d:
            e=Engine(d)
            with self.assertRaisesRegex(ValueError,"missing dependency"):e.install(*pkg("a","1",[dep("b",">=1,<2")]))
            e.install(*pkg("b","1"))
            s=e.install(*pkg("a","1",[dep("b",">=1,<2")]))
            self.assertEqual(s["dependencies"],[dep("b",">=1,<2")])
            with self.assertRaisesRegex(ValueError,"incompatible"):e.install(*pkg("b","2"))
            self.assertEqual(e.status("b")["version"],"1")
