import ctypes as C
import hashlib,io,json,struct,unittest,zipfile
import test_native_http as httpbase
import test_native_store as base

TOKEN=httpbase.TOKEN
HEADERS=(httpbase.HOST,httpbase.AUTH,b"Origin: http://127.0.0.1:8765",b"X-PayloadForge-Confirm: yes",b"Content-Type: application/octet-stream")
class Upload(C.Structure):
    _fields_=[("action",C.c_uint),("manifest",C.c_void_p),("archive",C.c_void_p),
              ("manifest_n",C.c_size_t),("archive_n",C.c_size_t),("manifest_sha",C.c_char*65),("archive_sha",C.c_char*65)]
class NativeUploadTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    @classmethod
    def setUpClass(cls):
        httpbase.NativeHTTPTests.setUpClass.__func__(cls)
        cls.lib.pf_http_upload_head.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_char_p,C.POINTER(C.c_uint),C.POINTER(C.c_size_t)]
        cls.lib.pf_http_upload_head.restype=C.c_int
        cls.lib.pf_http_upload_parse.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_char_p,C.POINTER(Upload)]
        cls.lib.pf_http_upload_parse.restype=C.c_int
        cls.lib.pf_http_upload_dispatch.argtypes=[C.c_int,C.POINTER(Upload),C.c_void_p,C.c_size_t]
        cls.lib.pf_http_upload_dispatch.restype=C.c_int
    def package(self,version="1.0.0",text=b"v1"):
        z=io.BytesIO();items=[("settings.json",b"{}","preserve"),("assets/demo.txt",text,"replace-with-backup")]
        m={"schema_version":3,"id":"demo","version":version,"files":[],"dependencies":[],"conflicts":[],"resources":[]}
        with zipfile.ZipFile(z,"w") as out:
            for p,v,policy in items:
                out.writestr(p,v);m["files"].append({"path":p,"size":len(v),"sha256":hashlib.sha256(v).hexdigest(),"policy":policy})
        return self.envelope(json.dumps(m).encode(),z.getvalue())
    def envelope(self,m,a,mh=None,ah=None):
        return b"PFU1"+struct.pack(">II",len(m),len(a))+(mh or hashlib.sha256(m).hexdigest().encode())+(ah or hashlib.sha256(a).hexdigest().encode())+m+a
    def header(self,n,action=b"verify",headers=HEADERS,length=None):
        content=str(n).encode() if length is None else length
        return b"\r\n".join([b"POST /api/upload/"+action+b" HTTP/1.1",*headers,b"Content-Length: "+content,b"",b""])
    def request(self,body=None,action=b"verify",headers=HEADERS,length=None):
        body=self.package() if body is None else body
        return self.header(len(body),action,headers,length)+body
    def parse(self,raw,status=200):
        b=C.create_string_buffer(raw);q=Upload()
        self.assertEqual(self.lib.pf_http_upload_parse(b,len(raw),8765,TOKEN,C.byref(q)),status)
        if status!=200:self.assertEqual(q.action,0)
        return b,q
    def head(self,b,status=200):
        action=C.c_uint(99);length=C.c_size_t(99)
        self.assertEqual(self.lib.pf_http_upload_head(b,len(b),8765,TOKEN,C.byref(action),C.byref(length)),status)
        if status!=200:self.assertEqual((action.value,length.value),(0,0))
        return action.value,length.value
    def dispatch(self,raw,status=200):
        b,q=self.parse(raw);out=C.create_string_buffer(2048)
        self.assertEqual(self.lib.pf_http_upload_dispatch(self.fd,C.byref(q),out,len(out)),status)
        return json.loads(out.value)
    def test_header_before_body(self):
        b=self.package()
        self.assertEqual(self.head(self.header(len(b),b"verify")),(1,len(b)))
        self.assertEqual(self.head(self.header(len(b),b"install")),(2,len(b)))
    def test_auth_origin_confirmation(self):
        for missing,status in ((1,401),(2,403),(3,403),(4,400)):
            self.head(self.header(200,headers=tuple(v for i,v in enumerate(HEADERS) if i!=missing)),status)
        self.head(self.header(200,headers=HEADERS+(HEADERS[1],)),400)
        self.head(self.header(200,headers=HEADERS+(b"Transfer-Encoding: chunked",)),400)
        self.head(self.header(200,headers=HEADERS+(b"Content-Type: application/octet-stream",)),400)
    def test_lengths_and_invalid_type(self):
        for length in (b"0",b"140",b"20000000",b"9999999999999999999",b"+200",b"0200",b"2x"):
            self.head(self.header(200,length=length),400)
        self.head(self.header(200,headers=HEADERS[:-1]+(b"Content-Type: text/plain",)),400)
    def test_invalid_binary_framing(self):
        b=self.package()
        for bad in (b[:-1],b+b"x",b"BAD!"+b[4:],b[:4]+b"\xff"*4+b[8:],b[:12]+b"G"*64+b[76:]):
            self.parse(self.request(bad),400)
        self.parse(self.request(b,length=str(len(b)+1).encode()),400)
    def test_verify_no_write(self):
        x=self.dispatch(self.request())
        self.assertEqual((x["id"],x["version"],x["files"]),("demo","1.0.0",2))
        self.assertFalse(x["state_checked"]);self.assertFalse(x["provenance_verified"])
        self.assertEqual(list(self.root.iterdir()),[])
    def test_bad_hash_no_write(self):
        b=self.envelope(self.manifest,self.archive,ah=b"0"*64)
        self.assertFalse(self.dispatch(self.request(b,b"install"),409)["ok"])
        self.assertEqual(list(self.root.iterdir()),[])
    def test_invalid_manifest_no_write(self):
        b=self.envelope(b"{}",self.archive)
        self.assertFalse(self.dispatch(self.request(b,b"install"),409)["ok"])
        self.assertEqual(list(self.root.iterdir()),[])
    def test_install_upgrade_downgrade(self):
        self.assertTrue(self.dispatch(self.request(self.package(),b"install"))["ok"])
        (self.active()/"data/settings.json").write_bytes(b"user")
        self.assertTrue(self.dispatch(self.request(self.package("2.0.0",b"v2"),b"upgrade"))["ok"])
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
        self.assertEqual((self.active()/"data/assets/demo.txt").read_bytes(),b"v2")
        self.assertTrue(self.dispatch(self.request(self.package("1.0.0",b"v1"),b"downgrade"))["ok"])
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
    def test_small_output_no_write(self):
        b,q=self.parse(self.request(action=b"install"));out=C.create_string_buffer(32)
        self.assertEqual(self.lib.pf_http_upload_dispatch(self.fd,C.byref(q),out,len(out)),500)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_readonly_does_not_accept_upload(self):
        raw=self.header(len(self.package()),b"install");q=httpbase.Request()
        self.assertEqual(self.lib.pf_http_parse(raw,len(raw),8765,TOKEN,C.byref(q)),405)
        self.assertEqual(list(self.root.iterdir()),[])
