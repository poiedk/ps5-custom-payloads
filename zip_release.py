"""Opt-in release ZIP support. Never run an extracted executable."""
import hashlib
import io
import os
import re
import tempfile
import urllib.request
import zipfile
from urllib.parse import urlsplit
from payloadforge.archive import extract_elf, safe_name, MAX_ARCHIVE
from payloadforge.tar_archive import extract_tar_elf
from payloadforge.package_type import detect_package

def download_zip(url):
    if urlsplit(url).scheme!="https":
        raise ValueError("HTTPS required")
    request=urllib.request.Request(url,headers={"User-Agent":"payloadforge-catalog"})
    with urllib.request.urlopen(request,timeout=30) as response:
        if urlsplit(response.geturl()).scheme!="https":
            raise ValueError("HTTPS downgrade")
        data=response.read(MAX_ARCHIVE+1)
    if len(data)>MAX_ARCHIVE:
        raise ValueError("archive exceeds size limit")
    return data

def prepare_zip(source, asset_url, digest, root, download=download_zip):
    """Stage a verified standalone member using a content-addressed filename."""
    policy=source.get("archive")
    if (not isinstance(policy,dict) or set(policy)!={"member","standalone","redistribution"}
        or policy["standalone"] is not True
        or not isinstance(policy["redistribution"],str)
        or not policy["redistribution"].startswith("https://")):
        raise ValueError("ZIP requires explicit standalone review and redistribution evidence")
    member=safe_name(policy["member"])
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}",source["id"]):
        raise ValueError("invalid catalog ID")
    raw=download(asset_url)
    if not isinstance(raw,bytes) or len(raw)>MAX_ARCHIVE or hashlib.sha256(raw).hexdigest()!=digest.lower():
        raise ValueError("archive size or digest mismatch")
    fmt,kind=detect_package(raw)
    path=urlsplit(asset_url).path.lower()
    expected="tar.gz" if path.endswith((".tar.gz",".tgz")) else "zip"
    if fmt!=expected or kind!="bundle":
        raise ValueError("archive format mismatch or manifest bundle")
    if fmt=="tar.gz":
        elf,sha=extract_tar_elf(raw,digest,member,docs_only=True)
    else:
        elf,sha=extract_elf(raw,digest,member)
        # Never silently discard companion files.
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for i in z.infolist():
                if i.is_dir() or i.filename==member:
                    continue
                name=safe_name(i.filename).rsplit("/",1)[-1]
                if not re.fullmatch(r"(?:README|LICEN[CS]E|COPYING|NOTICE|CHANGELOG|AUTHORS)(?:\.(?:txt|md|rst))?",name,re.I):
                    raise ValueError("ZIP contains possible companion files; bundle review required")
    directory=root/"generated"/source["id"]
    directory.mkdir(parents=True,exist_ok=True)
    path=directory/(sha+".elf")
    if path.exists():
        if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest()!=sha:
            raise ValueError("existing generated file integrity mismatch")
    else:
        fd,tmp=tempfile.mkstemp(prefix=".stage-",dir=directory)
        try:
            with os.fdopen(fd,"wb") as f:
                f.write(elf)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
    return path.relative_to(root).as_posix(),sha
