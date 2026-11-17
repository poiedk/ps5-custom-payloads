import ctypes,hashlib,json,unittest
import test_native_store as base
import test_native_update as update_tests
from payloadforge.dependencies import version_key

class NativeVersionTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    bundle=update_tests.NativeUpdateTests.bundle
    @classmethod
    def setUpClass(cls):
        base.NativeStoreTests.setUpClass.__func__(cls)
        cls.lib.pf_version_compare.argtypes=[ctypes.c_char_p,ctypes.c_char_p,ctypes.POINTER(ctypes.c_int)]
        cls.lib.pf_version_compare.restype=ctypes.c_int
        for fn in (cls.lib.pf_install_upgrade,cls.lib.pf_install_downgrade):
            fn.argtypes=cls.lib.pf_install_initial.argtypes;fn.restype=ctypes.c_int
        cls.lib.pf_status.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_void_p];cls.lib.pf_status.restype=ctypes.c_int
        cls.lib.pf_uninstall.argtypes=[ctypes.c_int,ctypes.c_char_p,ctypes.c_int,ctypes.POINTER(ctypes.c_size_t)]
        cls.lib.pf_uninstall.restype=ctypes.c_int
    def compare(self,a,b):
        result=ctypes.c_int(99)
        rc=self.lib.pf_version_compare(a.encode(),b.encode(),ctypes.byref(result))
        return rc,result.value
    def status(self):
        v=ctypes.create_string_buffer(65);g=ctypes.create_string_buffer(65)
        rc=self.lib.pf_status(self.fd,b"demo",v,g);return rc,v.value.decode(),g.value.decode()
    def test_cross_language_vectors(self):
        versions=["1","v1.0","1.0.0+build","1.0.0-alpha","1.0.0-alpha.1","1.0.0-alpha.beta","1.0.0-beta.2","1.0.0-beta.11","1.0.0-rc.1","2","10.2","V2.1"]
        for a in versions:
            for b in versions:
                ka,kb=version_key(a),version_key(b)
                self.assertEqual(self.compare(a,b),(0,(ka>kb)-(ka<kb)),(a,b))
    def test_invalid_versions(self):
        for value in ("","v","01","1.02","1.2.3.4","1-","1+","1.0.0-beta.01","1..2","dev","1 beta","1.0.0-a..b"):
            self.assertEqual(self.compare(value,"1")[0],-1,value)
    def test_large_numeric_components(self):
        self.assertEqual(self.compare("9"*60,"8"*60),(0,1))
    def test_upgrade_downgrade(self):
        self.assertEqual(self.install(),0);old=self.active()
        self.assertEqual(self.lib.pf_install_upgrade(self.fd,*self.bundle("0.9.0")),-1)
        self.assertEqual(self.active(),old)
        self.assertEqual(self.lib.pf_install_upgrade(self.fd,*self.bundle("2.0.0")),0)
        active=self.active();self.assertEqual(self.lib.pf_install_upgrade(self.fd,*self.bundle("2.0.0+same")),-1)
        self.assertEqual(self.active(),active)
        self.assertEqual(self.lib.pf_install_downgrade(self.fd,*self.bundle("1.5.0")),0)
        self.assertEqual(self.status()[1],"1.5.0")
    def test_status_lifecycle(self):
        self.assertEqual(self.status(),(0,"",""))
        self.assertEqual(self.install(),0);self.assertEqual(self.status(),(1,"1.0.0",self.active().name))
        count=ctypes.c_size_t()
        self.assertEqual(self.lib.pf_uninstall(self.fd,b"demo",1,ctypes.byref(count)),0)
        self.assertEqual(self.status(),(0,"",""))
    def test_corrupt_marker(self):
        self.assertEqual(self.install(),0)
        (self.app()/"CURRENT").write_text("../bad")
        self.assertEqual(self.status(),(-1,"",""))
