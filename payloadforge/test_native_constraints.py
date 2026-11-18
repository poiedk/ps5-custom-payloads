import ctypes as C
import pathlib, subprocess, tempfile, unittest

class Dep(C.Structure):
    _fields_=[("id",C.c_char*49),("constraint",C.c_char*129)]
class Resource(C.Structure):
    _fields_=[("kind",C.c_uint),("port",C.c_uint),("path",C.c_char*513)]
class State(C.Structure):
    _fields_=[("id",C.c_char*49),("version",C.c_char*65),
        ("dependencies",C.POINTER(Dep)),("conflicts",C.POINTER(Dep)),
        ("dependency_count",C.c_size_t),("conflict_count",C.c_size_t),
        ("resources",C.POINTER(Resource)),("resource_count",C.c_size_t)]

class NativeConstraintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"constraints.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",*[str(base/x) for x in ("core.c","version.c","constraints.c")],"-o",str(out)],check=True)
        cls.lib=C.CDLL(str(out))
        cls.lib.pf_constraint_match.argtypes=[C.c_char_p,C.c_char_p];cls.lib.pf_constraint_match.restype=C.c_int
        cls.lib.pf_state_validate.argtypes=[C.POINTER(State),C.c_size_t];cls.lib.pf_state_validate.restype=C.c_int
    def match(self,v,c):return self.lib.pf_constraint_match(v.encode(),c.encode())
    def graph(self,*rows):
        states=[];keep=[]
        for id,v,deps,conflicts,resources in rows:
            d=(Dep*len(deps))(*(Dep(a.encode(),b.encode()) for a,b in deps))
            c=(Dep*len(conflicts))(*(Dep(a.encode(),b.encode()) for a,b in conflicts))
            rs=(Resource*len(resources))(*(Resource(k,p,s.encode()) for k,p,s in resources))
            keep.extend((d,c,rs))
            states.append(State(id.encode(),v.encode(),d,c,len(d),len(c),rs,len(rs)))
        return self.lib.pf_state_validate((State*len(states))(*states),len(states))
    def row(self,id,version="1",deps=(),conflicts=(),resources=()):
        return (id,version,deps,conflicts,resources)
    def test_constraints(self):
        for v,c,want in [("1.2",">=1,<2",1),("2",">=1,<2",0),("1.0-beta.2","<1.0",1),("1+build","==1",1),("dev-version","*",1),("1","!=1",0)]:
            with self.subTest(v=v,c=c):self.assertEqual(self.match(v,c),want)
    def test_invalid_constraint_even_after_false(self):
        for c in (">2,^1","==","<1,","=1","<1 2","<>1","",">=01"):
            with self.subTest(c=c):self.assertEqual(self.match("1",c),-1)
    def test_missing_incompatible(self):
        a=self.row("a",deps=[("b",">=2")])
        self.assertEqual(self.graph(a),-2)
        self.assertEqual(self.graph(a,self.row("b","1")),-2)
        self.assertEqual(self.graph(a,self.row("b","2")),0)
    def test_cycles(self):
        self.assertEqual(self.graph(self.row("a",deps=[("a","*")])),-3)
        self.assertEqual(self.graph(self.row("a",deps=[("b","*")]),self.row("b",deps=[("a","*")])),-3)
    def test_conflicts(self):
        a=self.row("a",conflicts=[("b",">=2")])
        self.assertEqual(self.graph(a,self.row("b","2")),-4)
        self.assertEqual(self.graph(a,self.row("b","1")),0)
        self.assertEqual(self.graph(self.row("a",conflicts=[("a","*")])),-4)
    def test_ports(self):
        a=self.row("a",resources=[(1,8080,"")])
        self.assertEqual(self.graph(a,self.row("b",resources=[(1,8080,"")])),-4)
        self.assertEqual(self.graph(a,self.row("b",resources=[(2,8080,"")])),0)
    def test_path_overlap(self):
        a=self.row("a",resources=[(3,0,"/data/Demo")])
        self.assertEqual(self.graph(a,self.row("b",resources=[(3,0,"/data/demo/sub")])),-4)
        self.assertEqual(self.graph(a,self.row("b",resources=[(3,0,"/data/demo2")])),0)
    def test_bad_metadata(self):
        for row in (self.row("a",resources=[(1,0,"")]),self.row("a",resources=[(3,0,"/data/../x")]),self.row("a",resources=[(3,0,"/other/x")]),self.row("a",deps=[("b","*"),("b","*")]),self.row("a",conflicts=[("b","^1")])):
            self.assertEqual(self.graph(row),-1)
        self.assertEqual(self.graph(self.row("a"),self.row("a")),-1)
    def test_reverse_dependency(self):
        a=self.row("a",deps=[("b","<2")]);self.assertEqual(self.graph(a,self.row("b","1")),0)
        self.assertEqual(self.graph(a,self.row("b","2")),-2)
