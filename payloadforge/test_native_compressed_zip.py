import ctypes as C
import hashlib,io,json,unittest,zipfile
import test_native_zip as zipbase
import test_native_store as storebase

class NativeCompressedZipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        zipbase.NativeZipTests.setUpClass.__func__(cls)
        cls.lib.pf_zip_scan_owned.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(zipbase.Entry),C.POINTER(C.c_void_p),C.c_size_t,C.POINTER(C.c_size_t)]
        cls.lib.pf_zip_scan_owned.restype=C.c_int
        cls.lib.pf_zip_release.argtypes=[C.POINTER(C.c_void_p),C.c_size_t];cls.lib.pf_zip_release.restype=None
    def scan(self,raw):
        buf=C.create_string_buffer(raw);entries=(zipbase.Entry*8)();owned=(C.c_void_p*8)();count=C.c_size_t(99)
        rc=self.lib.pf_zip_scan_owned(buf,len(raw),entries,owned,8,C.byref(count))
        try:
            if rc:
                self.assertEqual(count.value,0);self.assertFalse(any(owned));return None
            return [(C.string_at(e.name,e.name_len).decode(),C.string_at(e.data,e.size)) for e in entries[:count.value]]
        finally:self.lib.pf_zip_release(owned,8)
    def make(self,items):return zipbase.archive(items,zipfile.ZIP_DEFLATED)
    def test_deflated(self):
        items=[("a.txt",b"hello "*30),("b.txt",b"")]
        self.assertEqual(self.scan(self.make(items)),items)
    def test_mixed(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            z.writestr("stored.txt",b"stored",compress_type=zipfile.ZIP_STORED)
            z.writestr("deflated.txt",b"deflated"*12,compress_type=zipfile.ZIP_DEFLATED)
        self.assertEqual(self.scan(b.getvalue()),[("stored.txt",b"stored"),("deflated.txt",b"deflated"*12)])
    def test_bad_crc(self):
        b=bytearray(self.make([("a",b"hello")]))
        c=b.index(b"PK\x01\x02"); b[14]^=1;b[c+16]^=1
        self.assertIsNone(self.scan(bytes(b)))
    def test_bad_output_length(self):
        b=bytearray(self.make([("a",b"hello")]))
        c=b.index(b"PK\x01\x02"); b[22]=6;b[c+24]=6
        self.assertIsNone(self.scan(bytes(b)))
    def test_cleanup_on_later_failure(self):
        b=bytearray(self.make([("a",b"hello"),("b",b"world")]))
        c=b.index(b"PK\x01\x02"); second=b.index(b"PK\x01\x02",c+4)
        b[second+16]^=1
        self.assertIsNone(self.scan(bytes(b)))
    def test_bomb_and_traversal(self):
        self.assertIsNone(self.scan(self.make([("a",b"A"*1000000)])))
        self.assertIsNone(self.scan(self.make([("../x",b"x")])))
    def test_duplicate_and_truncation(self):
        self.assertIsNone(self.scan(self.make([("a",b"one"),("A",b"two")])))
        raw=self.make([("a",b"test")])
        for n in range(len(raw)):self.assertIsNone(self.scan(raw[:n]))

class NativeCompressedStoreTests(unittest.TestCase):
    setUp=storebase.NativeStoreTests.setUp
    @classmethod
    def setUpClass(cls):storebase.NativeStoreTests.setUpClass.__func__(cls)
    def package(self,version):
        items=[("settings.json",b"{}", "preserve"),("data.txt",version.encode()*20,"replace-with-backup")]
        m={"schema_version":3,"id":"demo","version":version,"files":[],"dependencies":[],"resources":[],"conflicts":[]}
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w",compression=zipfile.ZIP_DEFLATED) as z:
            for path,raw,policy in items:
                z.writestr(path,raw);m["files"].append({"path":path,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"policy":policy})
        a=b.getvalue();raw=json.dumps(m).encode()
        return a,len(a),hashlib.sha256(a).hexdigest().encode(),raw,len(raw),hashlib.sha256(raw).hexdigest().encode()
    def active(self):
        p=self.root/"apps/demo";return p/"generations"/(p/"CURRENT").read_text()
    def test_install_update(self):
        self.assertEqual(self.lib.pf_install_initial(self.fd,*self.package("1")),0)
        (self.active()/"data/settings.json").write_bytes(b"user")
        self.assertEqual(self.lib.pf_install_update(self.fd,*self.package("2")),0)
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
        self.assertEqual((self.active()/"data/data.txt").read_bytes(),b"2"*20)
    def test_bad_hash(self):
        p=list(self.package("1"));p[2]=b"0"*64
        self.assertEqual(self.lib.pf_install_initial(self.fd,*p),-1)
        self.assertEqual(list(self.root.iterdir()),[])
