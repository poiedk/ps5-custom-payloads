import hashlib,io,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from payloadforge.engine import Engine

def package(version, files):
    b=io.BytesIO();items=[]
    with zipfile.ZipFile(b,"w") as z:
        for path,data,policy in files:
            z.writestr(path,data)
            items.append({"path":path,"sha256":hashlib.sha256(data).hexdigest(),"size":len(data),"policy":policy})
    raw=b.getvalue()
    return raw,hashlib.sha256(raw).hexdigest(),{"schema_version":1,"id":"demo","version":version,"files":items}

class EngineTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);self.e=Engine(self.root)
        self.p1=package("v1",[("settings.json",b"{}", "preserve"),("assets/a.txt",b"old","replace-with-backup")])
        self.p2=package("v2",[("settings.json",b'{"default":true}',"preserve"),("assets/a.txt",b"new","replace-with-backup")])
    def data(self,record):return self.root/"apps"/"demo"/"generations"/record["generation"]/"data"
    def test_install(self):
        s=self.e.install(*self.p1)
        self.assertEqual(self.e.status("demo"),s)
        self.assertEqual((self.data(s)/"assets/a.txt").read_bytes(),b"old")
    def test_update_preserves_settings(self):
        old=self.e.install(*self.p1)
        (self.data(old)/"settings.json").write_bytes(b'{"user":true}')
        s=self.e.install(*self.p2)
        self.assertEqual(s["version"],"v2")
        self.assertEqual((self.data(s)/"settings.json").read_bytes(),b'{"user":true}')
        self.assertEqual((self.data(s)/"assets/a.txt").read_bytes(),b"new")
        self.assertEqual((self.data(old)/"assets/a.txt").read_bytes(),b"old")
    def test_omitted_config_preserved(self):
        self.e.install(*self.p1)
        s=self.e.install(*package("v2",[("assets/a.txt",b"new","replace-with-backup")]))
        self.assertTrue((self.data(s)/"settings.json").is_file())
    def test_bad_update_no_change(self):
        old=self.e.install(*self.p1)
        with self.assertRaises(ValueError):self.e.install(self.p2[0],"0"*64,self.p2[2])
        self.assertEqual(self.e.status("demo"),old)
    def test_interrupted_before_pointer(self):
        old=self.e.install(*self.p1)
        with patch.object(self.e,"_before_activate",side_effect=OSError("simulated interruption")):
            with self.assertRaises(OSError):self.e.install(*self.p2)
        self.assertEqual(self.e.status("demo"),old)
        self.assertEqual(len(list((self.root/"apps/demo/generations").iterdir())),1)
    def test_symlink_config_rejected(self):
        old=self.e.install(*self.p1)
        outside=self.root/"outside";outside.write_text("private")
        p=self.data(old)/"settings.json";p.unlink();p.symlink_to(outside)
        with self.assertRaises(OSError):self.e.install(*self.p2)
        self.assertEqual(outside.read_text(),"private")
    def test_modified_immutable_file_blocked(self):
        old=self.e.install(*self.p1)
        (self.data(old)/"assets/a.txt").write_bytes(b"tampered")
        with self.assertRaises(ValueError):self.e.install(*self.p2)
        self.assertEqual(self.e.status("demo"),old)
    def test_new_manifest_conflict_with_preserved(self):
        old=self.e.install(*self.p1)
        p=package("v2",[("settings.json/file.txt",b"x","replace-with-backup")])
        with self.assertRaises(ValueError):self.e.install(*p)
        self.assertEqual(self.e.status("demo"),old)
    def test_reopen(self):
        s=self.e.install(*self.p1)
        self.assertEqual(Engine(self.root).status("demo"),s)
    def test_manifest_exec_rejected(self):
        with self.assertRaises(ValueError):self.e.install(*package("v1",[("tool.elf",b"\x7fELF","replace-with-backup")]))
