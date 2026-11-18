import ctypes,hashlib,io,json,pathlib,subprocess,tempfile,unittest,zipfile
class File(ctypes.Structure):
    _fields_=[("path",ctypes.c_char*1025),("sha256",ctypes.c_char*65),("size",ctypes.c_size_t),("preserve",ctypes.c_int)]
class Manifest(ctypes.Structure):
    _fields_=[("id",ctypes.c_char*49),("version",ctypes.c_char*65),("count",ctypes.c_size_t),("total",ctypes.c_size_t),("schema",ctypes.c_uint)]
def entry(name="settings.json",data=b"{}",policy="preserve"):
    return {"path":name,"sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"policy":policy}
def doc(files=None):
    return {"schema_version":3,"id":"demo","version":"v1.0","files":files if files is not None else [entry()],"dependencies":[],"resources":[],"conflicts":[]}
def raw(d):return json.dumps(d,ensure_ascii=False).encode()
def sha(b):return hashlib.sha256(b).hexdigest().encode()
def archive(items):
    f=io.BytesIO()
    with zipfile.ZipFile(f,"w") as z:
        for name,data in items:z.writestr(name,data)
    return f.getvalue()
class NativeManifestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"manifest.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",*[str(base/x) for x in ("core.c","sha256.c","zip.c","manifest.c","version.c","constraints.c","inflate.c","tar.c")],"-o",str(out),"-lz"],check=True)
        cls.lib=ctypes.CDLL(str(out))
        cls.lib.pf_manifest_parse.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(Manifest),ctypes.POINTER(File),ctypes.c_size_t]
        cls.lib.pf_manifest_parse.restype=ctypes.c_int
        cls.lib.pf_bundle_verify.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p,ctypes.POINTER(Manifest),ctypes.POINTER(File),ctypes.c_size_t]
        cls.lib.pf_bundle_verify.restype=ctypes.c_int
    def parse(self,d,cap=8):
        b=raw(d) if isinstance(d,dict) else d;m=Manifest();f=(File*cap)()
        status=self.lib.pf_manifest_parse(b,len(b),ctypes.byref(m),f,cap)
        if status:self.assertEqual(m.count,0);return None
        return m,f
    def verify(self,a,m,ah=None,mh=None):
        m=raw(m);result=Manifest();f=(File*8)()
        status=self.lib.pf_bundle_verify(a,len(a),ah or sha(a),m,len(m),mh or sha(m),ctypes.byref(result),f,8)
        return status==0
    def test_valid_versions(self):
        for schema in (1,2,3):
            d=doc();d["schema_version"]=schema
            if schema<3:d.pop("conflicts");d.pop("resources")
            if schema==1:d.pop("dependencies")
            m,f=self.parse(d);self.assertEqual(m.schema,schema);self.assertEqual(m.count,1);self.assertEqual(f[0].path,b"settings.json")
    def test_unknown_duplicate_fields(self):
        self.assertIsNone(self.parse({**doc(),"extra":1}))
        self.assertIsNone(self.parse(raw(doc()).replace(b'"id": "demo"',b'"id":"demo","id":"demo"')))
    def test_policy(self):
        self.assertIsNone(self.parse(doc([entry(policy="replace-with-backup")])))
        self.assertIsNotNone(self.parse(doc([entry("a.txt",b"x","replace-with-backup")])))
    def test_paths(self):
        for n in ("../a.txt","/a.txt",".secret.txt","a/.secret.txt","a.elf","é.txt","x/a.exe"):
            with self.subTest(n=n):self.assertIsNone(self.parse(doc([entry(n)])))
    def test_collision(self):
        for names in (["a.txt","A.TXT"],["a.txt","a.txt/b.txt"]):
            self.assertIsNone(self.parse(doc([entry(n) for n in names])))
    def test_nonempty_constraints(self):
        d=doc();d["dependencies"]=[{"id":"other","constraint":"*"}];self.assertIsNone(self.parse(d))
    def test_bad_size(self):
        for n in (-1,True,67108865,1.5):
            f=entry();f["size"]=n;self.assertIsNone(self.parse(doc([f])))
    def test_capacity_and_empty(self):
        self.assertIsNone(self.parse(doc([])));self.assertIsNone(self.parse(doc([entry("a.txt"),entry("b.txt")]),1))
    def test_hashes(self):
        f=entry();f["sha256"]="A"*64;self.assertIsNone(self.parse(doc([f])))
    def test_bundle(self):self.assertTrue(self.verify(archive([("settings.json",b"{}")]),doc()))
    def test_wrong_hashes(self):
        a=archive([("settings.json",b"{}")]);self.assertFalse(self.verify(a,doc(),ah=b"0"*64));self.assertFalse(self.verify(a,doc(),mh=b"0"*64))
    def test_missing_extra_wrong_data(self):
        for items in ([("other.txt",b"{}")],[("settings.json",b"xx")],[("settings.json",b"{}"),("extra.txt",b"x")]):
            self.assertFalse(self.verify(archive(items),doc()))
