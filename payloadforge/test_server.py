import base64,http.client,json,tempfile,threading,unittest
from payloadforge.engine import Engine
from payloadforge.server import Server
from test_engine import package

class ServerTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.server=Server(Engine(tmp.name),token="local-test-token")
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
        self.addCleanup(self.close_server)
        self.raw,self.sha,self.manifest=package("v1",[("a.txt",b"data","replace-with-backup")])
    def close_server(self):
        self.server.shutdown();self.server.server_close();self.thread.join(2)
    def request(self,method,path,item=None,auth=True,headers=None):
        h={"Authorization":"Bearer local-test-token"} if auth else {}
        if item is not None:h["Content-Type"]="application/json"
        h.update(headers or {})
        c=http.client.HTTPConnection("127.0.0.1",self.server.server_address[1],timeout=3)
        try:
            c.request(method,path,json.dumps(item) if item is not None else None,h)
            r=c.getresponse();return r.status,json.loads(r.read())
        finally:c.close()
    def bundle(self,action="install",confirm=True):
        x={"action":action,"archive":base64.b64encode(self.raw).decode(),"sha256":self.sha,"manifest":self.manifest}
        if action!="plan":x["confirm"]=confirm
        return x
    def test_health(self):self.assertEqual(self.request("GET","/api/health"),(200,{"mode":"host-preview","native":False}))
    def test_auth(self):self.assertEqual(self.request("GET","/api/packages",auth=False)[0],401)
    def test_host(self):self.assertEqual(self.request("GET","/api/packages",headers={"Host":"evil.example"})[0],403)
    def test_origin(self):self.assertEqual(self.request("POST","/api/action",self.bundle(),headers={"Origin":"https://evil.example"})[0],403)
    def test_confirmation(self):self.assertEqual(self.request("POST","/api/action",self.bundle(confirm=False))[0],400)
    def test_plan_and_install(self):
        self.assertEqual(self.request("POST","/api/action",self.bundle("plan"))[0],200)
        self.assertEqual(self.request("GET","/api/packages")[1],[])
        code,result=self.request("POST","/api/action",self.bundle())
        self.assertEqual(code,200);self.assertEqual(result["version"],"v1")
        self.assertEqual(self.request("GET","/api/packages")[1][0]["id"],"demo")
    def test_backup_rollback_uninstall(self):
        self.request("POST","/api/action",self.bundle())
        code,data=self.request("POST","/api/action",{"action":"backup","id":"demo","confirm":True})
        self.assertEqual(code,200)
        self.assertEqual(self.request("POST","/api/action",{"action":"rollback","id":"demo","snapshot":data["snapshot"],"confirm":True})[0],200)
        self.assertEqual(self.request("POST","/api/action",{"action":"uninstall","id":"demo","preserve_config":True,"confirm":True})[0],200)
        self.assertEqual(self.request("GET","/api/packages")[1],[])
    def test_invalid_bundle(self):
        x=self.bundle();x["archive"]="bad!!"
        self.assertEqual(self.request("POST","/api/action",x)[0],400)
    def test_logs(self):
        self.request("POST","/api/action",self.bundle(confirm=False))
        code,logs=self.request("GET","/api/logs")
        self.assertEqual(code,200);self.assertFalse(logs[-1]["ok"]);self.assertNotIn("token",json.dumps(logs))
