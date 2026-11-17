import unittest
from manifest import validate

def entry(path="settings.json",policy="preserve"):
    return {"path":path,"sha256":"a"*64,"size":12,"policy":policy}
def doc(*items):
    return {"schema_version":1,"id":"demo","version":"v1.0","files":list(items)}
class ManifestTests(unittest.TestCase):
    def test_plan(self):
        result=validate(doc(entry()))
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["files"][0]["target"],"/data/payloadforge/apps/demo/settings.json")
    def test_traversal(self):
        for path in ("../escape.json","/escape.json","folder/../a.json"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                validate(doc(entry(path)))
    def test_duplicate(self):
        with self.assertRaises(ValueError):
            validate(doc(entry("A.json"),entry("a.json")))
    def test_prefix_conflict(self):
        with self.assertRaises(ValueError):
            validate(doc(entry("a.json"),entry("a.json/b.txt")))
    def test_config_preservation(self):
        with self.assertRaises(ValueError):
            validate(doc(entry(policy="replace-with-backup")))
    def test_executable(self):
        with self.assertRaises(ValueError): validate(doc(entry("tool.elf")))
    def test_arbitrary_destination(self):
        m=doc(entry());m["destination"]="/data"
        with self.assertRaises(ValueError):validate(m)
    def test_invalid_identifier(self):
        m=doc(entry());m["id"]="../demo"
        with self.assertRaises(ValueError):validate(m)
if __name__=="__main__":unittest.main()
