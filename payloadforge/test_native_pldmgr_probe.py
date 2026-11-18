import ctypes as C,json,os,pathlib,socket,subprocess,tempfile,threading,unittest
import test_native_store as base
from test_native_http import TOKEN

class NativePLDMGRProbeTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    @classmethod
    def setUpClass(cls):
        work=tempfile.TemporaryDirectory();cls.addClassCleanup(work.cleanup);p=pathlib.Path(work.name)
        stub=socket.socket(socket.AF_INET,socket.SOCK_STREAM);cls.addClassCleanup(stub.close)
        stub.bind(("127.0.0.1",0));stub.listen(4);stub.settimeout(3)
        cls.stub=stub;cls.port=stub.getsockname()[1]
        src=pathlib.Path(__file__).resolve().parent/"native";out=p/"probe.so"
        subprocess.run(["python3",str(src/"embed_ui.py"),str(p/"ui_assets.h")],check=True)
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC","-DPF_ENABLE_MANAGED","-DPF_ENABLE_UI","-DPF_TEST_PLDMGR_PORT="+str(cls.port),"-I"+str(p),
            *[str(src/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c","http.c","transport.c")],"-o",str(out),"-lz"],check=True)
        cls.lib=C.CDLL(str(out))
        cls.lib.pf_http_listen.argtypes=[C.c_uint,C.POINTER(C.c_uint)];cls.lib.pf_http_listen.restype=C.c_int
        cls.lib.pf_http_serve_managed_one.argtypes=[C.c_int,C.c_int,C.c_char_p,C.c_uint];cls.lib.pf_http_serve_managed_one.restype=C.c_int
    def call(self,request_reply=None,auth=True,path="/api/pldmgr/version"):
        received=[];errors=[]
        def upstream():
            try:
                with self.stub.accept()[0] as s:
                    s.settimeout(2);buf=b""
                    while b"\r\n\r\n" not in buf:
                        chunk=s.recv(1024)
                        if not chunk:break
                        buf+=chunk
                    received.append(buf)
                    if request_reply:s.sendall(request_reply)
            except Exception as e:errors.append(str(e))
        if request_reply is not None:
            t=threading.Thread(target=upstream,daemon=True);t.start()
        port=C.c_uint();fd=self.lib.pf_http_listen(0,C.byref(port));self.assertGreaterEqual(fd,0)
        result=[]
        host=threading.Thread(target=lambda:result.append(self.lib.pf_http_serve_managed_one(fd,self.fd,TOKEN,3500)),daemon=True);host.start()
        try:
            with socket.create_connection(("127.0.0.1",port.value),timeout=3) as s:
                s.settimeout(5)
                authline="Authorization: Bearer "+TOKEN.decode()+"\r\n" if auth else ""
                s.sendall(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port.value}\r\n{authline}\r\n".encode())
                raw=b""
                while True:
                    b=s.recv(4096)
                    if not b:break
                    raw+=b
            host.join(5);self.assertFalse(host.is_alive());self.assertEqual(result,[1])
        finally:os.close(fd)
        if request_reply is not None:
            t.join(4);self.assertFalse(t.is_alive());self.assertEqual(errors,[])
            self.assertEqual(received,[f"GET /version HTTP/1.1\r\nHost: 127.0.0.1:{self.port}\r\nConnection: close\r\nAccept: text/plain\r\n\r\n".encode()])
        else:
            self.stub.settimeout(.08)
            try:
                with self.assertRaises(TimeoutError):self.stub.accept()
            finally:self.stub.settimeout(3)
        h,b=raw.split(b"\r\n\r\n",1)
        self.assertEqual(list(self.root.iterdir()),[])
        return int(h.split(b" ")[1]),json.loads(b)
    def reply(self,body=b"0.6.3",status=b"200 OK",extra=b"",mime=b"text/plain"):
        return b"HTTP/1.1 "+status+b"\r\nContent-Type: "+mime+b"\r\nContent-Length: "+str(len(body)).encode()+b"\r\n"+extra+b"\r\n"+body
    def test_exact_version_only(self):
        code,body=self.call(self.reply())
        self.assertEqual(code,200);self.assertEqual(body,{"reachable":True,"reported_version":"0.6.3","identity_verified":False,"read_only":True})
    def test_auth_before_outbound_probe(self):
        self.assertEqual(self.call(auth=False)[0],401)
    def test_no_arbitrary_path_or_query(self):
        self.assertEqual(self.call(path="/api/pldmgr/version?url=external")[0],404)
    def test_bad_responses_fail_closed(self):
        for reply in (self.reply(b"not version"),self.reply(b"0.6.3",status=b"302 Found",extra=b"Location: https://example.test/\r\n"),
                      self.reply(b"1.2.3",extra=b"Content-Length: 5\r\n"),self.reply(b"1.2.3",extra=b"Transfer-Encoding: chunked\r\n"),
                      self.reply(b"1.2.3",mime=b"application/json"),self.reply(b"1.2.3\""),self.reply(b"1.2.3")+b"extra"):
            with self.subTest(reply=reply):
                code,body=self.call(reply);self.assertEqual(code,200);self.assertFalse(body["reachable"]);self.assertEqual(body["reported_version"],"")
