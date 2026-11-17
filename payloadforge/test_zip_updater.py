import hashlib,io,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import update
from zip_release import prepare_zip

ELF=b"\x7fELFsynthetic-test-data"
BASE={"id":"demo","repo":"example/demo","name":"Demo","pattern":r"demo\.zip","archive":{"member":"demo.elf","standalone":True,"redistribution":"https://example.org/license"}}
def fixture(entries):
    f=io.BytesIO()
    with zipfile.ZipFile(f,"w") as z:
        for p,b in entries:z.writestr(p,b)
    data=f.getvalue()
    return data,hashlib.sha256(data).hexdigest()
def release(name,digest):
    return [{"draft":False,"prerelease":False,"tag_name":"v2","published_at":"2026-01-01","assets":[{"name":name,"digest":"sha256:"+digest,"browser_download_url":"https://github.com/example/demo/releases/download/v2/"+name}]}]
class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.raw,self.digest=fixture([("demo.elf",ELF),("README.md",b"test")])
    def stage(self,source=BASE,raw=None,digest=None):
        return prepare_zip(source,"https://example.org/demo.zip",digest or self.digest,self.root,download=lambda _:self.raw if raw is None else raw)
    def test_stage_and_idempotency(self):
        p,h=self.stage()
        self.assertEqual(h,hashlib.sha256(ELF).hexdigest())
        self.assertEqual((self.root/p).read_bytes(),ELF)
        self.assertEqual(self.stage(),(p,h))
    def test_wrong_hash(self):
        with self.assertRaises(ValueError):self.stage(digest="0"*64)
        self.assertFalse((self.root/"generated").exists())
    def test_companion_rejected(self):
        raw,d=fixture([("demo.elf",ELF),("config.json",b"{}")])
        with self.assertRaises(ValueError):self.stage(raw=raw,digest=d)
    def test_policy_required(self):
        with self.assertRaises(ValueError):self.stage(source={"id":"demo"})
    def test_wrong_member(self):
        s={**BASE,"archive":{**BASE["archive"],"member":"missing.elf"}}
        with self.assertRaises(ValueError):self.stage(source=s)
    def test_existing_corrupt(self):
        p,h=self.stage()
        (self.root/p).write_bytes(b"bad")
        with self.assertRaises(ValueError):self.stage()
    def test_unsafe_id(self):
        with self.assertRaises(ValueError):self.stage(source={**BASE,"id":"../bad"})
    def test_zip_catalog_metadata(self):
        with patch.object(update,"ROOT",self.root),patch.object(update,"prepare_zip",side_effect=lambda s,u,d,r:self.stage()):
            item=update.select(BASE,release("demo.zip",self.digest))
        self.assertEqual(item["id"],"demo")
        self.assertEqual(item["filename"],"demo.elf")
        self.assertEqual(item["checksum"],hashlib.sha256(ELF).hexdigest())
        self.assertIn("/main/generated/demo/",item["url"])
    def test_legacy_elf(self):
        source={**BASE,"pattern":r"demo\.elf"}
        item=update.select(source,release("demo.elf","a"*64))
        self.assertEqual(item["checksum"],"a"*64)
        self.assertTrue(item["url"].endswith("/demo.elf"))
    def test_fallback_on_bad_zip(self):
        previous={"id":"demo","name":"Demo","version":"v1","url":"https://example.org/old.elf","checksum":"b"*64}
        out=self.root/"payloads_v2.json"
        out.write_text(json.dumps({"payloads":[previous]}))
        (self.root/"sources.json").write_text(json.dumps([BASE]))
        with patch.object(update,"ROOT",self.root),patch.object(update,"OUT",out),patch.object(update,"get",return_value=release("demo.zip",self.digest)),patch.object(update,"prepare_zip",side_effect=ValueError("invalid archive")),patch.object(update,"build_icons",return_value=({},{})):
            update.main()
        self.assertEqual(json.loads(out.read_text())["payloads"],[previous])
        self.assertIn("invalid archive",json.loads((self.root/"status.json").read_text())["warnings"][0])
