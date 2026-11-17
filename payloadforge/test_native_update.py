import hashlib,io,json,os,unittest,zipfile
import test_native_store as base

class NativeUpdateTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    app=base.NativeStoreTests.app
    @classmethod
    def setUpClass(cls):
        base.NativeStoreTests.setUpClass.__func__(cls)
        cls.lib.pf_update.argtypes=cls.lib.pf_install_initial.argtypes
        cls.lib.pf_update.restype=cls.lib.pf_install_initial.restype
    def bundle(self,version="2",items=None):
        if items is None:items=[("settings.json",b'{"default":2}',"preserve"),("assets/demo.txt",b"v2","replace-with-backup")]
        b=io.BytesIO();m={"schema_version":3,"id":"demo","version":version,"files":[],"dependencies":[],"conflicts":[],"resources":[]}
        with zipfile.ZipFile(b,"w") as z:
            for p,raw,policy in items:
                z.writestr(p,raw);m["files"].append({"path":p,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"policy":policy})
        a=b.getvalue();raw=json.dumps(m).encode()
        return a,len(a),hashlib.sha256(a).hexdigest().encode(),raw,len(raw),hashlib.sha256(raw).hexdigest().encode()
    def update(self,package=None):return self.lib.pf_update(self.fd,*(package or self.bundle()))
    def current(self):return (self.app()/"CURRENT").read_bytes()
    def data(self):return self.app()/"generations"/self.current().decode()/"data"
    def test_update_preserves_config(self):
        self.assertEqual(self.install(),0)
        previous=self.data();(previous/"settings.json").write_bytes(b'{"user":42}')
        self.assertEqual(self.update(),0)
        self.assertEqual((self.data()/"settings.json").read_bytes(),b'{"user":42}')
        self.assertEqual((self.data()/"assets/demo.txt").read_bytes(),b"v2")
        self.assertEqual((previous/"assets/demo.txt").read_bytes(),b"v1")
    def test_update_without_install(self):self.assertEqual(self.update(),-2)
    def test_omitted_config_preserved(self):
        self.assertEqual(self.install(),0);old=self.current()
        (self.data()/"settings.json").write_bytes(b"user")
        self.assertEqual(self.update(self.bundle(items=[("assets/demo.txt",b"v2","replace-with-backup")])),0)
        self.assertNotEqual(self.current(),old)
        self.assertEqual((self.data()/"settings.json").read_bytes(),b"user")
        self.assertEqual((self.data()/"assets/demo.txt").read_bytes(),b"v2")
    def test_changed_immutable_blocked(self):
        self.assertEqual(self.install(),0);old=self.current()
        (self.data()/"assets/demo.txt").write_bytes(b"bad")
        self.assertEqual(self.update(),-1);self.assertEqual(self.current(),old)
    def test_config_symlink_blocked(self):
        self.assertEqual(self.install(),0);old=self.current()
        target=self.root/"outside";target.write_bytes(b"secret")
        p=self.data()/"settings.json";p.unlink();p.symlink_to(target)
        self.assertEqual(self.update(),-1);self.assertEqual(self.current(),old);self.assertEqual(target.read_bytes(),b"secret")
    def test_hardlink_blocked(self):
        self.assertEqual(self.install(),0);old=self.current()
        os.link(self.data()/"settings.json",self.root/"alias")
        self.assertEqual(self.update(),-1);self.assertEqual(self.current(),old)
    def test_manifest_tampered(self):
        self.assertEqual(self.install(),0);old=self.current()
        (self.data().parent/"manifest.json").write_bytes(b"{}")
        self.assertEqual(self.update(),-1);self.assertEqual(self.current(),old)
    def test_pre_activation_failure(self):
        self.assertEqual(self.install(),0);old=self.current();pack=self.bundle()
        generation=hashlib.sha256(pack[2]+pack[5]+old).hexdigest()
        (self.app()/(".pointer-"+generation)).write_bytes(b"blocked")
        self.assertEqual(self.update(pack),-1);self.assertEqual(self.current(),old)
    def test_two_updates(self):
        self.assertEqual(self.install(),0);self.assertEqual(self.update(),0)
        (self.data()/"settings.json").write_bytes(b"user")
        p=self.bundle("3",[("settings.json",b"default","preserve"),("assets/demo.txt",b"v3","replace-with-backup")])
        self.assertEqual(self.update(p),0);self.assertEqual((self.data()/"settings.json").read_bytes(),b"user")
