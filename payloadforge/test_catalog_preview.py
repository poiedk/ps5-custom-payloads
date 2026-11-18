import copy,json,tempfile,unittest
from pathlib import Path
from payloadforge.catalog_preview import ROOT,SOURCE_BLOB,COMPANION_BLOB,IDS,read_pinned,reference,project,encoded
class CatalogReferenceTests(unittest.TestCase):
    def setUp(self):
        self.source=read_pinned(ROOT/"pldmgr_snapshot.json",SOURCE_BLOB)
        self.sidecar=read_pinned(ROOT/"companion_snapshot.json",COMPANION_BLOB)
    def test_pinned_exact_reference(self):
        x=reference();self.assertEqual(tuple(r["id"] for r in x["items"]),IDS)
        self.assertEqual((x["pldmgr_count"],x["companion_count"]),(9,0))
        self.assertFalse(x["live"]);self.assertFalse(x["installable"]);self.assertFalse(x["provenance_verified"])
        self.assertEqual(json.loads(encoded()),x)
        for row in x["items"]:self.assertEqual(set(row),{"id","name","version","availability"})
    def test_extra_or_renamed_id_rejected(self):
        for action in ("extra","renamed","removed"):
            m=copy.deepcopy(self.source)
            if action=="extra":m["payloads"].append(dict(m["payloads"][0],id="omnipad"))
            elif action=="renamed":m["payloads"][0]["id"]="changed"
            else:m["payloads"].pop()
            with self.assertRaises(ValueError):project(m,self.sidecar)
    def test_unpinned_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"tampered.json";p.write_bytes((ROOT/"pldmgr_snapshot.json").read_bytes()+b"\n")
            with self.assertRaises(ValueError):read_pinned(p,SOURCE_BLOB)
    def test_companion_not_silently_approved(self):
        bad=dict(self.sidecar,packages=[{"id":"unreviewed"}])
        with self.assertRaises(ValueError):project(self.source,bad)
    def test_unsafe_display_metadata_rejected(self):
        m=copy.deepcopy(self.source);m["payloads"][0]["name"]="test\ncontrol"
        with self.assertRaises(ValueError):project(m,self.sidecar)
