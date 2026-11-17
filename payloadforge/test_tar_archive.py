import hashlib,io,tarfile,unittest
from unittest.mock import patch
from payloadforge.tar_archive import extract_tar_elf

ELF=b"\x7fELFexample"
def fixture(entries):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        for name,data in entries:
            i=name if isinstance(name,tarfile.TarInfo) else tarfile.TarInfo(name)
            i.size=len(data)
            t.addfile(i,io.BytesIO(data))
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()

class TarTests(unittest.TestCase):
    def run_extract(self,extras=(),**kwargs):
        raw,d=fixture([("tool.elf",ELF),*extras])
        return extract_tar_elf(raw,d,"tool.elf",**kwargs)
    def test_valid(self):
        self.assertEqual(self.run_extract([("README.md",b"doc")],docs_only=True)[0],ELF)
    def test_hash(self):
        raw,d=fixture([("tool.elf",ELF)])
        with self.assertRaises(ValueError):extract_tar_elf(raw,"0"*64,"tool.elf")
    def test_paths(self):
        for name in ("/bad","../bad","A/../bad","C:/bad","a\\b"):
            with self.subTest(name=name),self.assertRaises(ValueError):self.run_extract([(name,b"x")])
    def test_symlinks_and_hardlinks(self):
        for kind in (tarfile.SYMTYPE,tarfile.LNKTYPE,tarfile.FIFOTYPE):
            i=tarfile.TarInfo("link"); i.type=kind;i.linkname="tool.elf"
            with self.assertRaises(ValueError):self.run_extract([(i,b"")])
    def test_duplicates(self):
        with self.assertRaises(ValueError):self.run_extract([("TOOL.ELF",ELF)])
    def test_conflict(self):
        with self.assertRaises(ValueError):self.run_extract([("a",b"x"),("a/b",b"x")])
    def test_count(self):
        with patch("payloadforge.tar_archive.MAX_FILES",1),self.assertRaises(ValueError):self.run_extract([("a",b"x")])
    def test_member(self):
        with patch("payloadforge.tar_archive.MAX_MEMBER",len(ELF)),self.assertRaises(ValueError):self.run_extract([("a",b"x"*100)])
    def test_total(self):
        with patch("payloadforge.tar_archive.MAX_TOTAL",len(ELF)),self.assertRaises(ValueError):self.run_extract([("a",b"x")])
    def test_bomb(self):
        with self.assertRaises(ValueError):self.run_extract([("a",b"x"*1000000)])
    def test_companions(self):
        with self.assertRaises(ValueError):self.run_extract([("config.json",b"{}")],docs_only=True)
    def test_missing(self):
        raw,d=fixture([("tool.elf",ELF)])
        with self.assertRaises(ValueError):extract_tar_elf(raw,d,"other.elf")
