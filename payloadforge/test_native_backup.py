import ctypes,hashlib,json,os,unittest
import test_native_store as base

class NativeBackupTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    update=base.NativeStoreTests.update
    @classmethod
    def setUpClass(cls):
        base.NativeStoreTests.setUpClass.__func__(cls)
        cls.lib.pf_backup.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_void_p]
        cls.lib.pf_backup.restype=ctypes.c_int
        cls.lib.pf_backup_verify.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p]
        cls.lib.pf_backup_verify.restype=ctypes.c_int
    def backup(self):
        out=ctypes.create_string_buffer(65)
        rc=self.lib.pf_backup(self.fd,b"demo",out)
        return rc,out.value.decode()
    def verify(self,name):
        return self.lib.pf_backup_verify(self.fd,b"demo",name.encode())
    def snapshot(self,name):return self.app()/"backups"/name
    def snapshots(self):return sorted(p.name for p in (self.app()/"backups").iterdir() if not p.name.startswith("."))
    def test_manual_snapshot_actual_config(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/settings.json").write_bytes(b"user")
        rc,name=self.backup();self.assertEqual(rc,0);self.assertEqual(len(name),64)
        self.assertEqual(self.verify(name),0)
        p=self.snapshot(name)
        self.assertEqual((p/"data/settings.json").read_bytes(),b"user")
        self.assertEqual((p/"data/assets/demo.txt").read_bytes(),b"v1")
        r=(p/"registry.json").read_bytes()
        self.assertEqual(hashlib.sha256(r).hexdigest(),(p/"registry.sha256").read_text())
        self.assertEqual(next(f for f in json.loads(r)["files"] if f["path"]=="settings.json")["sha256"],hashlib.sha256(b"user").hexdigest())
    def test_auto_backup_before_update(self):
        self.assertEqual(self.install(),0);prior=self.active()
        (prior/"data/settings.json").write_bytes(b"custom")
        self.assertEqual(self.update(),0)
        names=self.snapshots();self.assertEqual(len(names),1);self.assertEqual(self.verify(names[0]),0)
        self.assertEqual((self.snapshot(names[0])/"data/settings.json").read_bytes(),b"custom")
        self.assertEqual((self.snapshot(names[0])/"data/assets/demo.txt").read_bytes(),b"v1")
        self.assertEqual((self.snapshot(names[0])/"source.generation").read_text(),prior.name)
    def test_idempotent_and_new_user_config(self):
        self.assertEqual(self.install(),0)
        rc,one=self.backup();self.assertEqual(rc,0)
        self.assertEqual(self.backup(),(0,one))
        (self.active()/"data/settings.json").write_bytes(b"changed")
        rc,two=self.backup();self.assertEqual(rc,0);self.assertNotEqual(one,two)
        self.assertEqual(len(self.snapshots()),2)
        self.assertEqual(self.verify(one),0);self.assertEqual(self.verify(two),0)
    def test_tampered_snapshot_blocks_reuse_and_update(self):
        self.assertEqual(self.install(),0);prior=self.active()
        rc,name=self.backup();self.assertEqual(rc,0)
        (self.snapshot(name)/"data/settings.json").write_bytes(b"tampered")
        self.assertEqual(self.verify(name),-1);self.assertEqual(self.backup(),(-1,""))
        self.assertEqual(self.update(),-1);self.assertEqual(self.active(),prior)
    def test_immutable_tamper_blocks_snapshot(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/assets/demo.txt").write_bytes(b"tampered")
        self.assertEqual(self.backup(),(-1,""))
    def test_snapshot_metadata_tamper(self):
        self.assertEqual(self.install(),0);rc,name=self.backup();self.assertEqual(rc,0)
        (self.snapshot(name)/"source.generation").write_text("a"*64)
        self.assertEqual(self.verify(name),-1)
    def test_backup_dir_symlink_blocks_update(self):
        self.assertEqual(self.install(),0);old=self.active()
        target=self.root/"outside";target.mkdir(mode=0o700)
        (self.app()/"backups").symlink_to(target)
        self.assertEqual(self.backup(),(-1,""))
        self.assertEqual(self.update(),-1);self.assertEqual(self.active(),old)
        self.assertEqual(list(target.iterdir()),[])
    def test_snapshot_hardlink_rejected(self):
        self.assertEqual(self.install(),0);rc,name=self.backup();self.assertEqual(rc,0)
        os.link(self.snapshot(name)/"data/settings.json",self.root/"alias")
        self.assertEqual(self.verify(name),-1)
    def test_invalid_or_missing_id(self):
        self.assertEqual(self.backup(),(-1,""))
        out=ctypes.create_string_buffer(65)
        self.assertEqual(self.lib.pf_backup(self.fd,b"../demo",out),-1)
        self.assertEqual(self.verify("../x"),-1)
