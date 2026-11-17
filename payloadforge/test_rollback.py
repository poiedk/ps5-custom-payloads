import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from payloadforge.engine import Engine
from test_engine import package
from test_dependencies import pkg,dep

class RollbackTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.e=Engine(self.root)
        self.p1=package("v1",[("settings.json",b"{}","preserve"),("a.txt",b"old","replace-with-backup")])
        self.p2=package("v2",[("settings.json",b"[]","preserve"),("a.txt",b"new","replace-with-backup")])
    def data(self,s):return self.root/"apps/demo/generations"/s["generation"]/"data"
    def test_rollback_preserves_new_config(self):
        self.e.install(*self.p1);s=self.e.install(*self.p2)
        self.data(s).joinpath("settings.json").write_bytes(b'{"user":true}')
        backup=self.e.backups("demo")[0]
        rolled=self.e.rollback("demo",backup["snapshot"])
        self.assertEqual(rolled["version"],"v1")
        self.assertEqual(self.data(rolled).joinpath("settings.json").read_bytes(),b'{"user":true}')
        self.assertEqual(self.data(rolled).joinpath("a.txt").read_bytes(),b"old")
        self.assertEqual(len(self.e.backups("demo")),2)
    def test_rollback_corrupt_snapshot(self):
        self.e.install(*self.p1);s=self.e.install(*self.p2)
        b=self.e.backups("demo")[0]
        (self.root/"apps/demo/backups"/b["snapshot"]/"data/a.txt").write_bytes(b"x")
        with self.assertRaisesRegex(ValueError,"snapshot integrity"):self.e.rollback("demo",b["snapshot"])
        self.assertEqual(self.e.status("demo"),s)
    def test_interruption_after_activation_restores_previous(self):
        old=self.e.install(*self.p1)
        original=self.e._activate
        def fault(app,g):
            original(app,g);raise OSError("injected failure after pointer switch")
        with patch.object(self.e,"_activate",side_effect=fault):
            with self.assertRaises(OSError):self.e.install(*self.p2)
        self.assertEqual(self.e.status("demo"),old)
    def test_first_install_activation_failure_clears_pointer(self):
        original=self.e._activate
        def fault(app,g):
            original(app,g);raise OSError("failure")
        with patch.object(self.e,"_activate",side_effect=fault):
            with self.assertRaises(OSError):self.e.install(*self.p1)
        self.assertIsNone(self.e.status("demo"))
    def test_recovery_report_does_not_delete(self):
        a=self.e.install(*self.p1);b=self.e.install(*self.p2)
        stage=self.root/"apps/demo/generations"/(".stage-"+"f"*32);stage.mkdir()
        report=self.e.recovery_report("demo")
        self.assertEqual(report["current"],b["generation"])
        self.assertIn(a["generation"],report["inactive_generations"])
        self.assertTrue(stage.exists());self.assertTrue(report["staged"])
    def test_rollback_reverse_dependency(self):
        self.e.install(*pkg("b","1"));self.e.install(*pkg("b","2"))
        self.e.install(*pkg("a","1",[dep("b",">=2")]))
        backup=self.e.backups("b")[0]
        with self.assertRaisesRegex(ValueError,"incompatible"):self.e.rollback("b",backup["snapshot"])
        self.assertEqual(self.e.status("b")["version"],"2")
