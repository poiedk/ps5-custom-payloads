import ctypes,hashlib,json,unittest
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
        cls.lib.pf_backup.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_void_p];cls.lib.pf_backup.restype=ctypes.c_int
        cls.lib.pf_backup_verify.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_char_p];cls.lib.pf_backup_verify.restype=ctypes.c_int
    def backup(self):
        out=ctypes.create_string_buffer(65);rc=self.lib.pf_backup(self.fd,b"demo",out)
        return rc,out.value.decode()
    def verify(self,snapshot):return self.lib.pf_backup_verify(self.fd,b"demo",snapshot.encode())
    def test_independent_snapshot_and_config_hash(self):
        self.assertEqual(self.install(),0)
        src=self.active()/"data/settings.json";src.write_bytes(b"user")
        rc,name=self.backup();self.assertEqual(rc,0)
        path=self.app()/"backups"/name;self.assertEqual((path/"data/settings.json").read_bytes(),b"user")
        record=json.loads((path/"registry.json").read_bytes())
        item=next(x for x in record["files"] if x["path"]=="settings.json")
        self.assertEqual(item["sha256"],hashlib.sha256(b"user").hexdigest())
        src.write_bytes(b"new");self.assertEqual((path/"data/settings.json").read_bytes(),b"user")
        self.assertEqual(self.verify(name),0)
    def test_idempotent_and_distinct(self):
        self.assertEqual(self.install(),0)
        rc,name=self.backup();self.assertEqual(rc,0);self.assertEqual(self.backup(),(0,name))
        (self.active()/"data/settings.json").write_bytes(b"changed")
        rc,new=self.backup();self.assertEqual(rc,0);self.assertNotEqual(name,new)
    def test_automatic_backup(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/settings.json").write_bytes(b"modified")
        self.assertEqual(self.update(),0)
        paths=list((self.app()/"backups").iterdir());self.assertEqual(len(paths),1)
        self.assertEqual((paths[0]/"data/settings.json").read_bytes(),b"modified")
        self.assertEqual(self.verify(paths[0].name),0)
    def test_corrupt_snapshot_blocks_update(self):
        self.assertEqual(self.install(),0);old=self.active()
        rc,name=self.backup();self.assertEqual(rc,0)
        (self.app()/"backups"/name/"data/settings.json").write_bytes(b"tamper")
        self.assertEqual(self.verify(name),-1);self.assertEqual(self.update(),-1);self.assertEqual(self.active(),old)
    def test_bad_snapshot(self):
        self.assertEqual(self.install(),0);self.assertEqual(self.verify("../outside"),-1)
    def test_missing_package(self):self.assertEqual(self.backup(),(-1,""))
    def test_immutable_tampering(self):
        self.assertEqual(self.install(),0);(self.active()/"data/assets/demo.txt").write_bytes(b"bad")
        self.assertEqual(self.backup(),(-1,""))
