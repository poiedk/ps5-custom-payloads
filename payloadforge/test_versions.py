import contextlib,io,json,tempfile,unittest
from pathlib import Path
from payloadforge.cli import main,strict_json
from payloadforge.engine import Engine
from test_engine import package

class VersionTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.e=Engine(self.root)
        self.p1=package("v1",[("a.txt",b"one","replace-with-backup")])
        self.p2=package("v2",[("a.txt",b"two","replace-with-backup")])
    def test_explicit_version_actions(self):
        self.e.install(*self.p1,action="install")
        with self.assertRaises(ValueError):self.e.install(*self.p2,action="install")
        self.assertEqual(self.e.install(*self.p2,action="upgrade")["version"],"v2")
        with self.assertRaises(ValueError):self.e.install(*self.p1,action="upgrade")
        self.assertEqual(self.e.install(*self.p1,action="downgrade")["version"],"v1")
    def test_missing_upgrade(self):
        with self.assertRaises(ValueError):self.e.install(*self.p2,action="upgrade")
    def test_versions(self):
        self.e.install(*self.p1);self.e.install(*self.p2)
        v=self.e.versions("demo")
        self.assertEqual(v["active"]["version"],"v2")
        self.assertEqual(v["backups"][0]["version"],"v1")
        self.assertEqual(len(self.e.list_installed()),1)
    def test_duplicate_json(self):
        with self.assertRaises(ValueError):strict_json(b'{"a":1,"a":2}')
    def test_cli(self):
        raw,h,m=self.p1
        archive=self.root/"data.zip";archive.write_bytes(raw)
        manifest=self.root/"manifest.json";manifest.write_text(json.dumps(m))
        args=["--root",str(self.root),"install","--archive",str(archive),"--manifest",str(manifest),"--sha256",h]
        with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args),1)
            self.assertEqual(main(args+["--confirm"]),0)
        out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(main(["--root",str(self.root),"list"]),0)
        self.assertEqual(json.loads(out.getvalue())[0]["version"],"v1")
    def test_plan_no_root_creation(self):
        raw,h,m=self.p1
        archive=self.root/"data.zip";archive.write_bytes(raw)
        manifest=self.root/"manifest.json";manifest.write_text(json.dumps(m))
        absent=self.root/"absent"
        out=io.StringIO()
        with contextlib.redirect_stdout(out):self.assertEqual(main(["--root",str(absent),"plan","--archive",str(archive),"--manifest",str(manifest),"--sha256",h]),0)
        self.assertTrue(json.loads(out.getvalue())["verified"]);self.assertFalse(absent.exists())
