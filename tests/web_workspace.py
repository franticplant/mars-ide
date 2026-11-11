"""Editor groups, rich Markdown and hostile document isolation (server + static)."""
import os, shutil, subprocess, threading, http.server, re
from functools import partial
from playwright.sync_api import sync_playwright, expect

WS = "/tmp/ws-workspace"
shutil.rmtree(WS, ignore_errors=True)
os.makedirs(WS + "/docs")
shutil.copy("/examples/hello.asm", WS)
DOC = """# Workspace guide

| Name | Value |
| --- | --- |
| **Rich** | ~~old~~ |

- [x] Task done
- [ ] Task pending

```javascript
const answer = 42;
```

```mermaid
flowchart LR
  A[Source] --> B[Preview]
```

```mermaid
sequenceDiagram
  participant User
  participant IDE
  User->>IDE: Preview document
```

[Next](next.md) · [External](https://example.com/)

![Local](pixel.png)
![Remote](https://example.com/tracker.png)

<script>parent.localStorage.setItem('pwned','yes')</script>
<img src=x onerror="parent.MarsIDE.S.theme='pwned'">
[Bad](javascript:alert(1))
"""
with open(WS + "/docs/guide.md", "w") as f: f.write(DOC)
with open(WS + "/docs/next.md", "w") as f: f.write("# Next page\n")
import base64
PIXEL = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aElkAAAAASUVORK5CYII="
with open(WS + "/docs/pixel.png", "wb") as f: f.write(base64.b64decode(PIXEL))
srv = subprocess.Popen(["java", "-jar", "/build/mars-engine.jar", "--token", "workspace-test", "--port", "8097", "--root", WS, "--web", "/web"], stdout=subprocess.PIPE, text=True)
srv.stdout.readline(); srv.stdout.readline()
PAGES = "/tmp/pages-workspace"
os.makedirs(PAGES, exist_ok=True)
os.symlink("/static", PAGES + "/mars-ide", target_is_directory=True)
httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 8096), partial(http.server.SimpleHTTPRequestHandler, directory=PAGES))
threading.Thread(target=httpd.serve_forever, daemon=True).start()

def setup(page, static):
    page.goto("http://127.0.0.1:8096/mars-ide/" if static else "http://127.0.0.1:8097/?token=workspace-test")
    page.wait_for_selector(".ftab")
    if static:
        page.evaluate("""async ({text, pixel}) => {
          await MarsIDE.engine.call('fs_write', {path:'docs/guide.md',text});
          await MarsIDE.engine.call('fs_write', {path:'docs/next.md',text:'# Next page\\n'});
          await MarsIDE.engine.call('fs_write', {path:'docs/pixel.png',b64:pixel});
        }""", {"text": DOC, "pixel": PIXEL})
    # Open via the file browser, exercising the normal file path rather than a test-only hook.
    page.click("#btn-side")
    page.click("#btn-refresh")
    docs = page.locator('.node[data-p="docs"]')
    if docs.get_attribute("aria-expanded") == "false":
        docs.locator(".nm").click()
    page.locator('.node[data-p="docs/guide.md"] .nm').dblclick()
    page.locator('.group-tab.selected [title="docs/guide.md"]').wait_for()
    assert page.evaluate("MarsIDE.S.current") == "docs/guide.md"

try:
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox"])
        unauth = pw.request.new_context()
        shell1 = unauth.get("http://127.0.0.1:8097/")
        shell2 = unauth.get("http://127.0.0.1:8097/")
        nonce1 = re.search(r'name="mars-script-nonce" content="([a-f0-9]+)"', shell1.text()).group(1)
        nonce2 = re.search(r'name="mars-script-nonce" content="([a-f0-9]+)"', shell2.text()).group(1)
        assert nonce1 != nonce2 and f"'nonce-{nonce1}'" in shell1.headers["content-security-policy"]
        script_policy = next(p for p in shell1.headers["content-security-policy"].split(";") if "script-src" in p)
        assert "unsafe-inline" not in script_policy and "blob:" not in script_policy
        assert unauth.get("http://127.0.0.1:8097/vendor/markdown.js").status == 200
        assert unauth.get("http://127.0.0.1:8097/js/app.js").status == 401
        assert unauth.post("http://127.0.0.1:8097/api/cmd", data='{"cmd":"hello"}').status == 401
        unauth.dispose()
        for static in [False, True]:
            page = browser.new_page(viewport={"width": 1400, "height": 860})
            errors, remote = [], []
            console = []
            page.on("console", lambda m: console.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("request", lambda r: remote.append(r.url) if r.url.startswith("https://example.com") else None)
            headers = []
            def image_response(route):
                headers.append(route.request.headers)
                route.fulfill(status=200, headers={"Access-Control-Allow-Origin": "*", "Content-Type": "image/png"}, body=base64.b64decode(PIXEL))
            page.route("https://example.com/tracker.png", image_response)
            page.context.add_cookies([{"name": "do-not-send", "value": "secret", "domain": "example.com", "path": "/", "secure": True, "sameSite": "None"}])
            setup(page, static)
            if not static:
                policy = page.request.get("http://127.0.0.1:8097/").headers["content-security-policy"]
                assert "connect-src 'self'" in policy and "https:" not in policy
            page.keyboard.press("Control+k"); page.keyboard.press("v")
            assert page.locator(".editor-group").count() == 2
            preview = page.frame_locator("iframe.markdown-preview")
            try:
                preview.locator(".mermaid svg").nth(1).wait_for(timeout=20000)
            except Exception:
                print("preview diagnostics", static, console, page.locator(".preview-host").inner_text(), flush=True)
                raise
            assert preview.locator(".mermaid svg").count() == 2
            assert preview.locator("table tbody tr").count() == 1
            assert preview.locator('input[type="checkbox"]').count() == 2
            assert preview.locator(".hljs-keyword").count() > 0
            preview.locator('img[alt="Local"][src^="data:"]').wait_for()
            assert not remote, remote
            assert page.evaluate("localStorage.getItem('pwned')") is None
            frame = page.locator("iframe.markdown-preview").element_handle().content_frame()
            assert frame.evaluate("(() => { try { parent.localStorage; return false; } catch (_) { return true; } })()")
            assert frame.evaluate("(() => { try { localStorage; return false; } catch (_) { return true; } })()")
            assert preview.locator('a[href^="javascript:"]').count() == 0
            assert preview.locator("[onerror], [onload], foreignObject").count() == 0
            # Every UI theme (including MARS Classic) and live theme changes reach the sandbox.
            for name in ["amoled", "midnight", "tokyo-night", "dracula", "nord", "gruvbox", "catppuccin", "light", "mars-classic", "amoled"]:
                page.click("#btn-settings")
                page.locator(f'.theme-card[data-t="{name}"]').click()
                page.keyboard.press("Escape")
                palette = page.evaluate("({surface:getComputedStyle(document.querySelector('.ed')).backgroundColor,text:getComputedStyle(document.body).color,dark:document.documentElement.dataset.dark})")
                expect(preview.locator("body")).to_have_css("background-color", palette["surface"])
                expect(preview.locator("body")).to_have_css("color", palette["text"])
                preview.locator(".mermaid svg").nth(1).wait_for()
                assert frame.evaluate("getComputedStyle(document.documentElement).colorScheme") == ("dark" if palette["dark"] == "1" else "light")
                if name == "amoled": assert palette["surface"] == "rgb(0, 0, 0)"
            page.click("#btn-settings"); page.locator('[data-s="fontSize"]').select_option("18"); page.keyboard.press("Escape")
            expect(preview.locator("pre code.hljs")).to_have_css("font-size", "18px")
            # Opt-in downloads use a separate opaque-origin helper, without weakening the IDE CSP.
            page.get_by_role("button", name="Load remote images for this preview (contacts external servers)", exact=True).click()
            page.get_by_role("button", name="Load images", exact=True).click()
            preview.locator('img[alt="Remote"][src^="data:"]').wait_for(timeout=20000)
            assert len(remote) == 1, remote
            assert len(headers) == 1 and "cookie" not in headers[0] and "referer" not in headers[0], headers
            # Both groups share one dirty document, preview follows unsaved source edits.
            source = page.locator(".editor-group").first.locator("textarea")
            source.fill(DOC.replace("Workspace guide", "Live preview"))
            assert source.input_value() == DOC.replace("Workspace guide", "Live preview")
            preview.locator("h1").filter(has_text="Live preview").wait_for()
            assert page.evaluate("MarsIDE.R.files.get('docs/guide.md').text.includes('Live preview')")
            assert page.locator(".group-tab").filter(has_text="•").count() == 2
            # Zen preserves splits. Maximize is independent and reversible.
            preview.locator("h1").click()
            page.keyboard.press("F10")
            page.locator("#app.zen").wait_for()
            assert page.locator(".editor-group:visible").count() == 2
            page.keyboard.press("Escape")
            page.locator("#app:not(.zen)").wait_for()
            page.keyboard.press("Alt+Shift+m")
            page.locator(".editor-groups.single-group").wait_for()
            expect(page.locator(".editor-group:visible")).to_have_count(1)
            page.keyboard.press("Escape")
            page.locator(".editor-groups:not(.single-group)").wait_for()
            assert page.locator(".editor-group:visible").count() == 2
            # Persist layout, including live draft, then restore it.
            page.wait_for_timeout(800)
            page.reload(); page.wait_for_selector("iframe.markdown-preview")
            page.frame_locator("iframe.markdown-preview").locator("h1").filter(has_text="Live preview").wait_for(timeout=20000)
            assert page.locator(".editor-group").count() == 2
            assert len(remote) == 1, "Remote-image permission must not persist through reload"
            if static:
                page.evaluate("navigator.serviceWorker.ready.then(() => true)")
                page.context.set_offline(True)
                page.reload()
                page.frame_locator("iframe.markdown-preview").locator(".mermaid svg").nth(1).wait_for(timeout=20000)
                assert len(remote) == 1
            page.screenshot(path=f"/shots/workspace-{'static' if static else 'server'}.png")
            # Local Markdown links navigate inside the IDE.
            page.frame_locator("iframe.markdown-preview").get_by_text("Next", exact=True).click()
            page.frame_locator("iframe.markdown-preview").locator("h1").filter(has_text="Next page").wait_for()
            assert page.evaluate("MarsIDE.S.current") == "docs/next.md"
            # Small screens show one group and offer next-group without changing the tree.
            page.set_viewport_size({"width": 390, "height": 844})
            expect(page.locator(".editor-group:visible")).to_have_count(1)
            page.keyboard.press("Alt+Shift+g")
            expect(page.locator(".editor-group:visible")).to_have_count(1)
            page.set_viewport_size({"width": 1400, "height": 860})
            expect(page.locator(".editor-group:visible")).to_have_count(2)
            assert not errors, errors
            page.close()
        browser.close()
finally:
    srv.terminate(); srv.wait(timeout=10)
    httpd.shutdown()
print("workspace / Markdown / isolation: ok (server + static)")
