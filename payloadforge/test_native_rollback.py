import ctypes,hashlib,json,shutil,unittest
import test_native_backup as base

class NativeRollbackTests(unittest.TestCase):
    setUp=base.NativeBackupTests.setUp
    install=base.NativeBackupTests.install
    app=base.NativeBackupTests.app
    active=base.NativeBackupTests.active
    update=base.NativeBackupTests.update
    backup=base.NativeBackupTests.backup
    verify=base.NativeBackupTests.verify
    @classmethod
    def setUpClass(cls):
        base.NativeBackupTests.setUpClass.__func__(cls)
        cls.lib.pf_rollback.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p];cls.lib.pf_rollback.restype=ctypes.c_int
    def rollback(self,snapshot):return self.lib.pf_rollback(self.fd,b"demo",snapshot.encode())
    def prepare(self):
        self.assertEqual(self.install(),0);old=self.active()
        self.assertEqual(self.update(),0)
        snaps=list((self.app()/"backups").iterdir());self.assertEqual(len(snaps),1)
        return old,snaps[0].name
    def test_restore_latest_config(self):
        first,name=self.prepare();prior=self.active()
        (prior/"data/settings.json").write_bytes(b'{"latest":true}')
        self.assertEqual(self.rollback(name),0);new=self.active()
        self.assertNotEqual(new,first);self.assertNotEqual(new,prior)
        self.assertEqual((new/"data/assets/demo.txt").read_bytes(),b"v1")
        self.assertEqual((new/"data/settings.json").read_bytes(),b'{"latest":true}')
        self.assertEqual(json.loads((new/"registry.json").read_bytes())["version"],"1.0.0")
        self.assertEqual(len(list((self.app()/"backups").iterdir())),2)
    def test_restore_without_source_generation(self):
        old,name=self.prepare();shutil.rmtree(old)
        self.assertEqual(self.verify(name),0);self.assertEqual(self.rollback(name),0)
        self.assertEqual((self.active()/"data/assets/demo.txt").read_bytes(),b"v1")
    def test_corrupt_snapshot(self):
        _,name=self.prepare();prior=self.active()
        (self.app()/"backups"/name/"data/settings.json").write_bytes(b"bad")
        self.assertEqual(self.rollback(name),-1);self.assertEqual(self.active(),prior)
    def test_corrupt_provenance(self):
        _,name=self.prepare();prior=self.active()
        (self.app()/"backups"/name/"manifest.json").write_bytes(b"{}")
        self.assertEqual(self.verify(name),-1);self.assertEqual(self.rollback(name),-1);self.assertEqual(self.active(),prior)
    def test_pre_activation_failure(self):
        _,name=self.prepare();prior=self.active()
        gen=hashlib.sha256(b"rollback"+prior.name.encode()+name.encode()).hexdigest()
        (self.app()/(".pointer-"+gen)).write_bytes(b"blocked")
        self.assertEqual(self.rollback(name),-1);self.assertEqual(self.active(),prior)
    def test_update_after_rollback(self):
        _,name=self.prepare();self.assertEqual(self.rollback(name),0)
        self.assertEqual(self.update(version="3.0.0"),0)
        self.assertEqual(json.loads((self.active()/"registry.json").read_bytes())["version"],"3.0.0")
    def test_rollback_keeps_new_config_path(self):
        self.assertEqual(self.install(),0)
        self.assertEqual(self.update([("settings.json",b"{}", "preserve"),("new.ini",b"x","preserve"),("assets/demo.txt",b"v2","replace-with-backup")]),0)
        (self.active()/"data/new.ini").write_bytes(b"user")
        name=next((self.app()/"backups").iterdir()).name
        self.assertEqual(self.rollback(name),0)
        self.assertEqual((self.active()/"data/new.ini").read_bytes(),b"user")
