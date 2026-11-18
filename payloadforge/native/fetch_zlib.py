"""Fetch a pinned upstream zlib source archive for the read-only native build."""
import argparse
import hashlib
import io
from pathlib import Path
import tarfile
import urllib.request

URL="https://zlib.net/fossils/zlib-1.4.tar.gz"
SHA256="02dd159783677a749c04adbdd02b55b8a2bcc7e054f51b76b549199a916ad584"
LIMIT=4*1024*1024
FILES={"adler32.c","crc32.c","crc32.h","inflate.c","inflate.h","inffast.c","inffast.h",
       "inftrees.c","inftrees.h","inffixed.h","zlib.h","zconf.h","zutil.c","zutil.h","LICENSE"}

def fetch(destination):
    dest=Path(destination)
    dest.mkdir(parents=True,exist_ok=False)
    # Only the identical pinned archive is acceptable; do not learn a new hash on retry.
    raw=None
    import time
    for attempt in range(3):
        try:
            req=urllib.request.Request(URL,headers={"User-Agent":"PayloadForge-build","Accept-Encoding":"identity","Cache-Control":"no-cache"})
            with urllib.request.urlopen(req,timeout=60) as response:
                if not response.geturl().startswith("https://"):
                    raise ValueError("HTTPS required")
                candidate=response.read(LIMIT+1)
            actual=hashlib.sha256(candidate).hexdigest()
            if len(candidate)>LIMIT or actual!=SHA256:
                raise ValueError("zlib source checksum or size mismatch: received "+str(len(candidate))+" bytes, sha256 "+actual)
            raw=candidate
            break
        except (OSError,ValueError) as exc:
            print("Pinned zlib fetch attempt "+str(attempt+1)+": "+str(exc),flush=True)
            if attempt<2:
                time.sleep(2**attempt)
    if raw is None:
        raise ValueError("Pinned zlib source unavailable; refusing native build")
    found=set()
    with tarfile.open(fileobj=io.BytesIO(raw),mode="r:gz") as archive:
        for m in archive:
            if m.name not in {"zlib-1.4/"+p for p in FILES}:
                continue
            name=m.name.split("/")[1]
            if name in found or not m.isfile() or not 0<m.size<=2*1024*1024:
                raise ValueError("invalid zlib source member")
            with archive.extractfile(m) as f:
                data=f.read(2*1024*1024+1)
            if len(data)!=m.size:
                raise ValueError("truncated source member")
            (dest/name).write_bytes(data)
            found.add(name)
    if found!=FILES:
        raise ValueError("missing zlib sources: "+", ".join(sorted(FILES-found)))
    (dest/"zlib-1.4.tar.gz").write_bytes(raw)
    print("Verified zlib 1.4 source SHA-256: "+SHA256)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("destination",type=Path)
    fetch(p.parse_args().destination)
