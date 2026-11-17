import ctypes,hashlib,unittest
import test_native_backup as base

class NativeUninstallTests(unittest.TestCase):
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
        cls.lib.pf_uninstall.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)];cls.lib.pf_uninstall.restype=ctypes.c_int
    def uninstall(self,keep=1):
        count=ctypes.c_size_t(0)
        rc=self.lib.pf_uninstall(self.fd,b"demo",keep,ctypes.byref(count))
        return rc,count.value
    def marker(self):return (self.app()/"CURRENT").read_text()
    def test_registry_only_cleanup(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/untracked.txt").write_bytes(b"keep")
        self.assertEqual(self.uninstall(),(0,2))
        marker=self.marker();self.assertTrue(marker.startswith("uninstalled:"));self.assertTrue(marker.endswith(":keep"))
        self.assertFalse((old/"data/settings.json").exists());self.assertFalse((old/"data/assets/demo.txt").exists())
        self.assertEqual((old/"data/untracked.txt").read_bytes(),b"keep")
        self.assertEqual(self.verify(marker.split(":")[1]),0)
    def test_keep_config_reinstall(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/settings.json").write_bytes(b"user")
        self.assertEqual(self.uninstall(1),(0,2));self.assertEqual(self.install(),0)
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
        self.assertEqual(self.update(),0);self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
    def test_drop_config_reinstall(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/settings.json").write_bytes(b"user")
        self.assertEqual(self.uninstall(0),(0,2));name=self.marker().split(":")[1]
        self.assertEqual(self.install(),0);self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"{}")
        self.assertEqual(self.verify(name),0)
    def test_double_uninstall(self):
        self.assertEqual(self.install(),0);self.assertEqual(self.uninstall(),(0,2))
        self.assertEqual(self.uninstall(),(-2,0))
        self.assertEqual(self.update(),-2)
    def test_backup_failure_keeps_active(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/assets/demo.txt").write_bytes(b"bad")
        self.assertEqual(self.uninstall(),(-1,0));self.assertEqual(self.active(),old)
        self.assertTrue((old/"data/settings.json").exists())
    def test_tampered_snapshot_blocks_keep_reinstall(self):
        self.assertEqual(self.install(),0);self.assertEqual(self.uninstall(),(0,2))
        marker=self.marker();name=marker.split(":")[1]
        (self.app()/"backups"/name/"data/settings.json").write_bytes(b"bad")
        self.assertEqual(self.install(),-1);self.assertEqual(self.marker(),marker)
    def test_pre_activation_failure(self):
        self.assertEqual(self.install(),0);old=self.active()
        rc,name=self.backup();self.assertEqual(rc,0)
        (self.app()/(".uninstall-"+name)).write_bytes(b"blocked")
        self.assertEqual(self.uninstall(),(-1,0));self.assertEqual(self.active(),old)
        self.assertTrue((old/"data/settings.json").exists())
