import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from payloadforge.engine import Engine
from test_engine import package
from test_dependencies import pkg,dep

class UninstallTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.e=Engine(self.root)
        self.p1=package("v1",[("settings.json",b"{}","preserve"),("a.txt",b"old","replace-with-backup")])
        self.p2=package("v2",[("settings.json",b'{"default":2}',"preserve"),("a.txt",b"new","replace-with-backup")])
    def data(self,s):return self.root/"apps/demo/generations"/s["generation"]/"data"
    def test_registry_only(self):
        s=self.e.install(*self.p1);(self.data(s)/"untracked.txt").write_text("keep")
        report=self.e.uninstall("demo")
        self.assertIsNone(self.e.status("demo"))
        self.assertEqual(report["removed"],["a.txt","settings.json"])
        self.assertTrue((self.data(s)/"untracked.txt").exists())
        self.assertFalse((self.data(s)/"a.txt").exists())
        self.assertEqual(report["cleanup_errors"],[])
    def test_preserve_reinstall(self):
        s=self.e.install(*self.p1);(self.data(s)/"settings.json").write_bytes(b'{"user":1}')
        self.e.uninstall("demo",preserve_config=True)
        s=self.e.install(*self.p2)
        self.assertEqual((self.data(s)/"settings.json").read_bytes(),b'{"user":1}')
    def test_drop_reinstall(self):
        s=self.e.install(*self.p1);(self.data(s)/"settings.json").write_bytes(b'{"user":1}')
        self.e.uninstall("demo",preserve_config=False)
        s=self.e.install(*self.p2)
        self.assertEqual((self.data(s)/"settings.json").read_bytes(),b'{"default":2}')
    def test_reverse_dependency_block(self):
        self.e.install(*pkg("b","1"));self.e.install(*pkg("a","1",[dep("b")]))
        with self.assertRaisesRegex(ValueError,"missing dependency"):self.e.uninstall("b")
        self.assertEqual(self.e.status("b")["version"],"1")
    def test_uninstalled_rollback(self):
        self.e.install(*self.p1);r=self.e.uninstall("demo")
        s=self.e.rollback("demo",r["snapshot"])
        self.assertEqual(s["version"],"v1")
        self.assertEqual((self.data(s)/"a.txt").read_bytes(),b"old")
    def test_failed_reinstall_preserves_tombstone(self):
        s=self.e.install(*self.p1);(self.data(s)/"settings.json").write_bytes(b'{"user":1}')
        self.e.uninstall("demo");original=self.e._activate
        def fault(app,g):
            original(app,g);raise OSError("fault")
        with patch.object(self.e,"_activate",side_effect=fault):
            with self.assertRaises(OSError):self.e.install(*self.p2)
        self.assertIsNone(self.e.status("demo"))
        s=self.e.install(*self.p2)
        self.assertEqual((self.data(s)/"settings.json").read_bytes(),b'{"user":1}')
