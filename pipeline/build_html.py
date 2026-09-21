"""Assemble the single-file interactive report (v2).

Injects into web/template.html (stamped with the D79 static-lane keys):
  - the report package JSON (disclosure-safe aggregates + narrative only)
  - the client application (web/app.js)
  - optimised base64 WebP image assets (Young Artist + Brain Break)
  - the mandatory cover assets extracted from the supplied title-page
    Word document (white Sport Wales logo, official 2026 lockup)
  - base64 Montserrat webfonts (400 / 600 / 800, OFL licensed)

Usage:
    python -m pipeline.build_html <report.json> <yac_assets_dir> <fonts_dir> \
        <cover_media_dir> [out.html]
"""
from __future__ import annotations

import base64
import io
import json
import sys
from pathlib import Path

from PIL import Image

from .common import GENERATED_DIR, ROOT

# Young Artist artwork is temporarily withheld from the generated report
# (Corrective Brief section 5); the assets remain in the project library for
# deliberate reintroduction. Only the Brain Break characters are embedded.
YAC_IMAGES = {
    "__IMG_BRAIN_JAV__":  ("wheelchair javlin thrower.png", 560),
    "__IMG_BRAIN_FOOT__": ("football.png", 460),
    "__IMG_BRAIN_BASK__": ("basketball.png", 460),
}
COVER_IMAGES = {
    "__SW_LOGO_WHITE__": ("image1.png", 500),   # white Sport Wales logo
    "__LOCKUP_2026__":   ("image3.png", 940),   # official 2026 SSS lockup
}
FONT_FACES = [("400", "montserrat-latin-400-normal.woff2"),
              ("600", "montserrat-latin-600-normal.woff2"),
              ("800", "montserrat-latin-800-normal.woff2")]


def image_data_uri(path: Path, max_w: int) -> str:
    im = Image.open(path)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def fonts_css(fonts_dir: Path) -> str:
    css = []
    for weight, fname in FONT_FACES:
        b64 = base64.b64encode((fonts_dir / fname).read_bytes()).decode()
        css.append(
            "@font-face{font-family:'Montserrat';font-style:normal;"
            f"font-weight:{weight};font-display:swap;"
            f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}")
    return "\n".join(css)


def main():
    if len(sys.argv) < 5:
        raise SystemExit(__doc__)
    report_json = Path(sys.argv[1])
    yac_dir = Path(sys.argv[2])
    fonts_dir = Path(sys.argv[3])
    cover_dir = Path(sys.argv[4])
    out = Path(sys.argv[5]) if len(sys.argv) > 5 else GENERATED_DIR / "report.html"

    html = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
    app_js = (ROOT / "web" / "app.js").read_text(encoding="utf-8")

    package = json.loads(report_json.read_text(encoding="utf-8"))
    # D79 (Framework v2.2): stamp data-i18n="<key>" on every translator-
    # owned static text node, bound by its English to the payload manifest
    # welsh.static; an unbound node or row fails the build, and the stamped
    # markup is verified the way gate v7 verifies it (CAT-static-bound /
    # CAT-static-english) before anything is written.
    from . import static_lane as _SL
    _static = (package.get("welsh") or {}).get("static") or {}
    if not _static:
        raise SystemExit("payload carries no welsh.static manifest (D79)")
    html = _SL.stamp(html, {v["en"]: k for k, v in _static.items()})
    _bad = _SL.verify(html.replace("__SCHOOL_NAME__", package["school"]["name"]),
                      _static)
    if _bad:
        raise SystemExit("D79 static lane does not verify:\n  " + "\n  ".join(_bad))
    if _SL.attribute_literals(html):
        raise SystemExit("D80: legacy text-bearing attributes still in the markup: "
                         + str(_SL.attribute_literals(html)))
    payload = json.dumps(package, ensure_ascii=False, separators=(",", ":"))
    payload = payload.replace("</", "<\\/")
    html = html.replace("__REPORT_JSON__", payload)
    html = html.replace("/*__APP_JS__*/", app_js.replace("</", "<\\/"))
    html = html.replace("__SCHOOL_NAME__", package["school"]["name"])
    html = html.replace("/*__FONTS_CSS__*/", fonts_css(fonts_dir))

    for token, (fname, w) in YAC_IMAGES.items():
        html = html.replace(token, image_data_uri(yac_dir / fname, w))
    for token, (fname, w) in COVER_IMAGES.items():
        html = html.replace(token, image_data_uri(cover_dir / fname, w))

    out.parent.mkdir(parents=True, exist_ok=True)
    # v2.3 gate (Finding 2): the assembled report must carry no unsigned
    # 2022 equivalence claim outside the agreed caveat formulations.
    import re as _re
    banned = [r"matches the measure used in", r"same measure as the 2022",
              r"can be set alongside", r"so this figure can be compared with 2022"]
    for pat in banned:
        if _re.search(pat, html):
            raise SystemExit(f"2022-claim gate failed: pattern {pat!r} present")
    out.write_text(html, encoding="utf-8")
    print(f"report: {out} ({out.stat().st_size/1e6:.1f} MB)")


if __name__ == "__main__":
    main()

# EOF sentinel
