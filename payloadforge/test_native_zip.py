import ctypes,io,pathlib,stat,subprocess,tempfile,unittest,warnings,zipfile
class Entry(ctypes.Structure):
    _fields_=[("name",ctypes.c_void_p),("data",ctypes.c_void_p),("name_len",ctypes.c_size_t),("size",ctypes.c_size_t)]
def archive(items,method=zipfile.ZIP_STORED):
    f=io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",UserWarning)
        with zipfile.ZipFile(f,"w",compression=method) as z:
            for p,data in items:z.writestr(p,data)
    return f.getvalue()
class NativeZipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"zip.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",str(base/"core.c"),str(base/"zip.c"),"-o",str(out)],check=True)
        cls.lib=ctypes.CDLL(str(out));cls.lib.pf_zip_scan.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(Entry),ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)];cls.lib.pf_zip_scan.restype=ctypes.c_int
    def scan(self,raw,capacity=16):
        buf=ctypes.create_string_buffer(raw);out=(Entry*capacity)();count=ctypes.c_size_t(99)
        status=self.lib.pf_zip_scan(buf,len(raw),out,capacity,ctypes.byref(count))
        if status!=0:
            self.assertEqual(count.value,0);return None
        return [(ctypes.string_at(e.name,e.name_len).decode(),ctypes.string_at(e.data,e.size)) for e in out[:count.value]]
    def test_normal(self):self.assertEqual(self.scan(archive([("a.txt",b"x"),("assets/b.txt",b"")])),[("a.txt",b"x"),("assets/b.txt",b"")])
    def test_traversal(self):
        for name in ("../a","/a","C:/a","a\\x","a/../b","a//b"):
            with self.subTest(name=name):self.assertIsNone(self.scan(archive([(name,b"x")])))
    def test_duplicates(self):
        for names in (["a","a"],["a","A"],["a","a/b"]):self.assertIsNone(self.scan(archive([(n,b"x") for n in names])))
    def test_symlink(self):
        i=zipfile.ZipInfo("link");i.create_system=3;i.external_attr=(stat.S_IFLNK|0o777)<<16
        self.assertIsNone(self.scan(archive([(i,b"target")])))
    def test_unsupported(self):
        self.assertIsNone(self.scan(archive([("a",b"x"*99)],zipfile.ZIP_DEFLATED)))
        self.assertIsNone(self.scan(archive([("folder/",b"")])))
        self.assertIsNone(self.scan(archive([("é.txt",b"x")])))
    def test_count(self):self.assertIsNone(self.scan(archive([("a",b"x"),("b",b"y")]),1))
    def test_crc(self):
        raw=bytearray(archive([("a",b"unique content")]));raw[31]^=1
        self.assertIsNone(self.scan(bytes(raw)))
    def test_local_mismatch(self):
        raw=bytearray(archive([("a",b"x")]));raw[30]=ord("b")
        self.assertIsNone(self.scan(bytes(raw)))
    def test_truncated(self):
        raw=archive([("a",b"x")])
        for n in range(len(raw)):self.assertIsNone(self.scan(raw[:n]))
    def test_trailing(self):self.assertIsNone(self.scan(archive([("a",b"x")])+b"extra"))
    def test_encrypted_flag(self):
        raw=bytearray(archive([("a",b"x")]));raw[6]|=1;pos=raw.index(b"PK\x01\x02");raw[pos+8]|=1
        self.assertIsNone(self.scan(bytes(raw)))
