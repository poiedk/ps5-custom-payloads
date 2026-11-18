import hashlib,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from payloadforge import rc_kit

class CandidateKitTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.root=Path(tmp.name);p=self.root/"native/build";p.mkdir(parents=True)
        self.elf=p/rc_kit.ELF;self.elf.write_bytes(b"\x7fELF"+b"test-only")
        self.sums=p/"MANAGED-SHA256SUMS";self.hash=hashlib.sha256(self.elf.read_bytes()).hexdigest()
        self.sums.write_text(self.hash+"  "+rc_kit.ELF+"\n")
        self.zlib=p/"zlib/zlib-1.4.tar.gz";self.zlib.parent.mkdir();self.zlib.write_bytes(b"synthetic test source")
    def test_exact_artifact_gate(self):
        with patch.object(rc_kit,"ZLIB_SHA256",rc_kit.digest(self.zlib)):
            self.assertEqual(rc_kit.validate_artifact(self.root),(self.elf,self.zlib,self.hash))
    def test_changed_binary_refused(self):
        self.elf.write_bytes(b"\x7fELFaltered")
        with self.assertRaises(ValueError):rc_kit.validate_artifact(self.root)
    def test_invalid_elf_refused(self):
        self.elf.write_bytes(b"not elf")
        self.sums.write_text(rc_kit.digest(self.elf)+"  "+rc_kit.ELF+"\n")
        with self.assertRaises(ValueError):rc_kit.validate_artifact(self.root)
    def test_wrong_filename_or_extra_checksums_refused(self):
        for suffix in ("  other.elf\n","  "+rc_kit.ELF+"\nextra\n"):
            self.sums.write_text(self.hash+suffix)
            with self.assertRaises(ValueError):rc_kit.validate_artifact(self.root)
    def test_unpinned_source_refused(self):
        with self.assertRaises(ValueError):rc_kit.validate_artifact(self.root)
    def test_bad_ci_identity_refused(self):
        with self.assertRaises(ValueError):rc_kit.assemble(self.root,self.root/"out","branch","bad")
        self.assertFalse((self.root/"out").exists())
