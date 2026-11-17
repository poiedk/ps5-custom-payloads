import tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from payloadforge.engine import Engine
from test_engine import package

class BackupTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.e=Engine(self.root)
        self.p1=package("v1",[("settings.json",b"{}","preserve"),("a.txt",b"one","replace-with-backup")])
        self.p2=package("v2",[("settings.json",b"[]","preserve"),("a.txt",b"two","replace-with-backup")])
        self.old=self.e.install(*self.p1)
    def data(self):return self.root/"apps/demo/generations"/self.old["generation"]/"data"
    def snapshot(self,record):return self.root/"apps/demo/backups"/record["snapshot"]/"data"
    def test_manual(self):
        b=self.e.backup("demo")
        self.assertEqual(self.snapshot(b).joinpath("a.txt").read_bytes(),b"one")
        self.assertEqual(self.e.backups("demo"),[b])
    def test_update_automatically_snapshots(self):
        self.data().joinpath("settings.json").write_bytes(b'{"user":1}')
        self.e.install(*self.p2)
        b=self.e.backups("demo");self.assertEqual(len(b),1)
        self.assertEqual(self.snapshot(b[0]).joinpath("settings.json").read_bytes(),b'{"user":1}')
        self.assertEqual(b[0]["record"]["version"],"v1")
    def test_corrupt_snapshot(self):
        b=self.e.backup("demo");self.snapshot(b).joinpath("settings.json").write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError,"snapshot integrity"):self.e.backups("demo")
    def test_no_snapshot_on_initial_install(self):self.assertEqual(self.e.backups("demo"),[])
    def test_failed_update_keeps_snapshot_and_old(self):
        with patch.object(self.e,"_before_activate",side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):self.e.install(*self.p2)
        self.assertEqual(self.e.status("demo"),self.old)
        self.assertEqual(len(self.e.backups("demo")),1)
    def test_backup_failure_blocks_update(self):
        with patch.object(self.e,"_snapshot",side_effect=OSError("no space")):
            with self.assertRaises(OSError):self.e.install(*self.p2)
        self.assertEqual(self.e.status("demo"),self.old)
