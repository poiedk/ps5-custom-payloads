"""Host CLI for the managed data-bundle engine. Explicit confirmation for writes."""
import argparse
import json
import sys
from pathlib import Path
from .archive import MAX_ARCHIVE
from .bundle import verify_bundle
from .catalog import join
from .engine import Engine,regular

def strict_json(raw):
    def pairs(values):
        result={}
        for k,v in values:
            if k in result:raise ValueError("duplicate JSON key: "+k)
            result[k]=v
        return result
    def invalid(value):raise ValueError("invalid JSON constant: "+value)
    return json.loads(raw,object_pairs_hook=pairs,parse_constant=invalid)
def parser():
    p=argparse.ArgumentParser(description="PayloadForge host preview (not PS5 native)")
    p.add_argument("--root",required=True,help="private managed test root")
    sub=p.add_subparsers(dest="command",required=True)
    for name in ("plan","install","upgrade","downgrade"):
        s=sub.add_parser(name)
        s.add_argument("--archive",required=True,type=Path);s.add_argument("--sha256",required=True)
        s.add_argument("--manifest",required=True,type=Path)
        if name!="plan":s.add_argument("--confirm",action="store_true")
    sub.add_parser("list")
    cat=sub.add_parser("catalog");cat.add_argument("--pldmgr",required=True,type=Path);cat.add_argument("--bundles",required=True,type=Path)
    for name in ("info","versions","backups","recovery","backup","rollback","uninstall"):
        s=sub.add_parser(name);s.add_argument("id")
        if name in ("backup","rollback","uninstall"):s.add_argument("--confirm",action="store_true")
        if name=="rollback":s.add_argument("snapshot")
        if name=="uninstall":s.add_argument("--drop-config",action="store_true")
    return p
def execute(args):
    c=args.command
    if c in ("install","upgrade","downgrade","backup","rollback","uninstall") and not args.confirm:
        raise ValueError("explicit --confirm required")
    if c in ("plan","install","upgrade","downgrade"):
        raw=regular(args.archive,MAX_ARCHIVE);manifest=strict_json(regular(args.manifest,2*1024*1024))
        if c=="plan":return verify_bundle(raw,args.sha256,manifest)
        return Engine(args.root).install(raw,args.sha256,manifest,action=c)
    if c=="catalog":return join(strict_json(regular(args.pldmgr,16*1024*1024)),strict_json(regular(args.bundles,16*1024*1024)))
    engine=Engine(args.root)
    if c=="list":return engine.list_installed()
    if c=="info":return engine.status(args.id)
    if c=="versions":return engine.versions(args.id)
    if c=="backups":return engine.backups(args.id)
    if c=="recovery":return engine.recovery_report(args.id)
    if c=="backup":return engine.backup(args.id)
    if c=="rollback":return engine.rollback(args.id,args.snapshot)
    if c=="uninstall":return engine.uninstall(args.id,preserve_config=not args.drop_config)
    raise ValueError("unknown command")
def main(argv=None):
    args=parser().parse_args(argv)
    try:
        print(json.dumps(execute(args),ensure_ascii=False,indent=2))
        return 0
    except (ValueError,OSError,RuntimeError) as exc:
        print("PayloadForge: "+str(exc),file=sys.stderr)
        return 1
if __name__=="__main__":raise SystemExit(main())
