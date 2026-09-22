# -*- coding: utf-8 -*-
"""Real-browser probe of the served (chunked) package — the client-side half
of the served-package gate (review P0.7, G09/G10): loads a school's entry
page through an HTTP origin, changes views, and proves the loader is
fail-closed under a failed request, a truncated chunk and a chunk with the
wrong identity.

    python -m tests.browser.chunked_probe <site_dir> <entry path e.g. /2026/<token>/> [--json out.json] [--shots dir]

Requires Playwright's Chromium. Starts prod.serve_local on a free port.
"""
from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from pathlib import Path


def _free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def run(site: Path, entry: str, shots: Path | None) -> dict:
    from playwright.sync_api import sync_playwright
    from prod.serve_local import Handler
    from functools import partial
    from http.server import ThreadingHTTPServer
    port = _free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, root=site))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{port}"
    out = {"entry": entry, "checks": [], "requests": []}
    errors = []

    def check(name, ok, detail=""):
        out["checks"].append({"name": name, "ok": bool(ok), "detail": detail})

    with sync_playwright() as pw:
        b = pw.chromium.launch()
        # 0. CSP smoke test WITHOUT bypass: the page's own scripts must run under the
        #    production Content-Security-Policy (no inline script, no eval); the
        #    functional checks below run with bypass_csp because Playwright's own
        #    evaluate() uses eval, which the policy forbids.
        strict = b.new_context(viewport={"width": 1280, "height": 900})
        sp = strict.new_page()
        csp_errors = []
        sp.on("console", lambda m: csp_errors.append(m.text) if m.type == "error" else None)
        sp.goto(base + entry + "#scope=whole&gender=all&cohort=none&lang=en", wait_until="load")
        sp.wait_for_selector("#load-mask[hidden]", state="attached", timeout=20000)
        strict_banner = sp.locator("#view-banner").inner_text()
        check("page runs under the production CSP (no inline script, no eval)",
              "Whole school" in strict_banner and not any("Content Security Policy" in e for e in csp_errors),
              "; ".join(csp_errors)[:300])
        strict.close()
        ctx = b.new_context(viewport={"width": 1280, "height": 900}, bypass_csp=True)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("request", lambda r: out["requests"].append(r.url.replace(base, "")))

        # 1. cold load: whole school renders from the inline state, no chunk fetched
        page.goto(base + entry + "#scope=whole&gender=all&cohort=none&lang=en", wait_until="load")
        page.wait_for_function("document.getElementById('load-mask').hidden === true", timeout=20000)
        banner = page.inner_text("#view-banner")
        chunk_reqs = [r for r in out["requests"] if "/s-" in r]
        check("cold load renders whole school without a chunk fetch", "Whole school" in banner and len(chunk_reqs) == 0,
              f"banner={banner[:60]!r} chunkRequests={len(chunk_reqs)}")
        check("no console/page errors on load", not errors, "; ".join(errors)[:300])
        t0 = time.time()
        if shots: page.screenshot(path=str(shots / "01-whole.png"), full_page=False)

        # 2. scope change: three chunk fetches (all/boy/girl), mask shown then hidden, banner updated
        n0 = len(out["requests"])
        page.evaluate("location.hash = '#scope=y5&gender=all&cohort=none&lang=en'")
        page.wait_for_function("document.getElementById('load-mask').hidden === true && document.querySelector('#view-banner').innerText.indexOf('Year 5') > -1", timeout=30000)
        new_reqs = [r for r in out["requests"][n0:] if "/s-" in r]
        banner = page.inner_text("#view-banner")
        check("scope change fetches the scope's chunks and renders", "Year 5" in banner and len(new_reqs) >= 3,
              f"banner={banner[:60]!r} fetched={len(new_reqs)} in {time.time()-t0:.1f}s")
        # a second change inside the same scope needs no fetch
        n1 = len(out["requests"])
        page.evaluate("location.hash = '#scope=y5&gender=girl&cohort=none&lang=en'")
        page.wait_for_function("document.querySelector('#view-banner').innerText.indexOf('Girls') > -1 || document.querySelector('#view-banner').innerText.indexOf('girl') > -1", timeout=15000)
        check("gender change within a loaded scope needs no fetch", len([r for r in out["requests"][n1:] if "/s-" in r]) == 0)
        if shots: page.screenshot(path=str(shots / "02-y5-girls.png"))

        # 3. failed request: 500 on every chunk of scope y7 -> error mask, no stale content committed
        page.route("**/s-*.json", lambda route: route.fulfill(status=500, body="boom"))
        page.evaluate("location.hash = '#scope=y6&gender=all&cohort=none&lang=en'")
        page.wait_for_function("document.getElementById('load-mask').classList.contains('load-error')", timeout=20000)
        banner = page.inner_text("#view-banner") if page.is_visible("#view-banner") else "(hidden)"
        masked = page.evaluate("document.body.classList.contains('is-loading')")
        hidden_banner = page.evaluate("getComputedStyle(document.getElementById('view-banner')).visibility")
        print_disabled = page.evaluate("document.getElementById('btn-print').disabled")
        check("failed chunk request shows the error mask and hides the old view", masked and hidden_banner == "hidden" and print_disabled,
              f"masked={masked} bannerVisibility={hidden_banner} printDisabled={print_disabled}")
        if shots: page.screenshot(path=str(shots / "03-error.png"))
        # retry after the fault clears
        page.unroute("**/s-*.json")
        page.click("#load-retry")
        page.wait_for_function("document.getElementById('load-mask').hidden === true && document.querySelector('#view-banner').innerText.indexOf('Year 6') > -1", timeout=30000)
        check("retry after the fault clears renders the requested view", True)

        # 4. wrong identity: serve a chunk whose envelope names another recipient
        def tamper(route):
            resp = route.fetch()
            body = resp.body()
            try:
                j = json.loads(body); j["env"]["recipient"] = "0000000"
                route.fulfill(status=200, body=json.dumps(j, ensure_ascii=False), headers={"Content-Type": "application/json"})
            except Exception:
                route.fulfill(response=resp)
        page.route("**/s-*.json", tamper)
        page.evaluate("location.hash = '#scope=y4&gender=all&cohort=none&lang=en'")
        page.wait_for_function("document.getElementById('load-mask').classList.contains('load-error')", timeout=20000)
        check("chunk with another recipient's identity is refused", True)
        page.unroute("**/s-*.json")

        # 5. truncated chunk
        def truncate(route):
            resp = route.fetch(); body = resp.body()
            route.fulfill(status=200, body=body[: len(body) // 2], headers={"Content-Type": "application/json"})
        page.route("**/s-*.json", truncate)
        page.evaluate("location.hash = '#scope=y3&gender=all&cohort=none&lang=en'")
        page.wait_for_function("document.getElementById('load-mask').classList.contains('load-error')", timeout=20000)
        check("truncated chunk is refused", True)
        page.unroute("**/s-*.json")
        page.click("#load-retry")
        page.wait_for_function("document.getElementById('load-mask').hidden === true && document.querySelector('#view-banner').innerText.indexOf('Year 3') > -1", timeout=30000)

        # 6. Welsh mode with a cohort at the whole school (chunk whole|all)
        page.evaluate("location.hash = '#scope=whole&gender=all&cohort=sp_football&lang=cy'")
        page.wait_for_function("document.getElementById('load-mask').hidden === true && document.documentElement.lang === 'cy'", timeout=30000)
        check("Welsh view with a selected group renders after its chunk loads", True)
        if shots: page.screenshot(path=str(shots / "04-cy-football.png"))
        check("no console/page errors during the probe (other than the injected faults)",
              all(("500" in e) or ("chunk load failed" in e) or ("Failed to load resource" in e) for e in errors), "; ".join(errors)[:400])
        b.close()
    httpd.shutdown()
    out["ok"] = all(c["ok"] for c in out["checks"])
    out["chunkRequests"] = len([r for r in out["requests"] if "/s-" in r])
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site_dir"); ap.add_argument("entry"); ap.add_argument("--json"); ap.add_argument("--shots")
    a = ap.parse_args(argv)
    shots = Path(a.shots) if a.shots else None
    if shots: shots.mkdir(parents=True, exist_ok=True)
    res = run(Path(a.site_dir), a.entry, shots)
    if a.json:
        Path(a.json).write_text(json.dumps(res, indent=1), encoding="utf-8")
    for c in res["checks"]:
        print(("PASS " if c["ok"] else "FAIL ") + c["name"] + (("  — " + c["detail"]) if c["detail"] else ""))
    print("chunked probe:", "PASS" if res["ok"] else "FAIL", f"({res['chunkRequests']} chunk requests)")
    sys.exit(0 if res["ok"] else 1)


if __name__ == "__main__":
    main()
