import hashlib,unittest
from datetime import date
from payloadforge.catalog_guard import evaluate,duplicates,origin

RAW=b"test release";SHA=hashlib.sha256(RAW).hexdigest();REV="a"*40
C={"id":"demo","name":"Demo","repo":"owner/project","publisher":"owner","official_url":"https://github.com/owner/project","repo_created_at":"2026-01-01","public_code_url":"https://github.com/owner/project/tree/"+REV,"source_revision":REV,"asset_url":"https://github.com/owner/project/releases/download/v1/demo.elf","expected_sha256":SHA,"checksum_url":"https://github.com/owner/project/releases/tag/v1","reviewed":True,"review_evidence":["review"],"compatibility_13_60":True,"compatibility_evidence":["test"]}
class CatalogTests(unittest.TestCase):
    def gate(self,c=C,artifact=RAW,official=(),custom=()):
        return evaluate(c,list(official),list(custom),artifact,date(2026,11,17))
    def test_candidate(self):self.assertTrue(self.gate()["eligible"])
    def test_mirror_duplicate(self):
        self.assertFalse(self.gate(official=[{"name":"Alias","source":"https://github.com/OWNER/PROJECT/releases","url":"https://github.com/mirror/mirror/releases/download/x/y"}])["eligible"])
    def test_name_duplicate(self):self.assertEqual(duplicates({"name":"Demo CE"},[{"id":"demo-ce"}]),["demo-ce"])
    def test_publisher_mismatch(self):self.assertFalse(self.gate({**C,"publisher":"copycat"})["eligible"])
    def test_hash_wrong(self):self.assertFalse(self.gate(artifact=b"modified")["eligible"])
    def test_missing_bytes(self):self.assertFalse(self.gate(artifact=None)["eligible"])
    def test_no_code(self):self.assertFalse(self.gate({**C,"public_code_url":None})["eligible"])
    def test_new_repo(self):self.assertFalse(self.gate({**C,"repo_created_at":"2026-11-16"})["eligible"])
    def test_wrong_host(self):self.assertIsNone(origin("https://github.com.evil.example/owner/project"))
    def test_source_mismatch(self):self.assertFalse(self.gate({**C,"asset_url":"https://github.com/copy/project/releases/download/v1/demo.elf"})["eligible"])
    def test_unreviewed(self):self.assertFalse(self.gate({**C,"reviewed":False})["eligible"])
    def test_firmware_missing(self):self.assertFalse(self.gate({**C,"compatibility_13_60":False})["eligible"])
