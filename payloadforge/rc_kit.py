"""Assemble a CI-gated DEMO hardware test kit, never a production release."""
import argparse,hashlib,json,os,re,shutil,subprocess
from pathlib import Path
from .demo_fixture import generate
from .catalog_preview import reference,encoded

SDK="v0.42"
SDK_SHA256="8cfbc7cd5811e719eb4f0c47eea668d3dc7b40bc8ab11c4a5031d40c23ec02da"
ZLIB_SHA256="02dd159783677a749c04adbdd02b55b8a2bcc7e054f51b76b549199a916ad584"
ELF="payloadforge-runtime-managed-development.elf"
def digest(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate_artifact(source):
    p=Path(source)/"native/build"
    elf=p/ELF; sums=p/"MANAGED-SHA256SUMS"; zlib=p/"zlib/zlib-1.4.tar.gz"
    if not elf.is_file() or elf.is_symlink() or not 0<elf.stat().st_size<=16*1024*1024:
        raise ValueError("missing/oversized managed ELF")
    with elf.open("rb") as f:
        if f.read(4)!=b"\x7fELF":raise ValueError("not ELF")
    line=sums.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[a-f0-9]{64}  "+re.escape(ELF),line) or digest(elf)!=line[:64]:
        raise ValueError("managed ELF checksum mismatch")
    if not zlib.is_file() or zlib.is_symlink() or zlib.stat().st_size>4*1024*1024 or digest(zlib)!=ZLIB_SHA256:
        raise ValueError("invalid corresponding zlib source archive")
    return elf,zlib,line[:64]
def assemble(source,out,commit,run):
    if not re.fullmatch(r"[a-f0-9]{40}",commit) or not re.fullmatch(r"[0-9]+",run):
        raise ValueError("invalid CI commit or run ID")
    actual=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if actual!=commit:raise ValueError("source checkout does not match candidate commit")
    elf,zlib,sha=validate_artifact(source)
    ref=reference()
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(elf,out/ELF)
    shutil.copyfile(zlib,out/"zlib-1.4.tar.gz")
    package=Path(__file__).resolve().parent
    for file in ("HUMAN_TODO.md","HARDWARE_TEST_MATRIX.md","HARDWARE_RESULT_TEMPLATE.json","COPYING","RC_SCOPE.md"):
        shutil.copyfile(package/file,out/file)
    with (out/"payloadforge-corresponding-source.tar.gz").open("wb") as f:
        subprocess.run(["git","archive","--format=tar.gz","--prefix=payloadforge-source/",commit,
            "payloadforge",".github/workflows/payloadforge-tests.yml","payloadforge_catalog.json"],stdout=f,check=True)
    generate(out/"fixtures")
    (out/"catalog-reference.json").write_bytes(encoded())
    meta={"version":"0.2.0-rc0-demo","commit":commit,"ci_run":run,"elf":ELF,"elf_sha256":sha,
        "sdk":SDK,"sdk_sha256":SDK_SHA256,"zlib_sha256":ZLIB_SHA256,"catalog_git_blob":ref["source_git_blob"],
        "approved_companion_packages":0,"hardware_verified":False,"production_ready":False,"scope":"synthetic data-only demo"}
    (out/"CANDIDATE.json").write_text(json.dumps(meta,indent=2)+"\n",encoding="utf8")
    hashes=[]
    for p in sorted(out.rglob("*")):
        if p.is_file():hashes.append(digest(p)+"  "+p.relative_to(out).as_posix())
    (out/"SHA256SUMS").write_text("\n".join(hashes)+"\n",encoding="ascii")
    print("DEMO hardware candidate assembled: "+sha+" (hardware not verified)")
def main():
    p=argparse.ArgumentParser();p.add_argument("--artifact",required=True);p.add_argument("--out",required=True)
    p.add_argument("--commit",required=True);p.add_argument("--run",required=True)
    a=p.parse_args();assemble(a.artifact,a.out,a.commit,a.run)
if __name__=="__main__":main()
