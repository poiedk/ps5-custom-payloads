import ctypes, pathlib, subprocess, tempfile, unittest
from payloadforge.archive import safe_name
from payloadforge.dependencies import ID

class NativeVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native"
        out=pathlib.Path(cls.tmp.name)/"core.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",str(base/"core.c"),"-o",str(out)],check=True)
        cls.lib=ctypes.CDLL(str(out))
        for name in ("pf_id_valid","pf_path_valid","pf_sha_valid","pf_format_detect"):
            f=getattr(cls.lib,name);f.argtypes=[ctypes.c_char_p,ctypes.c_size_t];f.restype=ctypes.c_int
    def test_path_vectors(self):
        for value in ("a.txt","nested/a.txt","a/../b","../a","/a","a\\b","a:b","a//b","a\x00b",".","..",""):
            with self.subTest(value=value):
                try:safe_name(value);want=True
                except ValueError:want=False
                b=value.encode()
                self.assertEqual(bool(self.lib.pf_path_valid(b,len(b))),want)
    def test_id_vectors(self):
        for value in ("demo","demo-1","../a","A","-a","a_b","a"*49,""):
            b=value.encode()
            self.assertEqual(bool(self.lib.pf_id_valid(b,len(b))),bool(ID.fullmatch(value)))
    def test_sha_vectors(self):
        for raw,expected in ((b"a"*64,True),(b"A"*64,True),(b"g"*64,False),(b"0"*63,False)):
            self.assertEqual(bool(self.lib.pf_sha_valid(raw,len(raw))),expected)
    def test_magic_vectors(self):
        for raw,expected in ((b"\x7fELF",1),(b"PK\x03\x04",2),(b"\x1f\x8b",3),(b"zip",0)):
            self.assertEqual(self.lib.pf_format_detect(raw,len(raw)),expected)
