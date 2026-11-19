import hashlib,json,tempfile,unittest
from pathlib import Path
from payloadforge.demo_fixture import generate
from payloadforge.engine import Engine
class FixtureTests(unittest.TestCase):
    def test_demo_flow(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);out=root/"fixtures";generate(out)
            e=Engine(root/"managed")
            def p(version):
                raw=(out/("demo-v"+version+".zip")).read_bytes()
                return raw,hashlib.sha256(raw).hexdigest(),json.loads((out/("demo-v"+version+".json")).read_text())
            a=e.install(*p("1.0.0"),action="install")
            raw, digest, _ = p("1.0.0")
            pointer = root / "managed/apps/payloadforge-demo/CURRENT"
            previous = pointer.read_bytes()
            for field, reason in (("dependencies", "missing dependency"), ("conflicts", "declared version conflict")):
                manifest = json.loads((out / ("negative-" + field + ".json")).read_text())
                with self.assertRaisesRegex(ValueError, reason):
                    e.install(raw, digest, manifest, action="install")
                self.assertEqual(pointer.read_bytes(), previous)
            data=root/"managed/apps/payloadforge-demo/generations"/a["generation"]/"data"
            (data/"settings.json").write_text('{"theme":"user"}')
            b=e.install(*p("2.0.0"),action="upgrade")
            data=root/"managed/apps/payloadforge-demo/generations"/b["generation"]/"data"
            self.assertEqual((data/"settings.json").read_text(),'{"theme":"user"}')
            snap=e.backups("payloadforge-demo")[0]
            self.assertEqual(e.rollback("payloadforge-demo",snap["snapshot"])["version"],"1.0.0")
            self.assertTrue(e.uninstall("payloadforge-demo")["uninstalled"])
    def test_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileExistsError):generate(Path(tmp))
