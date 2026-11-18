import json,os,pathlib,re,socket,subprocess,tempfile,unittest
import test_native_store as base

class NativeRuntimeTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        src=pathlib.Path(__file__).resolve().parent/"native";cls.bin=pathlib.Path(tmp.name)/"runtime"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror",
            *[str(src/x) for x in ("core.c","sha256.c","zip.c","manifest.c","store.c","version.c","constraints.c","inflate.c","tar.c","http.c","transport.c","runtime.c")],
            "-o",str(cls.bin),"-lz"],check=True)
    def args(self,root=None,seconds="3"):
        return [str(self.bin),"--serve-read-only","--root",str(root or self.root),"--port","0","--seconds",seconds]
    def start(self,seconds="3"):
        p=subprocess.Popen(self.args(seconds=seconds),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        def close():
            if p.poll() is None:p.terminate()
            try:p.communicate(timeout=3)
            except subprocess.TimeoutExpired:p.kill();p.communicate(timeout=3)
        self.addCleanup(close)
        self.assertEqual(p.stdout.readline().strip(),"PayloadForge read-only runtime")
        port=int(p.stdout.readline().strip().split(":")[-1])
        token=p.stdout.readline().strip().removeprefix("Session token: ")
        self.assertRegex(token,r"^[a-f0-9]{64}$")
        return p,port,token
    def exchange(self,port,token,path="/api/health"):
        with socket.create_connection(("127.0.0.1",port),timeout=2) as conn:
            conn.sendall(f"GET {path} HTTP/1.1\r\nHost: 127.0.0.1:{port}\r\nAuthorization: Bearer {token}\r\n\r\n".encode())
            raw=b""
            while True:
                data=conn.recv(4096)
                if not data:break
                raw+=data
        head,body=raw.split(b"\r\n\r\n",1)
        return int(head.split(b" ")[1]),json.loads(body)
    def test_default_no_listener(self):
        p=subprocess.run([str(self.bin)],capture_output=True,timeout=2)
        self.assertEqual(p.returncode,2);self.assertEqual(p.stdout,b"")
        self.assertEqual(list(self.root.iterdir()),[])
    def test_bad_args(self):
        for seconds in ("0","301","-1","abc"):
            self.assertEqual(subprocess.run(self.args(seconds=seconds),capture_output=True,timeout=2).returncode,2)
    def test_missing_root_not_created(self):
        p=self.root/"absent"
        self.assertEqual(subprocess.run(self.args(p),capture_output=True,timeout=2).returncode,1)
        self.assertFalse(p.exists())
    def test_symlink_and_nonprivate(self):
        other=self.root/"other";other.mkdir(mode=0o755)
        link=self.root/"link";link.symlink_to(self.root)
        for p in (other,link,link/"other"):
            self.assertEqual(subprocess.run(self.args(p),capture_output=True,timeout=2).returncode,1)
    def test_runtime_network(self):
        p,port,token=self.start()
        self.assertEqual(self.exchange(port,"0"*64)[0],401)
        self.assertEqual(self.exchange(port,token)[0],200)
        code,body=self.exchange(port,token,"/api/recovery?id=demo")
        self.assertEqual((code,body["marker"]),(200,0))
        self.assertEqual(list(self.root.iterdir()),[])
        p.terminate();self.assertEqual(p.wait(timeout=3),0)
    def test_fresh_token_and_session_expiry(self):
        p,port,token=self.start("1")
        self.assertEqual(p.wait(timeout=3),0)
        with self.assertRaises(OSError):socket.create_connection(("127.0.0.1",port),timeout=1)
        _,port2,token2=self.start("2")
        self.assertNotEqual(token,token2)
        self.assertEqual(self.exchange(port2,token)[0],401)
