import ctypes as C
import json,unittest
import test_native_http as httpbase
import test_native_store as storebase

TOKEN=httpbase.TOKEN
HOST=httpbase.HOST
AUTH=httpbase.AUTH
ORIGIN=b"Origin: http://127.0.0.1:8765"
CONFIRM=b"X-PayloadForge-Confirm: yes"
LENGTH=b"Content-Length: 0"
class Control(C.Structure):
    _fields_=[("action",C.c_uint),("keep",C.c_uint),("marker",C.c_uint),("kind",C.c_uint),
        ("id",C.c_char*49),("snapshot",C.c_char*65),("current",C.c_char*65),("object_hash",C.c_char*65)]
class NativeControlTests(unittest.TestCase):
    setUp=storebase.NativeStoreTests.setUp
    install=storebase.NativeStoreTests.install
    app=storebase.NativeStoreTests.app
    active=storebase.NativeStoreTests.active
    @classmethod
    def setUpClass(cls):
        httpbase.NativeHTTPTests.setUpClass.__func__(cls)
        cls.lib.pf_http_control_parse.argtypes=[C.c_void_p,C.c_size_t,C.c_uint,C.c_char_p,C.POINTER(Control)]
        cls.lib.pf_http_control_parse.restype=C.c_int
        cls.lib.pf_http_control_dispatch.argtypes=[C.c_int,C.POINTER(Control),C.c_void_p,C.c_size_t]
        cls.lib.pf_http_control_dispatch.restype=C.c_int
    def raw(self,path=b"/api/control/backup?id=demo",headers=(HOST,AUTH,ORIGIN,CONFIRM,LENGTH),method=b"POST"):
        return b"\r\n".join([method+b" "+path+b" HTTP/1.1",*headers,b"",b""])
    def parse(self,raw,expected=200):
        q=Control();self.assertEqual(self.lib.pf_http_control_parse(raw,len(raw),8765,TOKEN,C.byref(q)),expected)
        if expected!=200:self.assertEqual(q.action,0)
        return q
    def dispatch(self,path,expected=200):
        q=self.parse(self.raw(path));out=C.create_string_buffer(2048)
        self.assertEqual(self.lib.pf_http_control_dispatch(self.fd,C.byref(q),out,len(out)),expected)
        return json.loads(out.value)
    def test_explicit_confirmation(self):
        for headers in [(HOST,AUTH,ORIGIN,LENGTH),(HOST,AUTH,CONFIRM,LENGTH),(HOST,AUTH,ORIGIN,CONFIRM),(HOST,AUTH,ORIGIN,b"X-PayloadForge-Confirm: no",LENGTH)]:
            self.parse(self.raw(headers=headers),403)
        self.parse(self.raw(headers=(HOST,ORIGIN,CONFIRM,LENGTH)),401)
        self.parse(self.raw(headers=(HOST,AUTH,CONFIRM,LENGTH,b"Origin: null")),403)
        self.parse(self.raw(headers=(HOST,AUTH,ORIGIN,CONFIRM,CONFIRM,LENGTH)),400)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_readonly_stays_readonly(self):
        r=self.raw();q=httpbase.Request()
        self.assertEqual(self.lib.pf_http_parse(r,len(r),8765,TOKEN,C.byref(q)),405)
        body=C.create_string_buffer(2048)
        self.assertEqual(self.lib.pf_http_dispatch(self.fd,C.byref(q),body,len(body)),404)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_strict_routes(self):
        for p in (b"/api/control/backup?id=../x",b"/api/control/backup?id=demo&x=y",
                  b"/api/control/rollback?id=demo&snapshot="+b"G"*64,b"/api/control/uninstall?id=demo&config=true",
                  b"/api/control/quarantine?id=demo&marker=0&current=x&kind=1&object="+b"a"*64):
            self.parse(self.raw(p),400)
        self.parse(self.raw(b"/api/control/install?id=demo"),404)
        self.parse(self.raw(method=b"GET"),405)
        self.parse(self.raw()+b"body",400)
    def test_backup_and_rollback(self):
        self.assertEqual(self.install(),0)
        snap=self.dispatch(b"/api/control/backup?id=demo")["snapshot"]
        self.assertRegex(snap,r"^[a-f0-9]{64}$")
        self.assertTrue(self.dispatch(b"/api/control/rollback?id=demo&snapshot="+snap.encode())["ok"])
    def test_uninstall_explicit_keep(self):
        self.assertEqual(self.install(),0)
        self.assertTrue(self.dispatch(b"/api/control/uninstall?id=demo&config=keep")["ok"])
        self.assertTrue((self.app()/"CURRENT").read_bytes().endswith(b":keep"))
    def test_quarantine(self):
        self.assertEqual(self.install(),0)
        h=b"a"*64;stage=self.app()/"generations"/(".stage-"+h.decode())
        stage.mkdir(mode=0o700);(stage/"data.txt").write_bytes(b"retained")
        p=b"/api/control/quarantine?id=demo&marker=1&current="+self.ah+b"&kind=1&object="+h
        self.assertTrue(self.dispatch(p)["ok"])
        self.assertEqual((self.root/"recovery-quarantine/demo/staged-generations"/h.decode()/"data.txt").read_bytes(),b"retained")
    def test_invalid_snapshot_conflict(self):
        self.assertEqual(self.install(),0)
        before=(self.app()/"CURRENT").read_bytes()
        result=self.dispatch(b"/api/control/rollback?id=demo&snapshot="+b"a"*64,409)
        self.assertFalse(result["ok"]);self.assertEqual((self.app()/"CURRENT").read_bytes(),before)
    def test_small_output_no_mutation(self):
        self.assertEqual(self.install(),0)
        q=self.parse(self.raw(b"/api/control/uninstall?id=demo&config=drop"))
        out=C.create_string_buffer(16)
        self.assertEqual(self.lib.pf_http_control_dispatch(self.fd,C.byref(q),out,len(out)),500)
        self.assertEqual((self.app()/"CURRENT").read_bytes(),self.ah)
