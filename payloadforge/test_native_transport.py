import ctypes as C
import json,os,pathlib,socket,subprocess,tempfile,threading,unittest
import test_native_store as base
from test_native_http import TOKEN

class NativeTransportTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    install=base.NativeStoreTests.install
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        src=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"transport.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",
            *[str(src/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c","http.c","transport.c")],"-o",str(out),"-lz"],check=True)
        cls.lib=C.CDLL(str(out))
        cls.lib.pf_http_listen.argtypes=[C.c_uint,C.POINTER(C.c_uint)];cls.lib.pf_http_listen.restype=C.c_int
        cls.lib.pf_http_serve_one.argtypes=[C.c_int,C.c_int,C.c_char_p,C.c_uint];cls.lib.pf_http_serve_one.restype=C.c_int
        cls.lib.pf_install_initial.argtypes=[C.c_int,C.c_void_p,C.c_size_t,C.c_char_p,C.c_void_p,C.c_size_t,C.c_char_p];cls.lib.pf_install_initial.restype=C.c_int
    def listener(self):
        port=C.c_uint();fd=self.lib.pf_http_listen(0,C.byref(port));self.assertGreaterEqual(fd,0)
        self.addCleanup(os.close,fd)
        return fd,port.value
    def request(self,port,path="/api/health",auth=True,host=None):
        return (f"GET {path} HTTP/1.1\r\nHost: {host or '127.0.0.1:'+str(port)}\r\n"+
                ("Authorization: Bearer "+TOKEN.decode()+"\r\n" if auth else "")+"\r\n").encode()
    def exchange(self,fd,port,parts):
        result=[]
        worker=threading.Thread(target=lambda:result.append(self.lib.pf_http_serve_one(fd,self.fd,TOKEN,2500)),daemon=True)
        worker.start()
        with socket.create_connection(("127.0.0.1",port),timeout=3) as s:
            s.settimeout(3)
            for part in parts:s.sendall(part)
            response=b""
            while True:
                data=s.recv(4096)
                if not data:break
                response+=data
        worker.join(4);self.assertFalse(worker.is_alive());self.assertEqual(result,[1])
        head,body=response.split(b"\r\n\r\n",1)
        self.assertIn(b"Connection: close",head)
        self.assertIn(b"Content-Length: "+str(len(body)).encode(),head)
        return int(head.split(b" ",2)[1]),json.loads(body)
    def test_loopback_and_health(self):
        fd,port=self.listener()
        with socket.fromfd(fd,socket.AF_INET,socket.SOCK_STREAM) as s:self.assertEqual(s.getsockname(),("127.0.0.1",port))
        code,body=self.exchange(fd,port,[self.request(port)])
        self.assertEqual(code,200);self.assertFalse(body["mutation"])
        self.assertEqual(list(self.root.iterdir()),[])
    def test_fragmented_managed_request(self):
        self.assertEqual(self.install(),0);fd,port=self.listener()
        req=self.request(port,"/api/recovery?id=demo")
        code,body=self.exchange(fd,port,[req[:17],req[17:-1],req[-1:]])
        self.assertEqual((code,body["integrity"]),(200,1))
    def test_auth_host_rejection_and_reuse(self):
        fd,port=self.listener()
        self.assertEqual(self.exchange(fd,port,[self.request(port,auth=False)])[0],401)
        self.assertEqual(self.exchange(fd,port,[self.request(port,host="evil.test")])[0],403)
        self.assertEqual(self.exchange(fd,port,[self.request(port)])[0],200)
    def test_reject_wildcard_listener(self):
        with socket.socket() as s:
            s.bind(("0.0.0.0",0));s.listen()
            self.assertEqual(self.lib.pf_http_serve_one(s.fileno(),self.fd,TOKEN,100),-1)
    def test_idle_timeout(self):
        fd,_=self.listener()
        self.assertEqual(self.lib.pf_http_serve_one(fd,self.fd,TOKEN,40),0)
    def test_incomplete_header_times_out(self):
        fd,port=self.listener();result=[]
        with socket.create_connection(("127.0.0.1",port),timeout=2) as s:
            s.sendall(b"GET /api/health HTTP/1.1\r\n")
            thread=threading.Thread(target=lambda:result.append(self.lib.pf_http_serve_one(fd,self.fd,TOKEN,100)),daemon=True)
            thread.start();thread.join(2);self.assertFalse(thread.is_alive());self.assertEqual(result,[-1])
            s.settimeout(2);self.assertEqual(s.recv(1),b"")
    def test_size_limit(self):
        fd,port=self.listener()
        self.assertEqual(self.exchange(fd,port,[b"A"*8192])[0],431)
    def test_invalid_listener_inputs(self):
        p=C.c_uint(99);self.assertEqual(self.lib.pf_http_listen(65536,C.byref(p)),-1);self.assertEqual(p.value,0)
        fd,_=self.listener()
        self.assertEqual(self.lib.pf_http_serve_one(fd,self.fd,TOKEN,0),-1)
