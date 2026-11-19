import json,pathlib,socket,subprocess,tempfile,unittest
import test_native_store as base
import test_native_managed_runtime as runtime

class NativeUITests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    args=runtime.NativeManagedRuntimeTests.args
    start=runtime.NativeManagedRuntimeTests.start
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        work=pathlib.Path(tmp.name)
        cls.src=pathlib.Path(__file__).resolve().parent/"native";cls.bin=work/"managed-ui"
        subprocess.run(["python3",str(cls.src/"embed_ui.py"),str(work/"ui_assets.h")],check=True)
        paths=[str(cls.src/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c","http.c","transport.c","runtime.c")]
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-DPF_ENABLE_MANAGED","-DPF_ENABLE_UI","-I"+str(work)]+paths+["-o",str(cls.bin),"-lz"],check=True)
    def exchange(self,port,path="/",headers=(),method="GET",body=b""):
        head=("\r\n".join([f"{method} {path} HTTP/1.1",*headers,"",""])).encode()
        with socket.create_connection(("127.0.0.1",port),timeout=3) as conn:
            conn.settimeout(12);conn.sendall(head+body)
            result=b""
            while True:
                chunk=conn.recv(4096)
                if not chunk:break
                result+=chunk
        h,b=result.split(b"\r\n\r\n",1)
        status=int(h.split(b" ")[1]);meta={}
        for row in h.split(b"\r\n")[1:]:
            k,v=row.split(b":",1);meta[k.lower()]=v.strip()
        self.assertEqual(int(meta[b"content-length"]),len(b))
        return status,meta,b
    def test_static_assets_and_csp(self):
        port,token=self.start()
        host=(f"Host: 127.0.0.1:{port}",)
        for url,name,mime in (("/","index.html",b"text/html"),("/ui.css","ui.css",b"text/css"),("/ui.js","ui.js",b"application/javascript")):
            code,h,b=self.exchange(port,url,host)
            self.assertEqual(code,200);self.assertEqual(b,(self.src/"web"/name).read_bytes())
            self.assertTrue(h[b"content-type"].startswith(mime))
            self.assertEqual(h[b"x-content-type-options"],b"nosniff")
            self.assertEqual(h[b"x-frame-options"],b"DENY")
            self.assertIn(b"connect-src 'self'",h[b"content-security-policy"])
            self.assertNotIn(b"unsafe-inline",h[b"content-security-policy"])
            self.assertNotIn(token.encode(),b)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_static_origin_and_host(self):
        port,_=self.start();host=f"Host: 127.0.0.1:{port}"
        for headers in (("Host: evil.test",),(host,"Origin: https://evil.test"),(host,host),(host,"Content-Length: 1")):
            code,_,_=self.exchange(port,"/",headers)
            self.assertIn(code,(400,403))
        self.assertEqual(self.exchange(port,"/",(host,"Transfer-Encoding: chunked"))[0],400)
    def test_api_remains_private(self):
        port,token=self.start();host=f"Host: 127.0.0.1:{port}"
        for path in ("/api/health","/api/recovery?id=demo"):
            self.assertEqual(self.exchange(port,path,(host,))[0],401)
        code,_,body=self.exchange(port,"/api/health",(host,"Authorization: Bearer "+token))
        self.assertEqual(code,200);self.assertTrue(json.loads(body)["mutation"])
        self.assertEqual(self.exchange(port,"/../store.c",(host,"Authorization: Bearer "+token))[0],404)
        self.assertEqual(self.exchange(port,"/ui.js",(host,"Content-Length: 0"),"POST")[0],401)
        self.assertEqual(self.exchange(port,"/ui.js",(host,"Authorization: Bearer "+token,f"Origin: http://127.0.0.1:{port}","X-PayloadForge-Confirm: yes","Content-Length: 0"),"POST")[0],404)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_catalog_reference_authenticated(self):
        from payloadforge.catalog_preview import reference
        port,token=self.start();host=f"Host: 127.0.0.1:{port}"
        self.assertEqual(self.exchange(port,"/api/catalog",(host,))[0],401)
        status,_,body=self.exchange(port,"/api/catalog",(host,"Authorization: Bearer "+token))
        self.assertEqual(status,200);self.assertEqual(json.loads(body),reference())
        self.assertEqual(list(self.root.iterdir()),[])
    def test_ui_source_policy(self):
        html=(self.src/"web/index.html").read_text()
        js=(self.src/"web/ui.js").read_text()
        self.assertIn('src="/ui.js"',html);self.assertIn('href="/ui.css"',html)
        for forbidden in ("localStorage","sessionStorage","document.cookie","innerHTML","eval("):
            self.assertNotIn(forbidden,js)
        self.assertIn('new Blob([head,m,a]',js)
        self.assertIn('verified.blob',js)
        self.assertIn('X-PayloadForge-Confirm',js)
        self.assertIn('credentials:"omit"',js)
