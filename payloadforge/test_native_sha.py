import ctypes, hashlib, pathlib, random, subprocess, tempfile, unittest
class NativeShaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp=tempfile.TemporaryDirectory(); cls.addClassCleanup(cls.tmp.cleanup)
        src=pathlib.Path(__file__).parent/"native"/"sha256.c"
        out=pathlib.Path(cls.tmp.name)/"sha.so"
        subprocess.run(["cc","-std=c11","-Wall","-Wextra","-Werror","-shared","-fPIC",str(src),"-o",str(out)],check=True)
        cls.lib=ctypes.CDLL(str(out)); cls.lib.pf_sha256_hex.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_void_p];cls.lib.pf_sha256_hex.restype=None
        cls.lib.pf_sha256_matches.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.c_char_p];cls.lib.pf_sha256_matches.restype=ctypes.c_int
    def check_hash(self,raw):
        out=ctypes.create_string_buffer(65);self.lib.pf_sha256_hex(raw,len(raw),out)
        self.assertEqual(out.value.decode(),hashlib.sha256(raw).hexdigest())
    def test_known(self):
        for raw in (b"",b"abc",b"a"*1000000):self.check_hash(raw)
    def test_boundaries(self):
        for n in (1,55,56,57,63,64,65,119,120,127,128,129,4096):self.check_hash(bytes(i%256 for i in range(n)))
    def test_random(self):
        rng=random.Random(42)
        for n in (3,101,512,999,16384):self.check_hash(rng.randbytes(n))
    def test_matches(self):
        raw=b"abc";h=hashlib.sha256(raw).hexdigest().encode()
        self.assertEqual(self.lib.pf_sha256_matches(raw,len(raw),h),1)
        self.assertEqual(self.lib.pf_sha256_matches(b"abd",3,h),0)
        self.assertEqual(self.lib.pf_sha256_matches(raw,len(raw),b"bad"),0)
