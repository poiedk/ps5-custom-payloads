import ctypes as C
import pathlib, random, subprocess, tempfile, unittest, zlib
def compressed(raw):
    obj=zlib.compressobj(wbits=-15)
    return obj.compress(raw)+obj.flush()
class NativeInflateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        tmp=tempfile.TemporaryDirectory();cls.addClassCleanup(tmp.cleanup)
        base=pathlib.Path(__file__).resolve().parent/"native";out=pathlib.Path(tmp.name)/"inflate.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",str(base/"inflate.c"),"-lz","-o",str(out)],check=True)
        cls.lib=C.CDLL(str(out))
        cls.lib.pf_inflate_exact.argtypes=[C.c_void_p,C.c_size_t,C.c_size_t,C.POINTER(C.c_void_p)]
        cls.lib.pf_inflate_exact.restype=C.c_int
        cls.lib.pf_inflate_free.argtypes=[C.c_void_p];cls.lib.pf_inflate_free.restype=None
    def inflate(self,b,expected):
        out=C.c_void_p(1)
        status=self.lib.pf_inflate_exact(b,len(b),expected,C.byref(out))
        if status:
            self.assertFalse(out.value);return None
        try:return C.string_at(out,expected)
        finally:self.lib.pf_inflate_free(out)
    def test_vectors(self):
        rng=random.Random(31)
        for n in (0,1,64,4096,65536):
            raw=rng.randbytes(n);self.assertEqual(self.inflate(compressed(raw),n),raw)
    def test_text(self):
        raw=(b"hello payloadforge\n"*30)
        self.assertEqual(self.inflate(compressed(raw),len(raw)),raw)
    def test_wrong_length(self):
        raw=b"test"*20;b=compressed(raw)
        for n in (0,len(raw)-1,len(raw)+1):
            self.assertIsNone(self.inflate(b,n))
    def test_truncated(self):
        b=compressed(b"hello world")
        for n in range(len(b)):self.assertIsNone(self.inflate(b[:n],11))
    def test_trailing(self):
        self.assertIsNone(self.inflate(compressed(b"test")+b"x",4))
        self.assertIsNone(self.inflate(compressed(b"test")+compressed(b"test"),4))
    def test_wrong_format(self):
        self.assertIsNone(self.inflate(zlib.compress(b"test"),4))
    def test_expansion_limit(self):
        raw=b"A"*1000000
        self.assertIsNone(self.inflate(compressed(raw),len(raw)))
    def test_member_limit(self):
        self.assertIsNone(self.inflate(compressed(b"x"),64*1024*1024+1))
