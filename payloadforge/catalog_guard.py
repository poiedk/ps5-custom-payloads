"""Offline catalogue eligibility gate. Metadata is evidence, not malware analysis."""
import hashlib
import re
from datetime import date
from urllib.parse import urlsplit

ID=re.compile(r"[a-z0-9][a-z0-9._-]{0,79}")
HEX=re.compile(r"[0-9a-fA-F]{64}")
def normalize(text):
    return re.sub(r"[^a-z0-9]","",str(text).casefold())
def origin(url):
    if not isinstance(url,str):return None
    try:p=urlsplit(url)
    except ValueError:return None
    if p.scheme!="https" or p.username or p.password or p.netloc.lower() not in ("github.com","codeberg.org","raw.githubusercontent.com"):
        return None
    parts=p.path.strip("/").split("/")
    if len(parts)<2 or any(not re.fullmatch(r"[a-zA-Z0-9_.-]+",x) or x in (".","..") for x in parts[:2]):
        return None
    host="github.com" if p.netloc.lower()=="raw.githubusercontent.com" else p.netloc.lower()
    return host+"/"+parts[0].casefold()+"/"+parts[1].removesuffix(".git").casefold()
def source_origin(entry):
    if entry.get("repo"):
        host="codeberg.org" if entry.get("provider")=="codeberg" else "github.com"
        return origin("https://"+host+"/"+entry["repo"])
    return origin(entry.get("source")) or origin(entry.get("source_direct")) or origin(entry.get("url"))
def duplicates(candidate, entries):
    ident={normalize(candidate.get(k,"")) for k in ("id","name")}-{""}
    repo=source_origin(candidate)
    result=[]
    for row in entries:
        names={normalize(row.get(k,"")) for k in ("id","name")}-{""}
        if ident&names or (repo and repo==source_origin(row)):
            result.append(row.get("id") or row.get("name"))
    return result
def evaluate(candidate, official, custom, artifact, today):
    """Return all blocking reasons; no network and no mutation of a catalog."""
    reasons=[]
    key=candidate.get("id")
    if not isinstance(key,str) or not ID.fullmatch(key):reasons.append("invalid id")
    repo=source_origin(candidate)
    if not repo or origin(candidate.get("official_url"))!=repo:reasons.append("canonical source not established")
    owner=repo.split("/")[1] if repo else None
    if not owner or str(candidate.get("publisher","")).casefold()!=owner:reasons.append("publisher mismatch")
    try:
        age=(today-date.fromisoformat(candidate["repo_created_at"])).days
        if age<14:reasons.append("new or future-dated repository; manual review")
    except (KeyError,ValueError,TypeError):reasons.append("repository age missing")
    commit=candidate.get("source_revision")
    if not isinstance(commit,str) or not re.fullmatch(r"[a-fA-F0-9]{40}",commit) or origin(candidate.get("public_code_url"))!=repo or commit.lower() not in str(candidate.get("public_code_url","")).lower().split("/"):
        reasons.append("public source revision not evidenced")
    asset=candidate.get("asset_url","")
    if origin(asset)!=repo or "/releases/download/" not in str(asset):reasons.append("release origin mismatch")
    checksum=candidate.get("expected_sha256")
    if not isinstance(checksum,str) or not HEX.fullmatch(checksum) or origin(candidate.get("checksum_url"))!=repo:
        reasons.append("upstream checksum not evidenced")
    elif not isinstance(artifact,bytes) or len(artifact)>128*1024*1024 or hashlib.sha256(artifact).hexdigest()!=checksum.lower():
        reasons.append("artifact digest not independently matched")
    if candidate.get("reviewed") is not True or not candidate.get("review_evidence"):
        reasons.append("manual provenance review missing")
    if candidate.get("compatibility_13_60") is not True or not candidate.get("compatibility_evidence"):
        reasons.append("13.60 support not evidenced")
    matches=duplicates(candidate,official+custom)
    if matches:reasons.append("duplicate: "+", ".join(str(m) for m in matches))
    return {"eligible":not reasons,"reasons":reasons}
