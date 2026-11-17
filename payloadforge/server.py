"""Loopback-only host API preview. This is not a PS5 daemon."""
import argparse
import base64
import hmac
import json
import secrets
import threading
import zipfile
from collections import deque
from datetime import datetime,timezone
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs,urlsplit
from .bundle import verify_bundle
from .cli import strict_json
from .engine import Engine

MAX_REQUEST=20*1024*1024
MAX_UPLOAD=12*1024*1024
STATIC=Path(__file__).resolve().parent/"web"

class Server(ThreadingHTTPServer):
    daemon_threads=True
    def __init__(self,engine,port=0,token=None):
        self.engine=engine
        self.token=token or secrets.token_urlsafe(32)
        self.events=deque(maxlen=200);self.event_lock=threading.Lock()
        super().__init__(("127.0.0.1",port),Handler)
    @property
    def origin(self):return "http://127.0.0.1:"+str(self.server_address[1])
    def event(self,action,ok):
        with self.event_lock:self.events.append({"time":datetime.now(timezone.utc).isoformat(),"action":action,"ok":ok})
    def logs(self):
        with self.event_lock:return list(self.events)

class Handler(BaseHTTPRequestHandler):
    protocol_version="HTTP/1.0"
    def setup(self):
        super().setup();self.connection.settimeout(15)
    def log_message(self,*args):pass
    def send_data(self,status,raw,kind="application/json; charset=utf-8"):
        self.send_response(status)
        self.send_header("Content-Type",kind)
        self.send_header("Content-Length",str(len(raw)))
        self.send_header("Cache-Control","no-store")
        self.send_header("X-Content-Type-Options","nosniff")
        self.send_header("Referrer-Policy","no-referrer")
        self.send_header("Content-Security-Policy","default-src 'none'; script-src 'self'; style-src 'self'; connect-src 'self'; form-action 'none'; frame-ancestors 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(raw)
    def reply(self,status,data):self.send_data(status,json.dumps(data,ensure_ascii=False).encode())
    def valid_host(self):
        return self.headers.get("Host")==self.server.origin.removeprefix("http://")
    def auth(self):
        value=self.headers.get("Authorization","")
        return hmac.compare_digest(value.encode(),("Bearer "+self.server.token).encode())
    def guard(self,require_auth=True):
        if not self.valid_host():self.reply(403,{"error":"invalid host"});return False
        if require_auth and not self.auth():self.reply(401,{"error":"authentication required"});return False
        origin=self.headers.get("Origin")
        if origin is not None and origin!=self.server.origin:self.reply(403,{"error":"invalid origin"});return False
        return True
    def do_GET(self):
        p=urlsplit(self.path)
        if p.path in ("/","/app.js","/style.css"):
            if not self.guard(False):return
            name={"/":"index.html","/app.js":"app.js","/style.css":"style.css"}[p.path]
            kind={"/":"text/html; charset=utf-8","/app.js":"application/javascript; charset=utf-8","/style.css":"text/css; charset=utf-8"}[p.path]
            try:raw=(STATIC/name).read_bytes()
            except FileNotFoundError:self.reply(404,{"error":"host UI not installed"});return
            self.send_data(200,raw,kind);return
        if not self.guard():return
        try:
            e=self.server.engine
            if p.path=="/api/health":result={"mode":"host-preview","native":False}
            elif p.path=="/api/packages":result=e.list_installed()
            elif p.path=="/api/logs":result=self.server.logs()
            elif p.path in ("/api/versions","/api/recovery","/api/backups"):
                q=parse_qs(p.query,strict_parsing=True)
                if set(q)!={"id"} or len(q["id"])!=1:raise ValueError("single id required")
                result={"/api/versions":e.versions,"/api/recovery":e.recovery_report,"/api/backups":e.backups}[p.path](q["id"][0])
            else:self.reply(404,{"error":"not found"});return
            self.reply(200,result)
        except (ValueError,OSError,RuntimeError) as exc:self.reply(400,{"error":str(exc)[:300]})
    def do_POST(self):
        if not self.guard():return
        if self.path!="/api/action":self.reply(404,{"error":"not found"});return
        action="invalid"
        try:
            if self.headers.get("Transfer-Encoding") or self.headers.get_content_type()!="application/json":raise ValueError("JSON content length required")
            length=int(self.headers.get("Content-Length","0"))
            if not 0<length<=MAX_REQUEST:raise ValueError("request size limit")
            raw=self.rfile.read(length)
            if len(raw)!=length:raise ValueError("incomplete request")
            item=strict_json(raw)
            if not isinstance(item,dict):raise ValueError("object required")
            action=item.get("action")
            if action not in ("plan","install","upgrade","downgrade","backup","rollback","uninstall"):raise ValueError("unsupported action")
            if action!="plan" and item.get("confirm") is not True:raise ValueError("explicit confirmation required")
            e=self.server.engine
            if action in ("plan","install","upgrade","downgrade"):
                fields={"action","archive","sha256","manifest"}|({"confirm"} if action!="plan" else set())
                if set(item)!=fields:raise ValueError("invalid bundle request")
                if not isinstance(item["archive"],str):raise ValueError("base64 archive required")
                archive=base64.b64decode(item["archive"],validate=True)
                if len(archive)>MAX_UPLOAD:raise ValueError("host upload limit")
                result=verify_bundle(archive,item["sha256"],item["manifest"]) if action=="plan" else e.install(archive,item["sha256"],item["manifest"],action=action)
            else:
                fields={"action","id","confirm"}
                if action=="rollback":fields.add("snapshot")
                if action=="uninstall":fields.add("preserve_config")
                if set(item)!=fields:raise ValueError("invalid action request")
                if action=="backup":result=e.backup(item["id"])
                elif action=="rollback":result=e.rollback(item["id"],item["snapshot"])
                else:result=e.uninstall(item["id"],preserve_config=item["preserve_config"])
            self.server.event(action,True);self.reply(200,result)
        except (ValueError,OSError,RuntimeError,TypeError,zipfile.BadZipFile) as exc:
            self.server.event(action if isinstance(action,str) and len(action)<32 else "invalid",False)
            self.reply(400,{"error":str(exc)[:300]})

def main():
    p=argparse.ArgumentParser(description="PayloadForge host-only loopback API")
    p.add_argument("--root",required=True);p.add_argument("--port",type=int,default=8765)
    args=p.parse_args();server=Server(Engine(args.root),args.port)
    print("Host preview: "+server.origin,flush=True)
    print("Session token: "+server.token,flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:server.server_close()
if __name__=="__main__":main()
