"""Bounded, in-memory TAR.GZ reader for explicitly reviewed standalone releases."""
import gzip
import hashlib
import io
import re
import tarfile
from pathlib import PurePosixPath
from .archive import safe_name, MAX_ARCHIVE, MAX_MEMBER, MAX_TOTAL, MAX_FILES

MAX_TAR = MAX_TOTAL + 8 * 1024 * 1024

def extract_tar_elf(data, digest, member, *, docs_only=False):
    if not isinstance(data,bytes) or not isinstance(digest,str) or not re.fullmatch(r"[a-fA-F0-9]{64}",digest):
        raise ValueError("invalid archive or digest")
    if len(data)>MAX_ARCHIVE or hashlib.sha256(data).hexdigest()!=digest.lower():
        raise ValueError("archive size or integrity failure")
    member=safe_name(member)
    if not member.lower().endswith(".elf"):
        raise ValueError("expected ELF member")
    # Limit total inflated bytes before passing them to tarfile (including metadata).
    limit=min(MAX_TAR,max(1,len(data))*200)
    with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
        raw=stream.read(limit+1)
    if len(raw)>limit:
        raise ValueError("TAR decompression limit exceeded")
    seen=set(); files=set(); total=0; result=None
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:") as t:
        for info in t:
            path=safe_name(info.name)
            key=path.casefold()
            if len(seen)>=MAX_FILES or key in seen:
                raise ValueError("archive count or duplicate path")
            seen.add(key)
            if info.type not in (tarfile.REGTYPE,tarfile.AREGTYPE,tarfile.DIRTYPE) or info.issparse():
                raise ValueError("special TAR member")
            if info.size<0 or info.size>MAX_MEMBER:
                raise ValueError("member size limit")
            total+=info.size
            if total>MAX_TOTAL:
                raise ValueError("total size limit")
            if info.isdir():
                if info.size!=0: raise ValueError("invalid directory")
                continue
            files.add(key)
            if path!=member:
                if docs_only and not re.fullmatch(r"(?:README|LICEN[CS]E|COPYING|NOTICE|CHANGELOG|AUTHORS)(?:\.(?:txt|md|rst))?",path.rsplit("/",1)[-1],re.I):
                    raise ValueError("possible companion files")
                continue
            with t.extractfile(info) as f:
                result=f.read(MAX_MEMBER+1)
            if len(result)!=info.size or not result.startswith(b"\x7fELF"):
                raise ValueError("invalid ELF candidate")
    if any(str(p) in files for path in seen for p in PurePosixPath(path).parents):
        raise ValueError("file/directory conflict")
    if result is None:
        raise ValueError("missing ELF")
    return result,hashlib.sha256(result).hexdigest()
