import ctypes,hashlib,io,json,os,pathlib,subprocess,tempfile,unittest,zipfile
class NativeStoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"store.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",*[str(base/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c")],"-o",str(out)],check=True)
        cls.lib=ctypes.CDLL(str(out));cls.lib.pf_install_initial.argtypes=[ctypes.c_int,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p];cls.lib.pf_install_initial.restype=ctypes.c_int
        cls.lib.pf_install_update.argtypes=cls.lib.pf_install_initial.argtypes;cls.lib.pf_install_update.restype=ctypes.c_int
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
        app=self.app();app.parent.mkdir(mode=0o700);app.mkdir(mode=0o700)
        (app/(".pointer-"+self.ah.decode())).write_text("blocked")
        self.assertEqual(self.install(),-1)
        self.assertFalse((app/"CURRENT").exists())

    def update(self,items=None,version="2.0.0",bad_hash=False):
        items=items if items is not None else [("settings.json",b'{"default":2}',"preserve"),("assets/demo.txt",b"v2","replace-with-backup")]
        b=io.BytesIO();m={"schema_version":3,"id":"demo","version":version,"files":[],"dependencies":[],"resources":[],"conflicts":[]}
        with zipfile.ZipFile(b,"w") as z:
            for path,data,policy in items:
                z.writestr(path,data);m["files"].append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"policy":policy})
        a=b.getvalue();raw=json.dumps(m).encode();ah=hashlib.sha256(a).hexdigest().encode();mh=hashlib.sha256(raw).hexdigest().encode()
        return self.lib.pf_install_update(self.fd,a,len(a),b"0"*64 if bad_hash else ah,raw,len(raw),mh)
    def active(self):
        return self.app()/"generations"/(self.app()/"CURRENT").read_text()
    def test_update_preserves_config_and_registry(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/settings.json").write_bytes(b'{"user":true}')
        self.assertEqual(self.update(),0);new=self.active()
        self.assertNotEqual(new,old)
        self.assertEqual((new/"data/settings.json").read_bytes(),b'{"user":true}')
        self.assertEqual((new/"data/assets/demo.txt").read_bytes(),b"v2")
        reg=(new/"registry.json").read_bytes();self.assertEqual(hashlib.sha256(reg).hexdigest(),(new/"registry.sha256").read_text())
        self.assertEqual(json.loads(reg)["version"],"2.0.0")
        item=next(x for x in json.loads(reg)["files"] if x["path"]=="settings.json")
        self.assertEqual(item["sha256"],hashlib.sha256(b'{"user":true}').hexdigest())
        self.assertEqual((old/"data/assets/demo.txt").read_bytes(),b"v1")
    def test_update_omitted_config_and_second_update(self):
        self.assertEqual(self.install(),0)
        (self.active()/"data/settings.json").write_bytes(b"user")
        items=[("assets/demo.txt",b"v2","replace-with-backup")]
        self.assertEqual(self.update(items),0)
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
        self.assertEqual(self.update(version="3.0.0"),0)
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
    def test_update_reject_missing(self):
        self.assertEqual(self.update(),-2)
    def test_update_wrong_hash(self):
        self.assertEqual(self.install(),0);old=self.active()
        self.assertEqual(self.update(bad_hash=True),-1);self.assertEqual(self.active(),old)
    def test_update_tampered_immutable(self):
        self.assertEqual(self.install(),0);old=self.active()
        (old/"data/assets/demo.txt").write_bytes(b"changed")
        self.assertEqual(self.update(),-1);self.assertEqual(self.active(),old)
    def test_update_symlink_config(self):
        self.assertEqual(self.install(),0);old=self.active();p=old/"data/settings.json"
        outside=self.root/"outside";outside.write_bytes(b"private");p.unlink();p.symlink_to(outside)
        self.assertEqual(self.update(),-1);self.assertEqual(self.active(),old);self.assertEqual(outside.read_bytes(),b"private")
    def test_update_case_conflict(self):
        self.assertEqual(self.install(),0);old=self.active()
        self.assertEqual(self.update([("SETTINGS.JSON",b"{}", "preserve")]),-1);self.assertEqual(self.active(),old)
    def test_update_registry_tamper(self):
        self.assertEqual(self.install(),0);self.assertEqual(self.update(),0);old=self.active()
        (old/"registry.json").write_text("{}")
        self.assertEqual(self.update(version="3.0.0"),-1);self.assertEqual(self.active(),old)
    def test_update_same_version_rejected(self):
        self.assertEqual(self.install(),0);old=self.active()
        self.assertEqual(self.update(version="1.0.0"),-1);self.assertEqual(self.active(),old)
