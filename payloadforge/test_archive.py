import hashlib, io, unittest, zipfile
from archive import extract_elf

def fixture(entries):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        for path,data in entries:
            z.writestr(path,data)
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()

class ArchiveTests(unittest.TestCase):
    def test_exact(self):
        raw,d=fixture([("release/tool.elf",b"\x7fELFexample")])
        self.assertEqual(extract_elf(raw,d,"release/tool.elf")[0],b"\x7fELFexample")
    def test_wrong_hash(self):
        raw,d=fixture([("tool.elf",b"\x7fELFexample")])
        with self.assertRaises(ValueError): extract_elf(raw,"0"*64,"tool.elf")
    def test_traversal(self):
        raw,d=fixture([("../outside",b"x"),("tool.elf",b"\x7fELFexample")])
        with self.assertRaises(ValueError): extract_elf(raw,d,"tool.elf")
    def test_not_elf(self):
        raw,d=fixture([("tool.elf",b"wrong")])
        with self.assertRaises(ValueError): extract_elf(raw,d,"tool.elf")
    def test_duplicate_case(self):
        raw,d=fixture([("TOOL.ELF",b"x"),("tool.elf",b"\x7fELFexample")])
        with self.assertRaises(ValueError): extract_elf(raw,d,"tool.elf")
if __name__=="__main__": unittest.main()
