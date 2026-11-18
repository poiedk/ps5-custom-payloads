import ctypes as C
import gzip, hashlib, io, json, pathlib, subprocess, tarfile, tempfile, unittest
import test_native_zip as zipbase
import test_native_store as storebase

def tar_bytes(items):
    buf=io.BytesIO()
    with tarfile.open(fileobj=buf,mode="w",format=tarfile.USTAR_FORMAT) as t:
        for name,raw in items:
            info=name if isinstance(name,tarfile.TarInfo) else tarfile.TarInfo(name)
            info.size=len(raw)
            t.addfile(info,io.BytesIO(raw))
    return buf.getvalue()
def packed(items):return gzip.compress(tar_bytes(items),mtime=0)
class NativeTarTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"tar.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",*[str(base/x) for x in ("core.c","zip.c","inflate.c","tar.c")],"-o",str(out),"-lz"],check=True)
        cls.lib=C.CDLL(str(out))
        cls.lib.pf_archive_scan.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(zipbase.Entry),C.POINTER(C.c_void_p),C.POINTER(C.c_void_p),C.c_size_t,C.POINTER(C.c_size_t)]
        cls.lib.pf_archive_scan.restype=C.c_int
        cls.lib.pf_archive_release.argtypes=[C.POINTER(C.c_void_p),C.POINTER(C.c_void_p),C.c_size_t];cls.lib.pf_archive_release.restype=None
    def scan(self,raw,cap=8):
        buf=C.create_string_buffer(raw);entries=(zipbase.Entry*cap)();owned=(C.c_void_p*cap)()
        expanded=C.c_void_p();count=C.c_size_t(99)
        status=self.lib.pf_archive_scan(buf,len(raw),entries,owned,C.byref(expanded),cap,C.byref(count))
        try:
            if status:
                self.assertEqual(count.value,0);self.assertFalse(expanded.value);self.assertFalse(any(owned));return None
            return [(C.string_at(e.name,e.name_len).decode(),C.string_at(e.data,e.size)) for e in entries[:count.value]]
        finally:self.lib.pf_archive_release(owned,C.byref(expanded),cap)
    def test_regular_and_prefix(self):
        items=[("folder/"+"a"*95+"/data.txt",b"hello"),("b.txt",b"")]
        self.assertEqual(self.scan(packed(items)),items)
    def test_zip_dispatch(self):
        self.assertEqual(self.scan(zipbase.archive([("a",b"test")])),[("a",b"test")])
    def test_bad_paths_and_duplicates(self):
        for names in (["../out"],["/out"],["a","A"],["a","a/b"],["a//b"],["a\\b"],["x/../a"]):
            with self.subTest(names=names):self.assertIsNone(self.scan(packed([(n,b"x") for n in names])))
    def test_special_entries(self):
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.DIRTYPE,tarfile.FIFOTYPE,tarfile.XHDTYPE,tarfile.GNUTYPE_LONGNAME):
            with self.subTest(kind=kind):
                info=tarfile.TarInfo("special");info.type=kind
                if kind in (tarfile.SYMTYPE,tarfile.LNKTYPE):info.linkname="other"
                self.assertIsNone(self.scan(packed([(info,b"")])))
    def test_corrupt_header_and_padding(self):
        raw=bytearray(tar_bytes([("a",b"hello")]))
        raw[0]^=1
        self.assertIsNone(self.scan(gzip.compress(raw)))
        raw=bytearray(tar_bytes([("a",b"hello")]))
        raw[517]=1
        self.assertIsNone(self.scan(gzip.compress(raw)))
    def test_nonzero_trailer(self):
        raw=bytearray(tar_bytes([("a",b"x")]))
        raw[-1]=1
        self.assertIsNone(self.scan(gzip.compress(raw)))
    def test_bad_gzip(self):
        raw=packed([("a",b"test")])
        self.assertIsNone(self.scan(raw+raw))
        self.assertIsNone(self.scan(raw+b"x"))
        bad=bytearray(raw);bad[-8]^=1
        self.assertIsNone(self.scan(bytes(bad)))
        for n in range(len(raw)):self.assertIsNone(self.scan(raw[:n]))
    def test_expansion_and_count(self):
        self.assertIsNone(self.scan(packed([("a",b"A"*1000000)])))
        self.assertIsNone(self.scan(packed([("a",b"x"),("b",b"y")]),1))
    def test_invalid_ustar(self):
        raw=bytearray(tar_bytes([("a",b"x")]))
        raw[257]=0
        raw[148:156]=b" "*8
        raw[148:156]=("%06o"%sum(raw[:512])).encode()+b"\0 "
        self.assertIsNone(self.scan(gzip.compress(raw)))

class NativeTarStoreTests(unittest.TestCase):
    setUp=storebase.NativeStoreTests.setUp
    @classmethod
    def setUpClass(cls):storebase.NativeStoreTests.setUpClass.__func__(cls)
    def package(self,v,extra=False):
        items=[("settings.json",b"{}", "preserve"),("assets/demo.txt",v.encode()*30,"replace-with-backup")]
        m={"schema_version":3,"id":"demo","version":v,"files":[],"dependencies":[],"resources":[],"conflicts":[]}
        for p,raw,policy in items:m["files"].append({"path":p,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"policy":policy})
        a=packed([(p,raw) for p,raw,_ in items]+([("extra.txt",b"x")] if extra else []))
        raw=json.dumps(m).encode()
        return a,len(a),hashlib.sha256(a).hexdigest().encode(),raw,len(raw),hashlib.sha256(raw).hexdigest().encode()
    def data(self):
        p=self.root/"apps/demo";return p/"generations"/(p/"CURRENT").read_text()/"data"
    def test_install_update(self):
        self.assertEqual(self.lib.pf_install_initial(self.fd,*self.package("1")),0)
        (self.data()/"settings.json").write_bytes(b"user")
        self.assertEqual(self.lib.pf_install_update(self.fd,*self.package("2")),0)
        self.assertEqual((self.data()/"settings.json").read_bytes(),b"user")
        self.assertEqual((self.data()/"assets/demo.txt").read_bytes(),b"2"*30)
    def test_extra_file_blocks(self):
        self.assertEqual(self.lib.pf_install_initial(self.fd,*self.package("1",True)),-1)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_zip_to_tar_update(self):
        self.assertEqual(storebase.NativeStoreTests.install(self),0)
        self.assertEqual(self.lib.pf_install_update(self.fd,*self.package("2")),0)
        self.assertEqual((self.data()/"assets/demo.txt").read_bytes(),b"2"*30)
