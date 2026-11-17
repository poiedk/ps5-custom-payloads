import io,tarfile,unittest,zipfile
from payloadforge.package_type import detect_package

def zpack(*names):
    b=io.BytesIO()
    with zipfile.ZipFile(b,"w") as z:
        for n in names:z.writestr(n,b"test")
    return b.getvalue()
def tpack(*names):
    b=io.BytesIO()
    with tarfile.open(fileobj=b,mode="w:gz") as t:
        for n in names:
            i=tarfile.TarInfo(n);i.size=4;t.addfile(i,io.BytesIO(b"test"))
    return b.getvalue()

class PackageTypeTests(unittest.TestCase):
    def test_elf(self):self.assertEqual(detect_package(b"\x7fELFexample"),("elf","standalone"))
    def test_zip(self):self.assertEqual(detect_package(zpack("a.elf")),("zip","bundle"))
    def test_zip_manifest(self):self.assertEqual(detect_package(zpack("payloadforge-manifest.json","a.txt")),("zip","manifest-bundle"))
    def test_tar(self):self.assertEqual(detect_package(tpack("a.elf")),("tar.gz","bundle"))
    def test_tar_manifest(self):self.assertEqual(detect_package(tpack("payloadforge-manifest.json","a.txt")),("tar.gz","manifest-bundle"))
    def test_unknown(self):
        with self.assertRaises(ValueError):detect_package(b"archive.zip")
    def test_duplicate(self):
        with self.assertRaises(ValueError):detect_package(zpack("a.txt","A.TXT"))
    def test_traversal(self):
        with self.assertRaises(ValueError):detect_package(zpack("../a"))
    def test_nested_manifest(self):self.assertEqual(detect_package(zpack("a/payloadforge-manifest.json")),("zip","bundle"))
