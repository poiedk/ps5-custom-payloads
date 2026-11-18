"""Real Chromium E2E; synthetic data-only fixtures and temporary Linux store."""
import hashlib
import json
import pathlib
import subprocess
import tempfile
from playwright.sync_api import sync_playwright, expect
from .demo_fixture import generate

def run():
    native=pathlib.Path(__file__).resolve().parent/"native"
    subprocess.run(["make","-C",str(native),"host-managed"],check=True)
    with tempfile.TemporaryDirectory(prefix="pf-browser-") as tmp:
        root=pathlib.Path(tmp)/"store";root.mkdir(mode=0o700)
        fixtures=pathlib.Path(tmp)/"fixtures";generate(fixtures)
        runtime=subprocess.Popen([str(native/"build/payloadforge-runtime-managed-host"),
            "--serve-managed","--root",str(root),"--port","0","--seconds","180"],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        try:
            assert runtime.stdout.readline().strip()=="PayloadForge managed development runtime"
            url=runtime.stdout.readline().strip()
            token=runtime.stdout.readline().strip().removeprefix("Session token: ")
            assert url.startswith("http://127.0.0.1:") and len(token)==64
            app=root/"apps/payloadforge-demo"
            def active():
                return app/"generations"/(app/"CURRENT").read_text()
            with sync_playwright() as p:
                browser=p.chromium.launch(headless=True)
                context=browser.new_context(viewport={"width":1280,"height":900})
                external=[]
                def route(request):
                    if request.request.url.startswith(url+"/"):request.continue_()
                    else:external.append(request.request.url);request.abort()
                context.route("**/*",route)
                page=context.new_page()
                errors=[];page.on("pageerror",lambda exc:errors.append(str(exc)))
                page.goto(url,wait_until="load")
                expect(page.locator("#verify")).to_be_disabled()
                expect(page.locator("#install")).to_be_disabled()
                page.locator("#token").fill("0"*64);page.locator("#connect").click()
                expect(page.locator("#result")).to_contain_text("token rejected")
                expect(page.locator("#verify")).to_be_disabled()
                page.locator("#token").fill(token);page.locator("#connect").click()
                expect(page.locator("#session")).to_contain_text("Connected")
                assert page.locator("#token").input_value()==""
                assert list(root.iterdir())==[]
                page.locator("#catalog").click()
                expect(page.locator("#catalog-rows tr")).to_have_count(9)
                expect(page.locator("#catalog-meta")).to_contain_text("0 companion bundles")
                assert "omnipad" not in [x.inner_text() for x in page.locator("#catalog-rows td:nth-child(2)").all()]
                assert list(root.iterdir())==[]
                def select(version):
                    for name,ext in (("manifest","json"),("archive","zip")):
                        path=fixtures/("demo-v"+version+"."+ext)
                        page.locator("#"+name).set_input_files(path)
                        page.locator("#"+name+"-hash").fill(hashlib.sha256(path.read_bytes()).hexdigest())
                def verify(version):
                    page.locator("#verify").click()
                    expect(page.locator("#verified")).to_contain_text(version,timeout=15000)
                    expect(page.locator("#verify")).to_be_enabled(timeout=15000)
                    expect(page.locator("#install")).to_be_disabled()
                def apply(action):
                    page.locator("#package-confirm").check()
                    page.locator("#"+action).click()
                    expect(page.locator("#verify")).to_be_enabled(timeout=15000)
                    data=json.loads(page.locator("#result").inner_text())
                    assert data["ok"],data
                    expect(page.locator("#install")).to_be_disabled()
                def control(action):
                    page.locator("#control-confirm").check()
                    page.locator("#"+action).click()
                    expect(page.locator("#verify")).to_be_enabled(timeout=15000)
                    data=json.loads(page.locator("#result").inner_text())
                    assert data["ok"],data
                    return data
                select("1.0.0");verify("1.0.0")
                # Editing input invalidates the previous verification.
                real=page.locator("#archive-hash").input_value()
                page.locator("#archive-hash").fill("0"*64)
                expect(page.locator("#install")).to_be_disabled()
                page.locator("#verify").click()
                expect(page.locator("#result")).to_contain_text("bundle verification failed")
                assert list(root.iterdir())==[]
                page.locator("#archive-hash").fill(real);verify("1.0.0")
                apply("install")
                assert (active()/"data/assets/message.txt").read_bytes()==b"demo v1\n"
                (active()/"data/settings.json").write_bytes(b'{"theme":"user"}')
                snap=control("backup")["snapshot"]
                assert page.locator("#snapshot").input_value()==snap
                select("2.0.0");verify("2.0.0");apply("upgrade")
                assert (active()/"data/assets/message.txt").read_bytes()==b"demo v2\n"
                assert (active()/"data/settings.json").read_bytes()==b'{"theme":"user"}'
                control("rollback")
                assert (active()/"data/assets/message.txt").read_bytes()==b"demo v1\n"
                assert (active()/"data/settings.json").read_bytes()==b'{"theme":"user"}'
                page.locator("#recovery").click()
                expect(page.locator("#result")).to_contain_text('"integrity": 1')
                expect(page.locator("#quarantine")).to_be_disabled()
                control("uninstall")
                assert (app/"CURRENT").read_bytes().endswith(b":keep")
                page.reload(wait_until="load")
                expect(page.locator("#verify")).to_be_disabled()
                assert page.locator("#token").input_value()==""
                assert page.evaluate("localStorage.length===0 && sessionStorage.length===0 && document.cookie===''" )
                assert not external,external
                assert not errors,errors
                browser.close()
            print("Chromium browser E2E PASS: auth, verify, tamper, install, backup, update, rollback, recovery, uninstall, session reset")
        finally:
            runtime.terminate()
            try:runtime.communicate(timeout=15)
            except subprocess.TimeoutExpired:runtime.kill();runtime.communicate(timeout=3)

if __name__=="__main__":run()
