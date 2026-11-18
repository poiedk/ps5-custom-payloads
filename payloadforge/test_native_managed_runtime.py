import hashlib,io,json,os,pathlib,socket,struct,subprocess,tempfile,unittest,zipfile
import test_native_store as base

class NativeManagedRuntimeTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    app=base.NativeStoreTests.app
    active=base.NativeStoreTests.active
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        src=pathlib.Path(__file__).resolve().parent/"native";cls.bin=pathlib.Path(tmp.name)/"managed"
        paths=[str(src/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c","http.c","transport.c","runtime.c")]
        cmd=["cc","-std=c11","-Wall","-Wextra","-Werror","-DPF_ENABLE_MANAGED"]
        subprocess.run(cmd+paths+["-o",str(cls.bin),"-lz"],check=True)
        cls.restricted=pathlib.Path(tmp.name)/"restricted"
        subprocess.run(cmd+["-DPF_PS5_BUILD"]+paths+["-o",str(cls.restricted),"-lz"],check=True)
    def args(self,bin=None,mode="--serve-managed"):
        return [str(bin or self.bin),mode,"--root",str(self.root),"--port","0","--seconds","30"]
    def start(self):
        p=subprocess.Popen(self.args(),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def close():
            if p.poll() is None:p.terminate()
            try:p.communicate(timeout=12)
            except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=3)
        self.addCleanup(close)
        self.assertEqual(p.stdout.readline().strip(),"PayloadForge managed development runtime")
        port=int(p.stdout.readline().strip().split(":")[-1])
        token=p.stdout.readline().strip().removeprefix("Session token: ")
        self.assertRegex(token,r"^[a-f0-9]{64}$")
        return port,token
    def header(self,port,token,path,body=b"",upload=False,confirm=True,method="POST"):
        lines=[f"{method} {path} HTTP/1.1",f"Host: 127.0.0.1:{port}",f"Authorization: Bearer {token}"]
        if method=="POST":
            lines += [f"Origin: http://127.0.0.1:{port}",f"Content-Length: {len(body)}"]
            if confirm:lines+=["X-PayloadForge-Confirm: yes"]
            if upload:lines+=["Content-Type: application/octet-stream"]
        return ("\r\n".join(lines)+"\r\n\r\n").encode()
    def talk(self,port,parts):
        with socket.create_connection(("127.0.0.1",port),timeout=6) as s:
            s.settimeout(12)
            for chunk in parts:s.sendall(chunk)
            reply=b""
            while True:
                data=s.recv(4096)
                if not data:break
                reply+=data
        head,body=reply.split(b"\r\n\r\n",1)
        self.assertIn(b"Connection: close",head)
        return int(head.split(b" ")[1]),json.loads(body)
    def package(self,version="1.0.0",data=b"v1"):
        m={"schema_version":3,"id":"demo","version":version,"files":[],"dependencies":[],"conflicts":[],"resources":[]}
        stream=io.BytesIO()
        with zipfile.ZipFile(stream,"w") as z:
            for p,b,policy in [("settings.json",b"{}","preserve"),("assets/demo.txt",data,"replace-with-backup")]:
                z.writestr(p,b);m["files"].append({"path":p,"sha256":hashlib.sha256(b).hexdigest(),"size":len(b),"policy":policy})
        a=stream.getvalue();m=json.dumps(m).encode()
        return b"PFU1"+struct.pack(">II",len(m),len(a))+hashlib.sha256(m).hexdigest().encode()+hashlib.sha256(a).hexdigest().encode()+m+a
    def upload(self,port,token,path,body):
        h=self.header(port,token,"/api/upload/"+path,body,True)
        return self.talk(port,[h[:20],h[20:]+body[:7],body[7:]])
    def control(self,port,token,path):
        return self.talk(port,[self.header(port,token,"/api/control/"+path)])
    def test_no_default_or_readonly_mode(self):
        for args in ([str(self.bin)],self.args(mode="--serve-read-only")):
            self.assertEqual(subprocess.run(args,capture_output=True,timeout=2).returncode,2)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_ps5_build_restricts_root(self):
        self.assertEqual(subprocess.run(self.args(self.restricted),capture_output=True,timeout=2).returncode,2)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_health_and_confirm(self):
        port,token=self.start()
        code,body=self.talk(port,[self.header(port,token,"/api/health",method="GET")])
        self.assertEqual(code,200);self.assertTrue(body["mutation"])
        self.assertEqual(self.talk(port,[self.header(port,token,"/api/control/backup?id=demo",confirm=False)])[0],403)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_reject_upload_before_body(self):
        port,token=self.start();b=self.package()
        h=self.header(port,"0"*64,"/api/upload/install",b,True)
        self.assertEqual(self.talk(port,[h])[0],401)
        self.assertEqual(list(self.root.iterdir()),[])
    def test_partial_upload_no_mutation(self):
        port,token=self.start();b=self.package()
        h=self.header(port,token,"/api/upload/install",b,True)
        with socket.create_connection(("127.0.0.1",port),timeout=2) as s:
            s.settimeout(4);s.sendall(h+b[:100]);s.shutdown(socket.SHUT_WR)
            self.assertEqual(s.recv(1),b"")
        self.assertEqual(list(self.root.iterdir()),[])
    def test_upload_and_backup_lifecycle(self):
        port,token=self.start();b=self.package()
        code,p=self.upload(port,token,"verify",b);self.assertEqual(code,200);self.assertFalse(p["state_checked"])
        self.assertEqual(list(self.root.iterdir()),[])
        self.assertEqual(self.upload(port,token,"install",b)[0],200)
        (self.active()/"data/settings.json").write_bytes(b"user")
        snap=self.control(port,token,"backup?id=demo")[1]["snapshot"]
        self.assertRegex(snap,r"^[a-f0-9]{64}$")
        self.assertEqual(self.upload(port,token,"upgrade",self.package("2.0.0",b"v2"))[0],200)
        self.assertEqual((self.active()/"data/settings.json").read_bytes(),b"user")
        self.assertEqual(self.control(port,token,"rollback?id=demo&snapshot="+snap)[0],200)
        self.assertEqual((self.active()/"data/assets/demo.txt").read_bytes(),b"v1")
        self.assertEqual(self.control(port,token,"uninstall?id=demo&config=keep")[0],200)
        self.assertTrue((self.app()/"CURRENT").read_bytes().endswith(b":keep"))
    def test_corrupt_upload_no_write(self):
        port,token=self.start();b=bytearray(self.package());b[-1]^=1
        self.assertEqual(self.upload(port,token,"install",bytes(b))[0],409)
        self.assertEqual(list(self.root.iterdir()),[])
