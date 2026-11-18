import ctypes as C
import json,pathlib,subprocess,tempfile,unittest
import test_native_store as base

TOKEN=b"0123456789abcdef"*4
HOST=b"Host: 127.0.0.1:8765"
AUTH=b"Authorization: Bearer "+TOKEN
class Request(C.Structure):
    _fields_=[("route",C.c_uint),("id",C.c_char*49)]
class NativeHTTPTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        src=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"http.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",
            *[str(src/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c","http.c")],"-o",str(out),"-lz"],check=True)
        cls.lib=C.CDLL(str(out))
        cls.lib.pf_http_parse.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_char_p,C.POINTER(Request)]
        cls.lib.pf_http_parse.restype=C.c_int
        cls.lib.pf_http_dispatch.argtypes=[C.c_int,C.POINTER(Request),C.c_void_p,C.c_size_t];cls.lib.pf_http_dispatch.restype=C.c_int
        cls.lib.pf_install_initial.argtypes=[C.c_int,C.c_void_p,C.c_size_t,C.c_char_p,C.c_void_p,C.c_size_t,C.c_char_p];cls.lib.pf_install_initial.restype=C.c_int
    def raw(self,path=b"/api/health",headers=(HOST,AUTH),method=b"GET"):
        return b"\r\n".join([method+b" "+path+b" HTTP/1.1",*headers,b"",b""])
    def parse(self,raw,expected=200):
        req=Request()
        self.assertEqual(self.lib.pf_http_parse(raw,len(raw),8765,TOKEN,C.byref(req)),expected)
        if expected!=200:self.assertEqual(req.route,0)
        return req
    def dispatch(self,path):
        p=self.parse(self.raw(path));body=C.create_string_buffer(2048)
        code=self.lib.pf_http_dispatch(self.fd,C.byref(p),body,len(body))
        return code,json.loads(body.value)
    def test_read_only_routes(self):
        for path,route in [(b"/api/health",1),(b"/api/status?id=demo",2),(b"/api/recovery?id=demo",3)]:
            self.assertEqual(self.parse(self.raw(path)).route,route)
    def test_missing_wrong_auth(self):
        for headers in [(HOST,),(HOST,b"Authorization: Bearer "+b"0"*64),(HOST,b"Authorization: Basic abc")]:
            self.parse(self.raw(headers=headers),401)
    def test_bad_host_origin(self):
        for headers in [(AUTH,),(AUTH,b"Host: evil.test"),(AUTH,b"Host: 127.0.0.1:8766"),(HOST,AUTH,b"Origin: https://evil.test"),(HOST,AUTH,b"Origin: null")]:
            self.parse(self.raw(headers=headers),403)
        self.parse(self.raw(headers=(HOST,AUTH,b"Origin: http://127.0.0.1:8765")))
    def test_header_duplicates(self):
        for header in (b"host: 127.0.0.1:8765",AUTH):
            self.parse(self.raw(headers=(HOST,AUTH,header)),400)
        for header in (b"Origin: http://127.0.0.1:8765",b"Content-Length: 0"):
            self.parse(self.raw(headers=(HOST,AUTH,header,header)),400)
    def test_body_and_upgrade_rejected(self):
        for h in (b"Content-Length: 1",b"Transfer-Encoding: chunked",b"Upgrade: websocket",b"Expect: 100-continue",b"Host : test"):
            self.parse(self.raw(headers=(HOST,AUTH,h)),400)
        self.parse(self.raw()+b"body",400)
        self.parse(self.raw(headers=(HOST,AUTH,b"Content-Length: 0")))
    def test_strict_framing(self):
        r=self.raw()
        for bad in (r[:-1],r.replace(b"\r\n",b"\n"),r.replace(HOST,b"Host: 127.0.0.1:8765\x00"),r.replace(AUTH,b" "+AUTH),r+r):
            self.parse(bad,400)
        self.parse(b"x"*8193,431)
    def test_paths(self):
        for path in (b"/api/status?id=../x",b"/api/status?id=a%2Fb",b"/api/recovery?id=a&x=b",b"/api/status?id=A"):
            self.parse(self.raw(path),400)
        self.parse(self.raw(b"/api/unknown"),404)
        self.parse(self.raw(method=b"POST"),405)
    def test_no_state_writes(self):
        code,body=self.dispatch(b"/api/health");self.assertEqual(code,200);self.assertFalse(body["mutation"])
        code,body=self.dispatch(b"/api/status?id=demo");self.assertEqual((code,body["active"]),(200,False))
        self.assertEqual(list(self.root.iterdir()),[])
    def test_managed_state(self):
        self.assertEqual(self.install(),0)
        code,body=self.dispatch(b"/api/recovery?id=demo")
        self.assertEqual((code,body["marker"],body["integrity"]),(200,1,1))
        self.assertEqual(body["current"],self.ah.decode())
    def test_small_response_buffer(self):
        p=self.parse(self.raw());body=C.create_string_buffer(4)
        self.assertEqual(self.lib.pf_http_dispatch(self.fd,C.byref(p),body,len(body)),500)
        self.assertEqual(body.value,b"")
