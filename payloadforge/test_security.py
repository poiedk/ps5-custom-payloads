import hashlib, io, stat, unittest, warnings, zipfile
from unittest.mock import patch
from archive import extract_elf, safe_name
from bundle import verify_bundle

ELF=b"\x7fELFtest"

def fixture(entries, compression=zipfile.ZIP_STORED):
    b=io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore",UserWarning)
        with zipfile.ZipFile(b,"w",compression=compression) as z:
            for path,data in entries: z.writestr(path,data)
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest()

def manifest(data):
    return {"schema_version":1,"id":"demo","version":"v1","files":[{"path":"a.txt","sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"policy":"preserve"}]}

class SecurityTests(unittest.TestCase):
    def reject_zip(self, entries, compression=zipfile.ZIP_STORED):
        raw,d=fixture([("tool.elf",ELF)]+entries,compression)
        with self.assertRaises(ValueError): extract_elf(raw,d,"tool.elf")
    def test_absolute_and_windows_paths(self):
        for p in ("/bad.txt","C:/bad.txt","../bad.txt","nested/../bad.txt","a\\b.txt","a//b.txt"):
            with self.subTest(path=p): self.reject_zip([(p,b"x")])
    def test_nul_and_non_string(self):
        for p in ("a\x00.txt",None,12):
            with self.subTest(path=p), self.assertRaises(ValueError): safe_name(p)
    def test_symlink(self):
        i=zipfile.ZipInfo("link.txt"); i.create_system=3; i.external_attr=(stat.S_IFLNK|0o777)<<16
        self.reject_zip([(i,b"target")])
    def test_special_file(self):
        i=zipfile.ZipInfo("fifo.txt"); i.create_system=3; i.external_attr=(stat.S_IFIFO|0o600)<<16
        self.reject_zip([(i,b"")])
    def test_duplicate_exact(self):
        self.reject_zip([("tool.elf",ELF)])
    def test_file_directory_conflict(self):
        self.reject_zip([("folder",b"x"),("folder/a.txt",b"x")])
    def test_archive_limit(self):
        with patch("archive.MAX_ARCHIVE",1): self.reject_zip([])
    def test_member_limit(self):
        with patch("archive.MAX_MEMBER",len(ELF)): self.reject_zip([("large.txt",b"a"*20)])
    def test_total_limit(self):
        with patch("archive.MAX_TOTAL",len(ELF)+1): self.reject_zip([("a.txt",b"xx")])
    def test_count_limit(self):
        with patch("archive.MAX_FILES",1): self.reject_zip([("extra.txt",b"x")])
    def test_compression_ratio(self):
        self.reject_zip([("bomb.txt",b"a"*100000)],zipfile.ZIP_DEFLATED)
    def test_bundle_absolute(self):
        raw,d=fixture([("a.txt",b"x"),("/bad.txt",b"x")])
        with self.assertRaises(ValueError): verify_bundle(raw,d,manifest(b"x"))
    def test_bundle_count(self):
        raw,d=fixture([("a.txt",b"x")])
        with patch("bundle.MAX_FILES",0), self.assertRaises(ValueError): verify_bundle(raw,d,manifest(b"x"))
    def test_bundle_ratio(self):
        data=b"a"*100000
        raw,d=fixture([("a.txt",data)],zipfile.ZIP_DEFLATED)
        with self.assertRaises(ValueError): verify_bundle(raw,d,manifest(data))
