import copy,unittest
from payloadforge.catalog import join
BASE={"name":"Demo","id":"demo","url":"https://github.com/owner/demo/releases/download/v1/demo.elf","source":"https://github.com/owner/demo"}
ITEM={"id":"demo","name":"Demo","version":"1","pldmgr_id":"demo","source":BASE["source"],"archive_url":"https://github.com/owner/demo/releases/download/v1/data.zip","archive_sha256":"a"*64,"manifest_url":"https://example.org/manifest.json","manifest_sha256":"b"*64,"firmwares":["13.60"]}
def side(items):return {"schema_version":1,"name":"test","packages":items}
class IntegrationTests(unittest.TestCase):
    def test_empty_sidecar(self):self.assertEqual(join({"payloads":[BASE]},side([]))["companion_count"],0)
    def test_link(self):
        rows=[copy.deepcopy(BASE)];original=copy.deepcopy(rows)
        out=join(rows,side([ITEM]))
        self.assertEqual(out["packages"][0]["pldmgr"]["id"],"demo")
        self.assertTrue(out["packages"][0]["supports_13_60"]);self.assertEqual(rows,original)
    def test_mismatch(self):
        with self.assertRaises(ValueError):join([BASE],side([{**ITEM,"id":"changed"}]))
    def test_duplicate(self):
        with self.assertRaises(ValueError):join([BASE],side([ITEM,ITEM]))
    def test_bundle_collision(self):
        with self.assertRaises(ValueError):join([BASE],side([{**ITEM,"pldmgr_id":None}]))
    def test_missing_hash(self):
        with self.assertRaises(ValueError):join([BASE],side([{**ITEM,"archive_sha256":""}]))
    def test_wrong_source(self):
        with self.assertRaises(ValueError):join([BASE],side([{**ITEM,"source":"https://github.com/copy/demo"}]))
    def test_bundles_only(self):
        x={**ITEM,"id":"other","name":"Other","pldmgr_id":None,"source":"https://github.com/owner/other","archive_url":"https://github.com/owner/other/releases/download/v1/a.zip"}
        self.assertIsNone(join([BASE],side([x]))["packages"][0]["pldmgr"])
    def test_missing_firmware(self):
        with self.assertRaises(ValueError):join([BASE],side([{**ITEM,"firmwares":[]}]))
