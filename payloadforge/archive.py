"""Host-side validator for an explicitly selected ZIP member; never executes payloads."""
import hashlib
import io
import re
import stat
import zipfile
from pathlib import PurePosixPath

MAX_ARCHIVE = 128 * 1024 * 1024
MAX_MEMBER = 64 * 1024 * 1024
MAX_TOTAL = 256 * 1024 * 1024
MAX_FILES = 2048

def safe_name(name):
    if not isinstance(name,str) or not name or "\\" in name or ":" in name or any(ord(c)<32 for c in name):
        raise ValueError("invalid archive path")
    parts = name.rstrip("/").split("/")
    if any(p in ("", ".", "..") for p in parts):
        raise ValueError("unsafe archive path")
    return str(PurePosixPath(*parts))

def extract_elf(data, digest, member):
    """Return verified bytes and their SHA256, without writing or running files."""
    if not isinstance(data,bytes) or not isinstance(digest,str) or len(data)>MAX_ARCHIVE or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
        raise ValueError("invalid archive size or digest")
    if hashlib.sha256(data).hexdigest()!=digest.lower():
        raise ValueError("upstream archive digest mismatch")
    member=safe_name(member)
    if not member.lower().endswith(".elf"):
        raise ValueError("expected exact ELF member")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        items=z.infolist()
        if len(items)>MAX_FILES or sum(i.file_size for i in items)>MAX_TOTAL:
            raise ValueError("archive limits exceeded")
        seen=set()
        for info in items:
            path=safe_name(info.orig_filename).casefold()
            if path in seen:
                raise ValueError("duplicate archive path")
            seen.add(path)
            mode=stat.S_IFMT(info.external_attr>>16)
            if mode not in (0,stat.S_IFDIR if info.is_dir() else stat.S_IFREG) or info.flag_bits&1:
                raise ValueError("special or encrypted member")
            if info.file_size>MAX_MEMBER or info.file_size>max(1,info.compress_size)*200:
                raise ValueError("member limits exceeded")
        files={safe_name(i.orig_filename).casefold() for i in items if not i.is_dir()}
        if any(parent in files for path in seen for parent in (str(p) for p in PurePosixPath(path).parents)):
            raise ValueError("file/directory path conflict")
        matches=[i for i in items if i.filename==member and not i.is_dir()]
        if len(matches)!=1:
            raise ValueError("missing or ambiguous member")
        with z.open(matches[0]) as f:
            raw=f.read(MAX_MEMBER+1)
        if len(raw)!=matches[0].file_size or len(raw)>MAX_MEMBER or not raw.startswith(b"\x7fELF"):
            raise ValueError("not an ELF candidate")
        return raw,hashlib.sha256(raw).hexdigest()
