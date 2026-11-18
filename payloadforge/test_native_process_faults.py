"""Linux-only process interruption tests. No hardware power-off or production hooks."""
import ctypes as C
import os,pathlib,subprocess,tempfile,unittest
import test_native_store as base
from test_native_recovery import Report

WRAP=r"""
#define _POSIX_C_SOURCE 200809L
#include <string.h>
#include <unistd.h>
static int target;
void pf_test_fault(int value){target=value;}
int __real_renameat(int,const char *,int,const char *);
int __wrap_renameat(int oldfd,const char *old,int newfd,const char *new){
 int marker=!strcmp(new,"CURRENT");
 int publish=!strncmp(old,".stage-",7);
 /* 1/2 before/after active-pointer rename, 3/4 before/after staging publication. */
 if((target==1&&marker)||(target==3&&publish))_exit(77);
 int rc=__real_renameat(oldfd,old,newfd,new);
 if(!rc&&((target==2&&marker)||(target==4&&publish)))_exit(77);
 return rc;
}
"""
class NativeProcessFaultTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    update=base.NativeStoreTests.update
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        p=pathlib.Path(tmp.name);wrapper=p/"fault.c";wrapper.write_text(WRAP)
        native=pathlib.Path(__file__).resolve().parent/"native"
        out=p/"fault.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",
            *[str(native/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c")],
            str(wrapper),"-Wl,--wrap=renameat","-o",str(out),"-lz"],check=True)
        cls.lib=C.CDLL(str(out))
        args=[C.c_int,C.c_void_p,C.c_size_t,C.c_char_p,C.c_void_p,C.c_size_t,C.c_char_p]
        for key in ("pf_install_initial","pf_install_update"):
            fn=getattr(cls.lib,key);fn.argtypes=args;fn.restype=C.c_int
        cls.lib.pf_test_fault.argtypes=[C.c_int];cls.lib.pf_test_fault.restype=None
        cls.lib.pf_recovery_inspect.argtypes=[C.c_int,C.c_char_p,C.POINTER(Report)];cls.lib.pf_recovery_inspect.restype=C.c_int
        cls.lib.pf_uninstall.argtypes=[C.c_int,C.c_char_p,C.c_int,C.POINTER(C.c_size_t)];cls.lib.pf_uninstall.restype=C.c_int
        cls.lib.pf_backup.argtypes=[C.c_int,C.c_char_p,C.c_void_p];cls.lib.pf_backup.restype=C.c_int
        cls.lib.pf_rollback.argtypes=[C.c_int,C.c_char_p,C.c_char_p];cls.lib.pf_rollback.restype=C.c_int
    def interrupt(self,point,operation):
        pid=os.fork()
        if pid==0:
            self.lib.pf_test_fault(point)
            try:operation()
            finally:os._exit(78)
        _,status=os.waitpid(pid,0)
        self.assertTrue(os.WIFEXITED(status));self.assertEqual(os.WEXITSTATUS(status),77)
    def inspect(self):
        out=Report()
        self.assertEqual(self.lib.pf_recovery_inspect(self.fd,b"demo",C.byref(out)),0)
        return out
    def test_initial_before_publish(self):
        self.interrupt(3,self.install)
        p=self.inspect();self.assertEqual((p.marker,p.staged_generations,p.inactive_generations),(0,1,0))
    def test_initial_after_publish(self):
        self.interrupt(4,self.install)
        p=self.inspect();self.assertEqual((p.marker,p.staged_generations,p.inactive_generations),(0,0,1))
    def test_initial_before_activation(self):
        self.interrupt(1,self.install)
        p=self.inspect();self.assertEqual((p.marker,p.pending_markers,p.inactive_generations),(0,1,1))
    def test_initial_after_activation(self):
        self.interrupt(2,self.install)
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.pending_markers),(1,1,0))
        self.assertEqual((self.active()/"data/assets/demo.txt").read_bytes(),b"v1")
    def test_update_before_activation(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/settings.json").write_bytes(b"user")
        self.interrupt(1,self.update)
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.pending_markers),(1,1,1))
        self.assertEqual(self.active(),old);self.assertEqual((old/"data/settings.json").read_bytes(),b"user")
        self.assertGreaterEqual(p.backups,1)
    def test_update_after_activation(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/settings.json").write_bytes(b"user")
        self.interrupt(2,self.update)
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.pending_markers),(1,1,0))
        self.assertNotEqual(self.active(),old)
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
        self.assertEqual((self.active()/"data/assets/demo.txt").read_bytes(),b"v2")
    def test_uninstall_before_activation(self):
        self.assertEqual(self.install(),0)
        self.interrupt(1,lambda:self.lib.pf_uninstall(self.fd,b"demo",1,C.byref(C.c_size_t())))
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.pending_markers),(1,1,1))
        self.assertTrue((self.active()/"data/settings.json").exists())
    def test_uninstall_after_activation(self):
        self.assertEqual(self.install(),0);old=self.active()
        self.interrupt(2,lambda:self.lib.pf_uninstall(self.fd,b"demo",1,C.byref(C.c_size_t())))
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.pending_markers),(3,1,0))
        self.assertTrue((old/"data/settings.json").exists())
    def test_rollback_before_activation(self):
        self.assertEqual(self.install(),0);snap=C.create_string_buffer(65)
        self.assertEqual(self.lib.pf_backup(self.fd,b"demo",snap),0)
        self.assertEqual(self.update(),0);old=self.active()
        self.interrupt(1,lambda:self.lib.pf_rollback(self.fd,b"demo",snap.value))
        p=self.inspect();self.assertEqual((p.marker,p.integrity,p.pending_markers),(1,1,1))
        self.assertEqual(self.active(),old)
    def test_rollback_after_activation(self):
        self.assertEqual(self.install(),0);snap=C.create_string_buffer(65)
        self.assertEqual(self.lib.pf_backup(self.fd,b"demo",snap),0)
        self.assertEqual(self.update(),0)
        self.interrupt(2,lambda:self.lib.pf_rollback(self.fd,b"demo",snap.value))
        self.assertEqual(self.inspect().integrity,1)
        self.assertEqual((self.active()/"data/assets/demo.txt").read_bytes(),b"v1")
