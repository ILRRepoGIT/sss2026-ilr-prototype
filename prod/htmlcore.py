# -*- coding: utf-8 -*-
"""The served entry page and the shared release assets (deployment plan §2:
"a small core page … and beside it a set of state chunk files"; the client
script, fonts and artwork shared per release tag, content-hashed).

    python -m prod.htmlcore assets <release_out_dir> --release <tag> [--yac <dir>] [--fonts <dir>] [--cover <dir>]
    (the entry page is written by prod.runner through build_entry())

Release assets, written once per release under <release_out_dir>/r/<tag>/assets/:
    app-<sha256[:16]>.js               web/app.js (the same bytes the monolith embeds)
    fonts/montserrat-latin-{400,600,800}-normal.woff2
    img/yac-<key>-<sha256[:12]>.webp   the fourteen Young Artists Competition entries,
                                       prepared exactly as pipeline.yac_assets prepares them
    img/sw-logo-white-<h>.webp, img/lockup-2026-<h>.webp   the cover assets
    assets.json                        the manifest: token → path, sha256, bytes

The entry page is web/template.html assembled the way pipeline.build_html
assembles the monolith — the D79 static-lane stamping and verification, the
D80 attribute check and the 2022-claim gate are the same calls — with three
differences: the payload is the CORE payload (no states except the first,
plus the chunk map and the envelope), the client script is an external
content-hashed file, and fonts, artwork and cover images are URLs to the
shared release assets instead of data URIs.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
from pathlib import Path

from PIL import Image

from pipeline import static_lane as _SL
from pipeline.build_html import COVER_IMAGES, FONT_FACES
from pipeline.common import ROOT
from pipeline.yac_assets import YAC, prepared as _yac_prepared

SEP = (",", ":")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _webp(im: Image.Image) -> bytes:
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    return buf.getvalue()


def build_assets(release_out: Path, release: str, yac_dir: Path, fonts_dir: Path,
                 cover_dir: Path, app_js: Path | None = None, template: Path | None = None) -> dict:
    """Write the shared assets for one release; return the asset manifest."""
    app_js = app_js or ROOT / "web" / "app.js"
    adir = release_out / "r" / release / "assets"
    (adir / "fonts").mkdir(parents=True, exist_ok=True)
    (adir / "img").mkdir(parents=True, exist_ok=True)
    man = {"release": release, "files": {}, "tokens": {}}

    js = app_js.read_bytes()
    h = _sha(js)
    p = f"app-{h[:16]}.js"
    (adir / p).write_bytes(js)
    man["files"]["app"] = {"path": f"assets/{p}", "sha256": h, "bytes": len(js)}

    for weight, fname in FONT_FACES:
        b = (fonts_dir / fname).read_bytes()
        (adir / "fonts" / fname).write_bytes(b)
        man["files"][f"font{weight}"] = {"path": f"assets/fonts/{fname}", "sha256": _sha(b), "bytes": len(b)}

    for key, fname, token, w, crop, clear_bg, _src in YAC:
        src = yac_dir / fname
        if not src.exists():
            raise SystemExit(f"Young Artists Competition file missing: {src}")
        b = _webp(_yac_prepared(src, w, crop, clear_bg))
        h = _sha(b)
        short = key.replace("ui.alt_yac_", "").replace("_", "-")
        p = f"img/yac-{short}-{h[:12]}.webp"
        (adir / p).write_bytes(b)
        man["files"][key] = {"path": f"assets/{p}", "sha256": h, "bytes": len(b)}
        man["tokens"][token] = f"assets/{p}"

    for token, (fname, w) in COVER_IMAGES.items():
        im = Image.open(cover_dir / fname)
        if im.width > w:
            im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
        b = _webp(im)
        h = _sha(b)
        p = f"img/{token.strip('_').lower().replace('_', '-')}-{h[:12]}.webp"
        (adir / p).write_bytes(b)
        man["files"][token] = {"path": f"assets/{p}", "sha256": h, "bytes": len(b)}
        man["tokens"][token] = f"assets/{p}"

    (adir / "assets.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    return man


def fonts_css_urls(base: str) -> str:
    css = []
    for weight, fname in FONT_FACES:
        css.append("@font-face{font-family:'Montserrat';font-style:normal;"
                   f"font-weight:{weight};font-display:swap;"
                   f"src:url({base}assets/fonts/{fname}) format('woff2');}}")
    return "\n".join(css)


_APP_TAG = re.compile(r"<script>\s*/\*__APP_JS__\*/\s*</script>")
_BANNED_2022 = [r"matches the measure used in", r"same measure as the 2022",
                r"can be set alongside", r"so this figure can be compared with 2022"]


def build_entry(core: dict, assets: dict, release: str, site_prefix: str = "/",
                template: Path | None = None) -> str:
    """Assemble the served entry page for one school from its core payload."""
    template = template or ROOT / "web" / "template.html"
    html = template.read_text(encoding="utf-8")
    base = f"{site_prefix.rstrip('/')}/r/{release}/"
    school_name = core["school"]["name"]

    # D79 / D80 — identical to pipeline.build_html
    _static = (core.get("welsh") or {}).get("static") or {}
    if not _static:
        raise SystemExit("core payload carries no welsh.static manifest (D79)")
    html = _SL.stamp(html, {v["en"]: k for k, v in _static.items()})
    bad = _SL.verify(html.replace("__SCHOOL_NAME__", school_name), _static)
    if bad:
        raise SystemExit("D79 static lane does not verify:\n  " + "\n  ".join(bad))
    if _SL.attribute_literals(html):
        raise SystemExit("D80: legacy text-bearing attributes still in the markup: "
                         + str(_SL.attribute_literals(html)))

    payload = json.dumps(core, ensure_ascii=False, separators=SEP).replace("</", "<\\/")
    html = html.replace("__REPORT_JSON__", payload)
    if not _APP_TAG.search(html):
        raise SystemExit("template has no <script>/*__APP_JS__*/</script> block")
    app_path = assets["files"]["app"]["path"]
    html = _APP_TAG.sub(f'<script src="{base}{app_path}"></script>', html, count=1)
    html = html.replace("__SCHOOL_NAME__", school_name)
    html = html.replace("/*__FONTS_CSS__*/", fonts_css_urls(base))
    for token, path in assets["tokens"].items():
        if token not in html:
            raise SystemExit(f"template carries no {token}")
        html = html.replace(token, base + path)
    left = re.findall(r"__[A-Z0-9_]+__", html)
    if left:
        raise SystemExit(f"unreplaced template tokens: {sorted(set(left))}")
    for pat in _BANNED_2022:
        if re.search(pat, html):
            raise SystemExit(f"2022-claim gate failed: pattern {pat!r} present")
    return html


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a_ = sub.add_parser("assets"); a_.add_argument("release_out"); a_.add_argument("--release", required=True)
    a_.add_argument("--yac", default=str(ROOT / "inputs" / "yac images V4.16"))
    a_.add_argument("--fonts", default=str(ROOT / "inputs" / "fonts"))
    a_.add_argument("--cover", default=str(ROOT / "config" / "cover_media"))
    a = ap.parse_args(argv)
    man = build_assets(Path(a.release_out), a.release, Path(a.yac), Path(a.fonts), Path(a.cover))
    total = sum(f["bytes"] for f in man["files"].values())
    print(json.dumps({"release": a.release, "files": len(man["files"]), "bytes": total,
                      "app": man["files"]["app"]["path"]}, indent=1))


if __name__ == "__main__":
    main()
