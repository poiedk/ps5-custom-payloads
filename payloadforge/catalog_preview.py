"""Read-only, pinned production PLDMGR reference. No network, no executable downloads."""
import hashlib
import json
from pathlib import Path
from .catalog import join

SOURCE_URL="https://raw.githubusercontent.com/poiedk/ps5-custom-payloads/main/payloads_v2.json"
SOURCE_BLOB="a548325f19acf5ff226157f6bd4c477cbb86d509"
COMPANION_BLOB="b9fb9f777d2823802e9b883c5d5c800b33e9db34"
SNAPSHOT_DATE="2026-11-18"
IDS=("kraken-mount","shadowkraken","alembic","prosperomgr","hearbridge","omnipad-ce","glm","ghosttoothapi","anypad")
ROOT=Path(__file__).resolve().parent/"catalog_inputs"

def read_pinned(path,expected):
    raw=Path(path).read_bytes()
    if len(raw)>1024*1024:
        raise ValueError("catalog input exceeds limit")
    blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
    if blob!=expected:
        raise ValueError("pinned catalog blob mismatch: "+str(path))
    return json.loads(raw)

def project(source,sidecar):
    joined=join(source,sidecar)
    if joined["companion_count"]!=0:
        raise ValueError("no companion bundles have been approved for this development snapshot")
    rows=source["payloads"]
    if tuple(r["id"] for r in rows)!=IDS:
        raise ValueError("production ID set/order changed; require explicit review")
    items=[]
    for row in rows:
        name=row["name"];version=row.get("version")
        if not all(isinstance(s,str) and 0<len(s)<=128 and all(32<=ord(c)<127 for c in s) for s in (name,version)):
            raise ValueError("invalid display metadata")
        items.append({"id":row["id"],"name":name,"version":version,"availability":"pldmgr-reference-only"})
    return {"schema_version":1,"snapshot_date":SNAPSHOT_DATE,"source_url":SOURCE_URL,
        "source_git_blob":SOURCE_BLOB,"pldmgr_count":joined["pldmgr_count"],"companion_count":0,
        "live":False,"provenance_verified":False,"installable":False,"items":items}

def reference():
    return project(read_pinned(ROOT/"pldmgr_snapshot.json",SOURCE_BLOB),
                   read_pinned(ROOT/"companion_snapshot.json",COMPANION_BLOB))
def encoded():
    return (json.dumps(reference(),ensure_ascii=True,separators=(",",":"))+"\n").encode("ascii")
