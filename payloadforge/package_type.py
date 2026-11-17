"""Content-based package classification. Classification is NOT integrity verification."""
import gzip
import io
import tarfile
import zipfile
from .archive import MAX_ARCHIVE, MAX_FILES, safe_name
from .tar_archive import MAX_TAR

MANIFEST = "payloadforge-manifest.json"

def detect_package(raw):
    if not isinstance(raw,bytes) or not raw or len(raw)>MAX_ARCHIVE:
        raise ValueError("invalid package size")
    if raw.startswith(b"\x7fELF"):
        return ("elf","standalone")
    names=[]
    if raw.startswith((b"PK\x03\x04",b"PK\x05\x06")):
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            entries=z.infolist()
            if len(entries)>MAX_FILES:
                raise ValueError("too many ZIP members")
            for i in entries:
                name=safe_name(i.orig_filename)
                if not i.is_dir():
                    names.append(name)
        fmt="zip"
    elif raw.startswith(b"\x1f\x8b"):
        limit=min(MAX_TAR,max(1,len(raw))*200)
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as stream:
            expanded=stream.read(limit+1)
        if len(expanded)>limit:
            raise ValueError("gzip expansion limit")
        with tarfile.open(fileobj=io.BytesIO(expanded),mode="r:") as t:
            for n,i in enumerate(t,1):
                if n>MAX_FILES:
                    raise ValueError("too many TAR members")
                name=safe_name(i.name)
                if not i.isdir():
                    names.append(name)
        fmt="tar.gz"
    else:
        raise ValueError("unsupported package format")
    folded=[n.casefold() for n in names]
    if len(folded)!=len(set(folded)):
        raise ValueError("duplicate member")
    return (fmt,"manifest-bundle" if MANIFEST in names else "bundle")
