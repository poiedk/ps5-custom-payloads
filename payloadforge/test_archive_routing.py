import hashlib,io,tarfile,tempfile,unittest,zipfile
from pathlib import Path
from zip_release import prepare_zip
import update
from unittest.mock import patch

SOURCE={"id":"demo","repo":"example/demo","name":"Demo","pattern":r"demo\.tar\.gz","archive":{"member":"demo.elf","standalone":True,"redistribution":"https://example.org/license"}}
ELF=b"\x7fELFtest"
class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        b=io.BytesIO()
        with tarfile.open(fileobj=b,mode="w:gz") as t:
            i=tarfile.TarInfo("demo.elf");i.size=len(ELF);t.addfile(i,io.BytesIO(ELF))
        self.raw=b.getvalue();self.digest=hashlib.sha256(self.raw).hexdigest()
    def test_tar_route(self):
        p,h=prepare_zip(SOURCE,"https://example.org/demo.tar.gz",self.digest,self.root,download=lambda _:self.raw)
        self.assertEqual((self.root/p).read_bytes(),ELF)
        self.assertEqual(h,hashlib.sha256(ELF).hexdigest())
    def test_format_mismatch(self):
        with self.assertRaises(ValueError):prepare_zip(SOURCE,"https://example.org/demo.zip",self.digest,self.root,download=lambda _:self.raw)
    def test_manifest_not_standalone(self):
        b=io.BytesIO()
        with zipfile.ZipFile(b,"w") as z:
            z.writestr("demo.elf",ELF);z.writestr("payloadforge-manifest.json",b"{}")
        raw=b.getvalue()
        with self.assertRaises(ValueError):prepare_zip(SOURCE,"https://example.org/demo.zip",hashlib.sha256(raw).hexdigest(),self.root,download=lambda _:raw)
    def test_catalog_tar(self):
        releases=[{"draft":False,"prerelease":False,"tag_name":"v1","published_at":"2026-01-01","assets":[{"name":"demo.tar.gz","digest":"sha256:"+self.digest,"browser_download_url":"https://github.com/example/demo/releases/download/v1/demo.tar.gz"}]}]
        with patch.object(update,"ROOT",self.root),patch.object(update,"prepare_zip",side_effect=lambda s,u,d,r:prepare_zip(s,u,d,r,download=lambda _:self.raw)):
            item=update.select(SOURCE,releases)
        self.assertEqual(item["id"],"demo")
        self.assertEqual(item["checksum"],hashlib.sha256(ELF).hexdigest())
