import ctypes as C
import subprocess
import sys
import hashlib, pathlib, unittest
import test_native_store as base

class Report(C.Structure):
    _fields_=[("marker",C.c_uint),("integrity",C.c_uint),
              *((name,C.c_size_t) for name in ("changed_configs","staged_generations","staged_backups","pending_markers","inactive_generations","backups","unexpected_entries")),
              ("current",C.c_char*65)]

class NativeRecoveryTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    update=base.NativeStoreTests.update
    @classmethod
    def setUpClass(cls):
        base.NativeStoreTests.setUpClass.__func__(cls)
        cls.lib.pf_recovery_inspect.argtypes=[C.c_int,C.c_char_p,C.POINTER(Report)]
        cls.lib.pf_recovery_inspect.restype=C.c_int
        cls.lib.pf_backup.argtypes=[C.c_int,C.c_char_p,C.c_void_p];cls.lib.pf_backup.restype=C.c_int
        cls.lib.pf_uninstall.argtypes=[C.c_int,C.c_char_p,C.c_int,C.POINTER(C.c_size_t)]
        cls.lib.pf_uninstall.restype=C.c_int
    def inspect(self,rc=0,id=b"demo"):
        report=Report()
        self.assertEqual(self.lib.pf_recovery_inspect(self.fd,id,C.byref(report)),rc)
        return report
    def tree(self):
        return sorted((str(p.relative_to(self.root)),p.read_bytes() if p.is_file() and not p.is_symlink() else None)
                      for p in self.root.rglob("*"))
    def test_empty_no_write(self):
        self.assertEqual(self.inspect().marker,0)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_active_and_changed_config(self):
        self.assertEqual(self.install(),0)
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.current),(1,1,self.ah))
        (self.active()/"data/settings.json").write_bytes(b"user edited")
        before=self.tree();p=self.inspect()
        self.assertEqual((p.integrity,p.changed_configs),(1,1));self.assertEqual(self.tree(),before)
    def test_damaged_immutable(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/assets/demo.txt").write_bytes(b"corrupt")
        self.assertEqual(self.inspect().integrity,2)
    def test_missing_config(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/settings.json").unlink()
        self.assertEqual(self.inspect().integrity,2)
    def test_bad_pointer_no_repair(self):
        self.assertEqual(self.install(),0)
        (self.app()/"CURRENT").write_bytes(b"invalid")
        before=self.tree();p=self.inspect()
        self.assertEqual((p.marker,p.integrity),(4,2));self.assertEqual(self.tree(),before)
    def test_missing_generation(self):
        self.assertEqual(self.install(),0)
        (self.app()/"CURRENT").write_bytes(b"a"*64)
        self.assertEqual(self.inspect().integrity,2)
    def test_interrupted_stage_and_pointer(self):
        self.assertEqual(self.install(),0)
        gens=self.app()/"generations"
        (gens/(".stage-"+"a"*64)).mkdir(mode=0o700)
        marker=self.app()/(".pointer-"+"a"*64);marker.write_bytes(b"b"*64);marker.chmod(0o600)
        (gens/("b"*64)).mkdir(mode=0o700)
        before=self.tree();p=self.inspect()
        self.assertEqual((p.staged_generations,p.pending_markers,p.inactive_generations),(1,1,1))
        self.assertEqual(p.integrity,1);self.assertEqual(self.tree(),before)
    def test_symlink_stage_not_followed(self):
        self.assertEqual(self.install(),0)
        outside=self.root/"outside";outside.mkdir();(outside/"secret").write_text("private")
        (self.app()/"generations"/(".stage-"+"a"*64)).symlink_to(outside)
        p=self.inspect();self.assertEqual(p.staged_generations,0);self.assertEqual(p.unexpected_entries,1)
        self.assertEqual((outside/"secret").read_text(),"private")
    def test_uninstall_retained_snapshot_verified(self):
        self.assertEqual(self.install(),0)
        removed=C.c_size_t()
        self.assertEqual(self.lib.pf_uninstall(self.fd,b"demo",1,C.byref(removed)),0)
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.backups),(3,1,1))
        snapshot=self.app()/"backups"/p.current.decode()
        (snapshot/"data/settings.json").write_bytes(b"corrupt")
        self.assertEqual(self.inspect().integrity,2)
    def test_busy_store_fails_without_waiting_or_mutating(self):
        self.assertEqual(self.install(), 0)
        before = self.tree()
        lock_script = (
            "import fcntl, sys, time\n"
            "with open(sys.argv[1], 'r+') as lock:\n"
            "    fcntl.lockf(lock, fcntl.LOCK_EX)\n"
            "    print('locked', flush=True)\n"
            "    time.sleep(5)\n"
        )
        with subprocess.Popen([sys.executable, "-c", lock_script, self.root / ".lock"],
                              stdout=subprocess.PIPE, text=True) as holder:
            try:
                self.assertEqual(holder.stdout.readline().strip(), "locked")
                self.inspect(-1)
                self.assertNotEqual(self.lib.pf_backup(self.fd, b"demo", None), 0)
                self.assertIsNone(holder.poll())
            finally:
                holder.terminate()
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.inspect().integrity, 1)

    def test_invalid_lock(self):
        outside=self.root/"outside";outside.write_bytes(b"private")
        (self.root/".lock").symlink_to(outside)
        self.inspect(-1);self.assertEqual(outside.read_bytes(),b"private")
    def test_existing_apps_without_lock(self):
        (self.root/"apps").mkdir(mode=0o700)
        self.inspect(-1);self.assertFalse((self.root/".lock").exists())
