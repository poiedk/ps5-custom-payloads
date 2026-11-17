"""Strict manifest and dry-run plan for data-only homebrew companion files.

No filesystem writes, downloads, executable launch or boot modifications.
This host-side prototype is not a native PS5 installer.
"""
import re
from pathlib import PurePosixPath
from archive import safe_name

ID = re.compile(r"[a-z0-9][a-z0-9-]{0,47}")
SHA = re.compile(r"[a-f0-9]{64}")
MAX_FILES = 2048
MAX_TOTAL = 256 * 1024 * 1024
ALLOWED_SUFFIXES = {".json", ".ini", ".cfg", ".conf", ".txt", ".png", ".jpg", ".jpeg", ".webp", ".md", ".dat"}

def validate(manifest):
    if not isinstance(manifest, dict) or set(manifest) != {"schema_version","id","version","files"}:
        raise ValueError("invalid manifest structure")
    if manifest["schema_version"] != 1:
        raise ValueError("unsupported schema")
    app = manifest["id"]
    if not isinstance(app,str) or not ID.fullmatch(app):
        raise ValueError("invalid id")
    version = manifest["version"]
    if not isinstance(version,str) or not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._+-]{0,63}",version):
        raise ValueError("invalid version")
    files=manifest["files"]
    if not isinstance(files,list) or not 1<=len(files)<=MAX_FILES:
        raise ValueError("invalid file count")
    seen=set()
    total=0
    plan=[]
    for item in files:
        if not isinstance(item,dict) or set(item)!={"path","sha256","size","policy"}:
            raise ValueError("invalid file metadata")
        path=safe_name(item["path"])
        p=PurePosixPath(path)
        if p.suffix.lower() not in ALLOWED_SUFFIXES:
            raise ValueError("unsupported companion file type")
        if any(part.startswith(".") for part in p.parts):
            raise ValueError("hidden paths not allowed")
        # Case-insensitive uniqueness and prefix conflicts.
        key=path.casefold()
        if key in seen or any(key.startswith(x+"/") or x.startswith(key+"/") for x in seen):
            raise ValueError("path conflict")
        seen.add(key)
        digest=item["sha256"]
        if not isinstance(digest,str) or not SHA.fullmatch(digest):
            raise ValueError("invalid sha256")
        n=item["size"]
        if type(n) is not int or not 0<=n<=64*1024*1024:
            raise ValueError("invalid file size")
        total+=n
        if total>MAX_TOTAL:
            raise ValueError("bundle size limit")
        policy=item["policy"]
        if policy not in ("preserve","replace-with-backup"):
            raise ValueError("invalid overwrite policy")
        if p.suffix.lower() in {".json",".ini",".cfg",".conf"} and policy!="preserve":
            raise ValueError("configuration must be preserved")
        plan.append({"relative_path":path,"target":"/data/payloadforge/apps/"+app+"/"+path,
                     "sha256":digest,"size":n,"policy":policy})
    return {"id":app,"version":version,"total_bytes":total,"files":plan,"dry_run":True}
