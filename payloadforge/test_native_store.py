import ctypes,hashlib,io,json,os,pathlib,subprocess,tempfile,unittest,zipfile
class NativeStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"store.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",*[str(base/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c")],"-o",str(out)],check=True)
        cls.lib=ctypes.CDLL(str(out));cls.lib.pf_install_initial.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p];cls.lib.pf_install_initial.restype=ctypes.c_int
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup);self.root=pathlib.Path(t.name);self.fd=os.open(self.root,os.O_RDONLY|os.O_DIRECTORY);self.addCleanup(os.close,self.fd)
        b=io.BytesIO();items=[("settings.json",b"{}","preserve"),("assets/demo.txt",b"v1","replace-with-backup")]
        manifest={"schema_version":3,"id":"demo","version":"1.0.0","files":[],"dependencies":[],"resources":[],"conflicts":[]}
        with zipfile.ZipFile(b,"w") as z:
            for path,data,policy in items:
                z.writestr(path,data);manifest["files"].append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"policy":policy})
        self.archive=b.getvalue();self.manifest=json.dumps(manifest).encode();self.ah=hashlib.sha256(self.archive).hexdigest().encode();self.mh=hashlib.sha256(self.manifest).hexdigest().encode()
    def install(self,ah=None,mh=None):return self.lib.pf_install_initial(self.fd,self.archive,len(self.archive),ah or self.ah,self.manifest,len(self.manifest),mh or self.mh)
    def app(self):return self.root/"apps/demo"
    def test_install(self):
        self.assertEqual(self.install(),0)
        app=self.app();g=app/"generations"/self.ah.decode()
        self.assertEqual((app/"CURRENT").read_bytes(),self.ah)
        self.assertEqual((g/"data/settings.json").read_bytes(),b"{}")
        self.assertEqual((g/"data/assets/demo.txt").read_bytes(),b"v1")
        self.assertEqual((g/"manifest.json").read_bytes(),self.manifest)
        self.assertEqual((g/"manifest.sha256").read_bytes(),self.mh)
    def test_existing_rejected(self):
        self.assertEqual(self.install(),0)
        self.assertEqual(self.install(),-2)
    def test_bad_hash_no_write(self):
        self.assertEqual(self.install(ah=b"0"*64),-1)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_bad_manifest_hash_no_write(self):
        self.assertEqual(self.install(mh=b"0"*64),-1)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_untrusted_root_mode(self):
        self.root.chmod(0o755)
        self.assertEqual(self.install(),-1)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_apps_symlink(self):
        outside=self.root/"outside";outside.mkdir();(self.root/"apps").symlink_to(outside)
        self.assertEqual(self.install(),-1);self.assertEqual(list(outside.iterdir()),[])
    def test_app_symlink(self):
        outside=self.root/"outside";outside.mkdir();(self.root/"apps").mkdir();(self.root/"apps/demo").symlink_to(outside)
        self.assertEqual(self.install(),-1);self.assertEqual(list(outside.iterdir()),[])
    def test_fail_before_activation(self):
        app=self.app();app.mkdir(parents=True)
        (app/(".pointer-"+self.ah.decode())).write_text("blocked")
        self.assertEqual(self.install(),-1)
        self.assertFalse((app/"CURRENT").exists())
