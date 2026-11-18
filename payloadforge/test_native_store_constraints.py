import ctypes as C
import hashlib, io, json, unittest, zipfile
import test_native_store as base

class NativeStoreConstraintTests(unittest.TestCase):
    setUp=base.NativeStoreTests.setUp
    @classmethod
    def setUpClass(cls):
        base.NativeStoreTests.setUpClass.__func__(cls)
        for name,args in (
            ("pf_uninstall",[C.c_int,C.c_char_p,C.c_int,C.POINTER(C.c_size_t)]),
            ("pf_rollback",[C.c_int,C.c_char_p,C.c_char_p]),
            ("pf_backup",[C.c_int,C.c_char_p,C.c_void_p]),
            ("pf_backup_verify",[C.c_int,C.c_char_p,C.c_char_p]),
            ("pf_status",[C.c_int,C.c_char_p,C.c_void_p,C.c_void_p])):
            fn=getattr(cls.lib,name);fn.argtypes=args;fn.restype=C.c_int
    def bundle(self,id,version="1",deps=(),conflicts=(),resources=()):
        files=[("settings.json",b"{}", "preserve"),("data.txt",version.encode(),"replace-with-backup")]
        m={"schema_version":3,"id":id,"version":version,"dependencies":list(deps),"conflicts":list(conflicts),"resources":list(resources),"files":[]}
        z=io.BytesIO()
        with zipfile.ZipFile(z,"w") as f:
            for path,raw,policy in files:
                f.writestr(path,raw);m["files"].append({"path":path,"size":len(raw),"sha256":hashlib.sha256(raw).hexdigest(),"policy":policy})
        a=z.getvalue();raw=json.dumps(m).encode()
        return a,len(a),hashlib.sha256(a).hexdigest().encode(),raw,len(raw),hashlib.sha256(raw).hexdigest().encode()
    def install(self,id,version="1",**kw):return self.lib.pf_install_initial(self.fd,*self.bundle(id,version,**kw))
    def update(self,id,version,**kw):return self.lib.pf_install_update(self.fd,*self.bundle(id,version,**kw))
    def dependency(self,id,constraint="*"):return {"id":id,"constraint":constraint}
    def resource(self,type,value):return {"type":type,"value":value}
    def active(self,id):
        app=self.root/"apps"/id
        return app/"generations"/(app/"CURRENT").read_text()
    def status(self,id):
        v=C.create_string_buffer(65);g=C.create_string_buffer(65)
        rc=self.lib.pf_status(self.fd,id.encode(),v,g)
        return rc,v.value.decode(),g.value.decode()
    def uninstall(self,id):
        n=C.c_size_t()
        return self.lib.pf_uninstall(self.fd,id.encode(),1,C.byref(n))
    def snapshot(self,id):
        out=C.create_string_buffer(65)
        self.assertEqual(self.lib.pf_backup(self.fd,id.encode(),out),0)
        return out.value
    def test_install_missing_then_satisfied(self):
        d=[self.dependency("lib",">=2")]
        self.assertEqual(self.install("app",deps=d),-1)
        self.assertEqual(self.status("app")[0],0)
        self.assertEqual(self.install("lib","2"),0)
        self.assertEqual(self.install("app",deps=d),0)
    def test_reverse_update_and_uninstall_blocked(self):
        self.assertEqual(self.install("lib","2"),0)
        self.assertEqual(self.install("app",deps=[self.dependency("lib",">=2,<3")]),0)
        prior=self.active("lib")
        self.assertEqual(self.update("lib","3"),-1)
        self.assertEqual(self.uninstall("lib"),-1)
        self.assertEqual(self.active("lib"),prior)
        self.assertEqual(self.uninstall("app"),0)
        self.assertEqual(self.update("lib","3"),0)
    def test_cycle_blocks_update(self):
        self.assertEqual(self.install("lib"),0)
        self.assertEqual(self.install("app",deps=[self.dependency("lib")]),0)
        before=self.active("lib")
        self.assertEqual(self.update("lib","2",deps=[self.dependency("app")]),-1)
        self.assertEqual(self.active("lib"),before)
    def test_resource_collision_and_persistence(self):
        self.assertEqual(self.install("a",resources=[self.resource("tcp",8080)]),0)
        self.assertEqual(self.install("b",resources=[self.resource("tcp",8080)]),-1)
        self.assertEqual(self.update("a","2",resources=[self.resource("tcp",9090)]),0)
        self.assertEqual(self.install("b",resources=[self.resource("tcp",8080)]),0)
        self.assertEqual(self.install("c",resources=[self.resource("tcp",9090)]),-1)
    def test_declared_conflict_reverse(self):
        self.assertEqual(self.install("a",conflicts=[self.dependency("b",">=2")]),0)
        self.assertEqual(self.install("b","1"),0)
        self.assertEqual(self.update("b","2"),-1)
        self.assertEqual(self.status("b")[1],"1")
    def test_rollback_revalidates_graph(self):
        self.assertEqual(self.install("lib","1"),0)
        snap=self.snapshot("lib")
        self.assertEqual(self.update("lib","2"),0)
        self.assertEqual(self.install("app",deps=[self.dependency("lib",">=2")]),0)
        prior=self.active("lib")
        self.assertEqual(self.lib.pf_rollback(self.fd,b"lib",snap),-1)
        self.assertEqual(self.active("lib"),prior)
        self.assertEqual(self.uninstall("app"),0)
        self.assertEqual(self.lib.pf_rollback(self.fd,b"lib",snap),0)
    def test_backup_and_rollback_metadata(self):
        self.assertEqual(self.install("lib"),0)
        d=[self.dependency("lib")]
        self.assertEqual(self.install("a",deps=d),0)
        snap=self.snapshot("a")
        self.assertEqual(self.lib.pf_backup_verify(self.fd,b"a",snap),0)
        self.assertEqual(self.update("a","2"),0)
        self.assertEqual(self.lib.pf_rollback(self.fd,b"a",snap),0)
        self.assertEqual(self.uninstall("lib"),-1)
    def test_corrupt_peer_metadata_blocks_mutation(self):
        self.assertEqual(self.install("a"),0)
        (self.active("a")/"manifest.json").write_bytes(b"{}")
        self.assertEqual(self.install("b"),-1)
        self.assertEqual(self.status("b")[0],0)
    def test_uninstalled_peer_not_active(self):
        self.assertEqual(self.install("lib"),0)
        self.assertEqual(self.uninstall("lib"),0)
        self.assertEqual(self.install("app",deps=[self.dependency("lib")]),-1)
        self.assertEqual(self.install("lib","2"),0)
        self.assertEqual(self.install("app",deps=[self.dependency("lib")]),0)
