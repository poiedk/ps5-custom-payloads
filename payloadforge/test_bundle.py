import hashlib, io, stat, unittest, zipfile
from bundle import verify_bundle

def fixture(entries):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        for p,data in entries: z.writestr(p,data)
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()
def doc(entries):
    return {"schema_version":1,"id":"demo","version":"v1","files":[{"path":p,"sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"policy":"preserve"} for p,data in entries]}
class BundleTests(unittest.TestCase):
    def test_valid(self):
        e=[("assets/a.png",b"sample"),("config.json",b"{}")]
        raw,d=fixture(e)
        self.assertTrue(verify_bundle(raw,d,doc(e))["verified"])
    def test_unexpected(self):
        e=[("config.json",b"{}")]
        raw,d=fixture(e+[("extra.txt",b"x")])
        with self.assertRaises(ValueError):verify_bundle(raw,d,doc(e))
    def test_missing(self):
        e=[("config.json",b"{}"),("a.txt",b"x")]
        raw,d=fixture(e[:1])
        with self.assertRaises(ValueError):verify_bundle(raw,d,doc(e))
    def test_hash(self):
        e=[("config.json",b"{}")]
        raw,d=fixture([("config.json",b"[]")])
        with self.assertRaises(ValueError):verify_bundle(raw,d,doc(e))
    def test_bad_archive_hash(self):
        e=[("a.txt",b"x")]
        raw,d=fixture(e)
        with self.assertRaises(ValueError):verify_bundle(raw,"0"*64,doc(e))
    def test_symlink(self):
        i=zipfile.ZipInfo("a.txt")
        i.create_system=3
        i.external_attr=(stat.S_IFLNK|0o777)<<16
        raw,d=fixture([(i,b"x")])
        with self.assertRaises(ValueError):verify_bundle(raw,d,doc([("a.txt",b"x")]))
    def test_directory(self):
        e=[("assets/a.txt",b"x")]
        raw,d=fixture([("assets/",b"")]+e)
        self.assertTrue(verify_bundle(raw,d,doc(e))["verified"])
    def test_traversal(self):
        e=[("a.txt",b"x")]
        raw,d=fixture(e+[("../x.txt",b"y")])
        with self.assertRaises(ValueError):verify_bundle(raw,d,doc(e))
if __name__=="__main__":unittest.main()
