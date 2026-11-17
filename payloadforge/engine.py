"""Host reference transaction engine. No payload execution or console system writes.

The managed root must be private to the installer; this is not a sandbox for
concurrent malicious local processes. Active versions are selected by one atomic
CURRENT pointer; only app-owned data files are supported in schema v1.
"""
import contextlib
import fcntl
import hashlib
import io
import json
import os
import re
import shutil
import stat
import uuid
import zipfile
from pathlib import Path
from .archive import MAX_MEMBER, MAX_TOTAL, safe_name
from .manifest import ID, validate
from .bundle import verify_bundle

GEN = re.compile(r"[a-f0-9]{32}")
def digest(raw): return hashlib.sha256(raw).hexdigest()
def directory(path, create=False):
    if create:
        path.mkdir(mode=0o700,exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise ValueError("unsafe or missing directory: "+str(path))
    return path
def regular(path, limit):
    with os.fdopen(os.open(path,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK),"rb") as f:
        info=os.fstat(f.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size>limit:
            raise ValueError("not a bounded regular file")
        data=f.read(limit+1)
    if len(data)>limit: raise ValueError("file size limit")
    return data
def within(base, name, create=False):
    directory(base)
    parts=safe_name(name).split("/")
    for part in parts[:-1]:
        base=directory(base/part,create)
    return base/parts[-1]
def sync_dir(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try: os.fsync(fd)
    finally: os.close(fd)
def write_new(path, raw):
    with path.open("xb") as f:
        f.write(raw);f.flush();os.fsync(f.fileno())
def encode(data):
    return (json.dumps(data,sort_keys=True,indent=2)+"\n").encode()

class Engine:
    def __init__(self,root):
        self.root=Path(root).absolute()
        if self.root.resolve()!=self.root:
            raise ValueError("managed root must not traverse symlinks")
        directory(self.root,True)
    @contextlib.contextmanager
    def locked(self):
        fd=os.open(self.root/".lock",os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):raise ValueError("invalid lock")
            fcntl.flock(fd,fcntl.LOCK_EX)
            yield
        finally: os.close(fd)
    def _app(self,app,create=False):
        if not isinstance(app,str) or not ID.fullmatch(app):
            raise ValueError("invalid package id")
        return directory(directory(self.root/"apps",create)/app,create)
    def _pointer(self,app):
        try: name=regular(app/"CURRENT",64).decode("ascii").strip()
        except FileNotFoundError:return None
        if not GEN.fullmatch(name):raise ValueError("invalid generation pointer")
        return name
    def _generation(self,app,name):
        if not isinstance(name,str) or not GEN.fullmatch(name):
            raise ValueError("invalid generation")
        return directory(directory(app/"generations")/name)
    def _state(self,app,name):
        folder=self._generation(app,name)
        record=json.loads(regular(folder/"registry.json",2*1024*1024))
        if set(record)!={"id","version","generation","archive_sha256","files"} or record["id"]!=app.name or record["generation"]!=name:
            raise ValueError("invalid registry")
        if not re.fullmatch(r"[a-f0-9]{64}",record["archive_sha256"]):
            raise ValueError("invalid archive digest in registry")
        validate({"schema_version":1,"id":record["id"],"version":record["version"],"files":record["files"]})
        return record,directory(folder/"data")
    def _read_state_files(self,record,base):
        result={};total=0
        for f in record["files"]:
            path=f["path"];raw=regular(within(base,path),MAX_MEMBER)
            if f["policy"]!="preserve" and (len(raw)!=f["size"] or digest(raw)!=f["sha256"]):
                raise ValueError("installed file changed: "+path)
            total+=len(raw)
            if total>MAX_TOTAL:raise ValueError("installed data too large")
            result[path]=(raw,f["policy"])
        return result
    def _activate(self,app,generation):
        tmp=app/(".pointer-"+uuid.uuid4().hex)
        try:
            write_new(tmp,(generation+"\n").encode("ascii"))
            os.replace(tmp,app/"CURRENT")
            sync_dir(app)
        finally:
            tmp.unlink(missing_ok=True)
    def _before_activate(self,app,generation):
        """Test hook; production implementation performs no action."""
    def _publish(self,app,version,archive_sha256,files):
        items=[{"path":path,"sha256":digest(raw),"size":len(raw),"policy":policy}
               for path,(raw,policy) in sorted(files.items())]
        validate({"schema_version":1,"id":app.name,"version":version,"files":items})
        gens=directory(app/"generations",True)
        name=uuid.uuid4().hex;stage=gens/(".stage-"+name);final=gens/name
        stage.mkdir(mode=0o700)
        record={"id":app.name,"version":version,"generation":name,"archive_sha256":archive_sha256,"files":items}
        try:
            base=directory(stage/"data",True)
            for path,(raw,_) in files.items():write_new(within(base,path,True),raw)
            write_new(stage/"registry.json",encode(record))
            for parent,_,_ in os.walk(stage,topdown=False):sync_dir(Path(parent))
            os.replace(stage,final);sync_dir(gens)
            self._before_activate(app,name)
            self._activate(app,name)
        except Exception:
            # Never remove an active generation; failed pointer durability is ambiguous.
            if stage.exists():shutil.rmtree(stage)
            if final.exists() and self._pointer(app)!=name:shutil.rmtree(final)
            raise
        return record
    def install(self,raw,archive_sha256,manifest):
        plan=verify_bundle(raw,archive_sha256,manifest)
        files={}
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            for f in plan["files"]:
                with z.open(f["relative_path"]) as stream:data=stream.read(MAX_MEMBER+1)
                if len(data)!=f["size"] or digest(data)!=f["sha256"]:raise ValueError("bundle changed")
                files[f["relative_path"]]=(data,f["policy"])
        with self.locked():
            app=self._app(plan["id"],True)
            current=self._pointer(app)
            if current:
                previous,base=self._state(app,current)
                for path,(data,policy) in self._read_state_files(previous,base).items():
                    if policy=="preserve":
                        if path in files and files[path][1]!="preserve":raise ValueError("cannot demote preserved configuration")
                        files[path]=(data,policy)
            return self._publish(app,plan["version"],archive_sha256.lower(),files)
    def status(self,app_id):
        with self.locked():
            app=self._app(app_id)
            current=self._pointer(app)
            if current is None:return None
            record,_=self._state(app,current)
            return record
