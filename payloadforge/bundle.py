"""Offline companion-bundle verification; no install, download or execution."""
import hashlib
import io
import stat
import zipfile
from archive import safe_name, MAX_ARCHIVE, MAX_MEMBER, MAX_TOTAL, MAX_FILES
from manifest import validate

def verify_bundle(raw, archive_sha256, manifest):
    plan=validate(manifest)
    if not isinstance(raw,bytes) or len(raw)>MAX_ARCHIVE:
        raise ValueError("invalid archive size")
    if not isinstance(archive_sha256,str) or hashlib.sha256(raw).hexdigest()!=archive_sha256.lower():
        raise ValueError("archive digest mismatch")
    expected={f["relative_path"]:f for f in plan["files"]}
    seen=set()
    actual=set()
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        items=z.infolist()
        if len(items)>MAX_FILES or sum(i.file_size for i in items)>MAX_TOTAL:
            raise ValueError("archive limits exceeded")
        for i in items:
            path=safe_name(i.filename)
            k=path.casefold()
            if k in seen:
                raise ValueError("duplicate archive path")
            seen.add(k)
            mode=stat.S_IFMT(i.external_attr>>16)
            if i.flag_bits&1 or mode not in (0,stat.S_IFREG,stat.S_IFDIR):
                raise ValueError("encrypted or special archive member")
            if i.is_dir():
                if mode not in (0,stat.S_IFDIR) or not any(x.startswith(path+"/") for x in expected):
                    raise ValueError("unexpected directory")
                continue
            if mode==stat.S_IFDIR or path not in expected:
                raise ValueError("unexpected archive member")
            f=expected[path]
            if i.file_size!=f["size"] or i.file_size>MAX_MEMBER or i.file_size>max(1,i.compress_size)*200:
                raise ValueError("invalid member size")
            digest=hashlib.sha256()
            count=0
            with z.open(i) as stream:
                while True:
                    chunk=stream.read(65536)
                    if not chunk: break
                    count+=len(chunk)
                    if count>f["size"]: raise ValueError("member exceeds declared size")
                    digest.update(chunk)
            if count!=f["size"] or digest.hexdigest()!=f["sha256"]:
                raise ValueError("member integrity mismatch")
            actual.add(path)
    if actual!=set(expected):
        raise ValueError("missing manifest files")
    return {**plan,"archive_sha256":archive_sha256.lower(),"verified":True}
