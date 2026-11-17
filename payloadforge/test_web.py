import http.client,pathlib,subprocess,tempfile,threading,unittest
from html.parser import HTMLParser
from payloadforge.engine import Engine
from payloadforge.server import Server

class Ids(HTMLParser):
    def __init__(self):super().__init__();self.ids=set()
    def handle_starttag(self,tag,attrs):
        d=dict(attrs)
        if "id" in d:
            if d["id"] in self.ids:raise ValueError("duplicate control ID")
            self.ids.add(d["id"])
class WebTests(unittest.TestCase):
    def test_controls_and_script(self):
        base=pathlib.Path(__file__).resolve().parent/"web"
        parser=Ids();parser.feed((base/"index.html").read_text())
        for key in ("connect","refresh","preview","apply","versions","backup","rollback","uninstall","logs","output"):
            self.assertIn(key,parser.ids)
        subprocess.run(["node","--check",str(base/"app.js")],check=True)
    def test_static_delivery_and_policy(self):
        with tempfile.TemporaryDirectory() as d:
            s=Server(Engine(d),token="test-secret-not-in-page");t=threading.Thread(target=s.serve_forever,daemon=True);t.start()
            try:
                for path,kind in (("/","text/html"),("/app.js","application/javascript"),("/style.css","text/css")):
                    c=http.client.HTTPConnection("127.0.0.1",s.server_address[1],timeout=3)
                    try:
                        c.request("GET",path);r=c.getresponse();body=r.read()
                        self.assertEqual(r.status,200);self.assertIn(kind,r.getheader("Content-Type"))
                        self.assertIn("frame-ancestors 'none'",r.getheader("Content-Security-Policy"))
                        self.assertNotIn(b"test-secret-not-in-page",body)
                    finally:c.close()
            finally:s.shutdown();s.server_close();t.join(2)
