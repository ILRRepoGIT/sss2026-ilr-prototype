# -*- coding: utf-8 -*-
"""Chromium render probe (V4.13): screenshots and a print PDF of the mini page.

    python -m tests.browser.render_probe <wd> <out_dir> [--a11y]

<wd> is a tests.jsdom.make_mini working directory (mini_data.json +
template_stamped.html). Writes, for English and Welsh: a full-page PNG at
1280 px, and a print-to-PDF (A4) with its page count in probe.json. Used to
prove that the default rendering of V4.13 is pixel-identical to V4.12 and
that the accessibility switch changes only what it should. Read-only: no
gate, no build step depends on it.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]


def page_html(wd: Path) -> str:
    tpl = (wd / "template_stamped.html").read_text(encoding="utf-8")
    app = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
    data = (wd / "mini_data.json").read_text(encoding="utf-8")
    html = tpl
    html = html.replace("__REPORT_JSON__", data.replace("</", "<\\/"))
    html = html.replace("/*__APP_JS__*/", app.replace("</", "<\\/"))
    html = html.replace("__SCHOOL_NAME__", "Ysgol Penrhyn Dewi")
    return html


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    a11y = "--a11y" in sys.argv
    wd, out = Path(args[0]), Path(args[1])
    out.mkdir(parents=True, exist_ok=True)
    html_path = out / "page.html"
    html_path.write_text(page_html(wd), encoding="utf-8")
    res = {}
    with sync_playwright() as p:
        b = p.chromium.launch()
        for lang in ("en", "cy"):
            ctx = b.new_context(viewport={"width": 1280, "height": 900}, device_scale_factor=1)
            pg = ctx.new_page()
            frag = f"#scope=whole&gender=all&cohort=none&lang={lang}" + ("&a11y=1" if a11y else "")
            pg.goto(html_path.resolve().as_uri() + frag, wait_until="load")
            pg.wait_for_timeout(600)
            # settle: open nothing, scroll to top
            pg.evaluate("window.scrollTo(0,0)")
            pg.wait_for_timeout(200)
            png = out / f"{lang}.png"
            pg.screenshot(path=str(png), full_page=True, animations="disabled")
            meta = pg.evaluate("""() => { const r = document.getElementById('meta-table');
              const b = r ? r.getBoundingClientRect() : null;
              return { h: document.documentElement.scrollHeight, cls: document.documentElement.className,
                       bodyFont: getComputedStyle(document.body).fontFamily,
                       bodySize: getComputedStyle(document.body).fontSize,
                       meta: b ? [b.left + scrollX, b.top + scrollY, b.right + scrollX, b.bottom + scrollY] : null } }""")
            pdf = out / f"{lang}.pdf"
            pg.emulate_media(media="print")
            pg.pdf(path=str(pdf), format="A4", print_background=True, prefer_css_page_size=True)
            pdf_bytes = pdf.read_bytes()
            pages = len(re.findall(rb"/Type\s*/Page[^s]", pdf_bytes))
            res[lang] = dict(meta, pdfPages=pages, pdfBytes=len(pdf_bytes))
            ctx.close()
        b.close()
    (out / "probe.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
