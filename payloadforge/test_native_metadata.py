import ctypes as C
import unittest
import test_native_manifest as base
from test_native_constraints import Dep, Resource, State

class Metadata(C.Structure):
    _fields_=[("dependency_count",C.c_size_t),("conflict_count",C.c_size_t),("resource_count",C.c_size_t),
        ("dependencies",Dep*64),("conflicts",Dep*64),("resources",Resource*128)]

class NativeMetadataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base.NativeManifestTests.setUpClass.__func__(cls)
        cls.lib.pf_manifest_parse_metadata.argtypes=cls.lib.pf_manifest_parse.argtypes+[C.POINTER(Metadata)]
        cls.lib.pf_manifest_parse_metadata.restype=C.c_int
        cls.lib.pf_bundle_verify_metadata.argtypes=cls.lib.pf_bundle_verify.argtypes+[C.POINTER(Metadata)]
        cls.lib.pf_bundle_verify_metadata.restype=C.c_int
        cls.lib.pf_state_validate.argtypes=[C.POINTER(State),C.c_size_t]
        cls.lib.pf_state_validate.restype=C.c_int
    def doc(self):
        return {**base.doc(),"dependencies":[{"id":"library","constraint":">=2,<3"}],
                "conflicts":[{"id":"other","constraint":"*"}],
                "resources":[{"type":"tcp","value":8765},{"type":"path","value":"/data/demo"}]}
    def parse(self,d,ok=True):
        raw=base.raw(d) if isinstance(d,dict) else d
        m=base.Manifest();f=(base.File*8)();meta=Metadata()
        rc=self.lib.pf_manifest_parse_metadata(raw,len(raw),C.byref(m),f,8,C.byref(meta))
        self.assertEqual(rc,0 if ok else -1)
        if not ok:
            self.assertEqual(m.count,0)
            self.assertEqual((meta.dependency_count,meta.conflict_count,meta.resource_count),(0,0,0))
        return m,meta
    def test_metadata(self):
        m,x=self.parse(self.doc())
        self.assertEqual(m.id,b"demo")
        self.assertEqual((x.dependency_count,x.conflict_count,x.resource_count),(1,1,2))
        self.assertEqual(x.dependencies[0].constraint,b">=2,<3")
        self.assertEqual(x.resources[0].port,8765)
        self.assertEqual(x.resources[1].path,b"/data/demo")
    def test_state_validation(self):
        m,x=self.parse(self.doc())
        s=State(m.id,m.version,x.dependencies,x.conflicts,x.dependency_count,x.conflict_count,x.resources,x.resource_count)
        self.assertEqual(self.lib.pf_state_validate((State*1)(s),1),-2)
        self.assertEqual(self.lib.pf_state_validate((State*2)(s,State(b"library",b"2")),2),0)
        self.assertEqual(self.lib.pf_state_validate((State*3)(s,State(b"library",b"2"),State(b"other",b"1")),3),-4)
    def test_legacy_fails_closed(self):
        self.assertIsNone(base.NativeManifestTests.parse(self,self.doc()))
        self.assertFalse(base.NativeManifestTests.verify(self,base.archive([("settings.json",b"{}")]),self.doc()))
    def test_duplicate_dependency(self):
        d=self.doc();d["dependencies"]*=2;self.parse(d,False)
    def test_invalid_constraint(self):
        d=self.doc();d["dependencies"][0]["constraint"]=">2,^1";self.parse(d,False)
    def test_invalid_resources(self):
        for resource in ({"type":"tcp","value":True},{"type":"udp","value":65536},{"type":"tcp","value":"80"},{"type":"path","value":"/data/../a"},{"type":"path","value":"/system/a"},{"type":"path","value":2},{"type":"other","value":22}):
            with self.subTest(resource=resource):self.parse({**self.doc(),"resources":[resource]},False)
    def test_duplicate_resource(self):
        self.parse({**self.doc(),"resources":[{"type":"path","value":"/data/Demo"},{"type":"path","value":"/data/demo"}]},False)
    def test_duplicate_top_level(self):
        d=base.raw(self.doc()).replace(b'"dependencies":',b'"dependencies":[],"dependencies":')
        self.parse(d,False)
    def test_schema_mismatch(self):
        self.parse({**self.doc(),"schema_version":2},False)
    def test_bounds(self):
        self.parse({**self.doc(),"dependencies":[{"id":"p"+str(i),"constraint":"*"} for i in range(65)]},False)
        self.parse({**self.doc(),"resources":[{"type":"tcp","value":i+1} for i in range(129)]},False)
    def test_bundle_metadata(self):
        d=base.raw(self.doc());a=base.archive([("settings.json",b"{}")])
        m=base.Manifest();f=(base.File*8)();x=Metadata()
        verify=self.lib.pf_bundle_verify_metadata
        self.assertEqual(verify(a,len(a),base.sha(a),d,len(d),base.sha(d),C.byref(m),f,8,C.byref(x)),0)
        self.assertEqual(x.dependency_count,1)
        bad=base.archive([("settings.json",b"xx")])
        self.assertEqual(verify(bad,len(bad),base.sha(bad),d,len(d),base.sha(d),C.byref(m),f,8,C.byref(x)),-1)
        self.assertEqual((m.count,x.dependency_count),(0,0))
        self.assertEqual(verify(a,len(a),base.sha(a),d,len(d),b"0"*64,C.byref(m),f,8,C.byref(x)),-1)
