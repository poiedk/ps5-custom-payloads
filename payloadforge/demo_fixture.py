"""Create harmless synthetic host-testing packages, not executable payloads."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path
def generate(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    hashes=[]
    for version,default,message in (("1.0.0",b'{"theme":"default"}\n',b"demo v1\n"),("2.0.0",b'{"theme":"new-default"}\n',b"demo v2\n")):
        prefix="demo-v"+version
        files=[("settings.json",default,"preserve"),("assets/message.txt",message,"replace-with-backup")]
        manifest={"schema_version":3,"id":"payloadforge-demo","version":version,"dependencies":[],"resources":[],"conflicts":[],"files":[]}
        path=out/(prefix+".zip")
        with zipfile.ZipFile(path,"x",compression=zipfile.ZIP_STORED) as z:
            for name,raw,policy in files:
                info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));z.writestr(info,raw)
                manifest["files"].append({"path":name,"sha256":hashlib.sha256(raw).hexdigest(),"size":len(raw),"policy":policy})
        mp=out/(prefix+".json")
        mp.write_text(json.dumps(manifest,indent=2)+"\n")
        for p in (path,mp):hashes.append(hashlib.sha256(p.read_bytes()).hexdigest()+"  "+p.name)
    # Both H10 manifests describe the same harmless files as the v1 archive.
    base = json.loads((out / "demo-v1.0.0.json").read_text())
    for field, peer in (("dependencies", "absent-demo-peer"), ("conflicts", "payloadforge-demo")):
        manifest = {**base, "id": "demo-negative", field: [{"id": peer, "constraint": "*"}]}
        path = out / ("negative-" + field + ".json")
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="ascii")
        hashes.append(hashlib.sha256(path.read_bytes()).hexdigest() + "  " + path.name)
    (out/"SHA256SUMS").write_text("\n".join(hashes)+"\n")
def main():
    p=argparse.ArgumentParser();p.add_argument("--out",required=True,type=Path)
    generate(p.parse_args().out)
if __name__=="__main__":main()
