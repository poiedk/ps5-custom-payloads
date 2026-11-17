"""Read-only join of explicit PLDMGR IDs with a separate companion catalogue."""
import re
from urllib.parse import urlsplit
from .catalog_guard import origin,duplicates,normalize

ID=re.compile(r"[a-z0-9][a-z0-9._-]{0,79}")
SHA=re.compile(r"[a-f0-9]{64}")
def https(value):
    if not isinstance(value,str) or len(value)>2048:return False
    try:p=urlsplit(value)
    except ValueError:return False
    return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password and not p.fragment
def join(pldmgr,sidecar):
    rows=pldmgr.get("payloads") if isinstance(pldmgr,dict) else pldmgr
    if not isinstance(rows,list) or len(rows)>4096:raise ValueError("invalid PLDMGR catalog")
    known={}
    for row in rows:
        if not isinstance(row,dict):raise ValueError("invalid PLDMGR item")
        key=row.get("id")
        if not isinstance(key,str) or not ID.fullmatch(key) or key in known:raise ValueError("stable unique explicit PLDMGR IDs required")
        if not isinstance(row.get("name"),str) or not https(row.get("url")):raise ValueError("invalid PLDMGR item")
        known[key]=row
    if not isinstance(sidecar,dict) or set(sidecar)!={"schema_version","name","packages"} or sidecar["schema_version"]!=1 or not isinstance(sidecar["name"],str) or not isinstance(sidecar["packages"],list) or len(sidecar["packages"])>4096:
        raise ValueError("invalid sidecar catalog")
    seen=set();result=[]
    fields={"id","name","version","pldmgr_id","source","archive_url","archive_sha256","manifest_url","manifest_sha256","firmwares"}
    for item in sidecar["packages"]:
        if not isinstance(item,dict) or set(item)!=fields:raise ValueError("invalid companion package")
        key=item["id"]
        if not isinstance(key,str) or not ID.fullmatch(key) or key in seen:raise ValueError("invalid or duplicate companion ID")
        seen.add(key)
        if not isinstance(item["name"],str) or not item["name"] or not isinstance(item["version"],str) or not item["version"]:raise ValueError("invalid companion metadata")
        if not all(https(item[k]) for k in ("source","archive_url","manifest_url")):raise ValueError("HTTPS metadata required")
        upstream=origin(item["source"]);asset=origin(item["archive_url"])
        if not upstream or upstream!=asset or "/releases/download/" not in item["archive_url"]:raise ValueError("archive must be official release")
        if not all(isinstance(item[k],str) and SHA.fullmatch(item[k]) for k in ("archive_sha256","manifest_sha256")):raise ValueError("invalid checksum")
        firmwares=item["firmwares"]
        if not isinstance(firmwares,list) or not firmwares or len(firmwares)>64 or len(set(firmwares))!=len(firmwares) or not all(isinstance(x,str) and re.fullmatch(r"\d{1,2}\.\d{2}",x) for x in firmwares):
            raise ValueError("explicit firmware list required")
        link=item["pldmgr_id"]
        if link is not None:
            if link!=key or link not in known:raise ValueError("companion must link to its unchanged PLDMGR ID")
            if origin(known[link].get("source"))!=upstream:raise ValueError("linked source mismatch")
        elif key in known or duplicates(item,list(known.values())):
            raise ValueError("bundle-only package collides with PLDMGR")
        result.append({"package":dict(item),"pldmgr":dict(known[link]) if link is not None else None,"supports_13_60":"13.60" in firmwares})
    return {"pldmgr_count":len(known),"companion_count":len(result),"packages":result}
