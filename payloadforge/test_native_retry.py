import ctypes as C
import hashlib,unittest
import test_native_store as base
from test_native_recovery import Report

class NativeRetryTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    update=base.NativeStoreTests.update
    @classmethod
    def setUpClass(cls):
        base.NativeStoreTests.setUpClass.__func__(cls)
        cls.lib.pf_recovery_quarantine.argtypes=[C.c_int,C.c_char_p,C.c_uint,C.c_char_p,C.c_uint,C.c_char_p]
        cls.lib.pf_recovery_quarantine.restype=C.c_int
        cls.lib.pf_recovery_inspect.argtypes=[C.c_int,C.c_char_p,C.POINTER(Report)]
        cls.lib.pf_recovery_inspect.restype=C.c_int
    def inspect(self):
        p=Report();self.assertEqual(self.lib.pf_recovery_inspect(self.fd,b"demo",C.byref(p)),0);return p
    def move(self,kind,h,marker=None,current=None):
        if marker is None:
            p=self.inspect();marker=p.marker;current=p.current
        return self.lib.pf_recovery_quarantine(self.fd,b"demo",marker,current,kind,h)
    def q(self,category,h):
        return self.root/"recovery-quarantine/demo"/category/h.decode()
    def test_missing_store_no_write(self):
        self.assertEqual(self.move(1,self.ah,0,b""),-1)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_active_never_moved(self):
        self.assertEqual(self.install(),0)
        self.assertEqual(self.move(5,self.ah),-1)
        self.assertTrue(self.active().is_dir())
        self.assertFalse((self.root/"recovery-quarantine").exists())
    def test_stage_kept_and_retry(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;stage=self.app()/"generations"/(".stage-"+h.decode())
        stage.mkdir(mode=0o700);(stage/"unregistered").write_bytes(b"retain")
        self.assertEqual(self.move(1,h),0)
        self.assertFalse(stage.exists())
        self.assertEqual((self.q("staged-generations",h)/"unregistered").read_bytes(),b"retain")
        self.assertEqual(self.inspect().integrity,1)
    def test_pending_and_inactive_initial_retry(self):
        # Initial installation blocked immediately before CURRENT: a fully
        # published generation remains. Test-only collision creates evidence.
        self.app().parent.mkdir(mode=0o700);self.app().mkdir(mode=0o700)
        pointer=self.app()/(".pointer-"+self.ah.decode())
        pointer.write_bytes(b"old evidence");pointer.chmod(0o600)
        self.assertEqual(self.install(),-1)
        p=self.inspect();self.assertEqual((p.marker,p.inactive_generations,p.pending_markers),(0,1,1))
        self.assertEqual(self.move(3,self.ah),0)
        self.assertEqual(self.move(5,self.ah),0)
        self.assertEqual(self.q("pending-activation",self.ah).read_bytes(),b"old evidence")
        self.assertEqual(self.install(),0)
        self.assertEqual(self.inspect().integrity,1)
    def test_stale_observation(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;s=self.app()/"generations"/(".stage-"+h.decode());s.mkdir(mode=0o700)
        self.assertEqual(self.move(1,h,1,b"b"*64),-1);self.assertTrue(s.exists())
    def test_corrupt_active_refuses(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;s=self.app()/"generations"/(".stage-"+h.decode());s.mkdir(mode=0o700)
        (self.active()/"data/assets/demo.txt").write_bytes(b"tampered")
        self.assertEqual(self.move(1,h),-1);self.assertTrue(s.exists())
    def test_never_overwrite_quarantine(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;s=self.app()/"generations"/(".stage-"+h.decode());s.mkdir(mode=0o700)
        (s/"data.txt").write_bytes(b"old")
        self.assertEqual(self.move(1,h),0)
        s.mkdir(mode=0o700);(s/"data.txt").write_bytes(b"new")
        self.assertEqual(self.move(1,h),-1)
        self.assertEqual((s/"data.txt").read_bytes(),b"new")
        self.assertEqual((self.q("staged-generations",h)/"data.txt").read_bytes(),b"old")
    def test_unsafe_entry(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;outside=self.root/"outside";outside.mkdir()
        (outside/"data").write_bytes(b"private")
        (self.app()/"generations"/(".stage-"+h.decode())).symlink_to(outside)
        self.assertEqual(self.move(1,h),-1)
        self.assertEqual((outside/"data").read_bytes(),b"private")
    def test_stage_backup_and_uninstall_marker(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;backups=self.app()/"backups";backups.mkdir(mode=0o700)
        (backups/(".stage-"+h.decode())).mkdir(mode=0o700)
        pointer=self.app()/(".uninstall-"+h.decode());pointer.write_bytes(b"pending");pointer.chmod(0o600)
        self.assertEqual(self.move(2,h),0);self.assertEqual(self.move(4,h),0)
        self.assertEqual(self.q("pending-uninstall",h).read_bytes(),b"pending")
        self.assertEqual(self.inspect().marker,1)
    def test_bad_arguments(self):
        self.assertEqual(self.install(),0)
        self.assertEqual(self.move(0,self.ah),-1)
        self.assertEqual(self.move(1,b"../outside"),-1)
        self.assertEqual(self.move(1,self.ah,4,b""),-1)
