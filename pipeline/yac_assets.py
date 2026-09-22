# -*- coding: utf-8 -*-
"""Young Artists Competition artwork (V4.16): the fourteen winning entries
supplied by Sport Wales on 22 Sep 2026 ("Finals YCA"), placed once each in
the report in place of the three Brain Break characters (Corrective Brief
section 5 withheld the artwork; the owner's instruction of 22 Sep 2026
reintroduces it).

Every image is an <img> with an alt frame on Framework sheet 43
(``ui.alt_yac_*``): the English alt text is the frame's English, the Welsh
is the translator's (PENDING until returned — shown as marked English in
Welsh mode, like every pending frame). No pupil's name appears anywhere:
the alt text describes the picture only.

The files are embedded as they were supplied, through one deterministic
path: crop the transparent margin (the artwork itself is untouched), scale
to the width the placement needs, encode as WebP with alpha. One file
("football eplosion .png") was supplied with its transparent background
flattened to a faint white/grey checker; ``clear_background`` restores the
transparency by taking every near-white, unsaturated pixel outside the
ball's drawn outline as background (the ball's white panels are kept).

    python -m pipeline.yac_assets <yac_dir>        # lists what would be embedded
"""
from __future__ import annotations

import base64
import io
import math
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageFilter

# key, file, template token, embed width (px), crop, clear_bg, source of the alt text
YAC = [
    ("ui.alt_yac_dragon_kit",      "top of page - full width.png",              "__IMG_YAC_DRAGON_KIT__",      600,  True,  False, "described from the artwork"),
    ("ui.alt_yac_welsh_symbols",   "walesh symbols - bottom of page.png",       "__IMG_YAC_WELSH_SYMBOLS__",   1100, True,  False, "described from the artwork"),
    ("ui.alt_yac_balls",           "balls - bottom of page.png",                "__IMG_YAC_BALLS__",           1100, True,  False, "described from the artwork"),
    ("ui.alt_yac_footballer",      "footballer yac.png",                        "__IMG_YAC_FOOTBALLER__",      900,  True,  False, "described from the artwork"),
    ("ui.alt_yac_football_splash", "football eplosion .png",                    "__IMG_YAC_FOOTBALL_SPLASH__", 560,  True,  True,  "described from the artwork"),
    ("ui.alt_yac_cyclist",         "Cyclist kneeling beside his pink bike.png", "__IMG_YAC_CYCLIST__",         520,  True,  False, "survey mascot description (S16, p_9325948_desc) + the artwork"),
    ("ui.alt_yac_dragon_football", "Dragon Image ILR (2).png",                  "__IMG_YAC_DRAGON_FOOTBALL__", 400,  True,  False, "survey mascot description (S16, p_9325958_desc) + the artwork"),
    ("ui.alt_yac_heart",           "idependant page - heasrt.png",              "__IMG_YAC_HEART__",           520,  True,  False, "described from the artwork"),
    ("ui.alt_yac_horse",           "right side of a page - horse.png",          "__IMG_YAC_HORSE__",           560,  True,  False, "described from the artwork"),
    ("ui.alt_yac_tennis_football", "tennis ball & football.png",                "__IMG_YAC_TENNIS_FOOTBALL__", 520,  True,  False, "described from the artwork"),
    ("ui.alt_yac_gymnastics",      "YCA GYmnastics.png",                        "__IMG_YAC_GYMNASTICS__",      520,  True,  False, "survey mascot description (S16, p_9325956_desc) + the artwork"),
    ("ui.alt_yac_cricket",         "Cricket shot in mid-swing.png",             "__IMG_YAC_CRICKET__",         560,  True,  False, "survey mascot description (S16, p_9325957_desc) + the artwork"),
    ("ui.alt_yac_basketball",      "Basketball image ILR.png",                  "__IMG_YAC_BASKETBALL__",      520,  True,  False, "survey mascot description (S16, p_9325976_desc) + the artwork"),
    ("ui.alt_yac_dragon_wales",    "dragon with wales.png",                     "__IMG_YAC_DRAGON_WALES__",    520,  True,  False, "survey mascot description (S16, p_9325985_desc) + the artwork"),
]

# The English alt text of each frame (sheet 43, column D). A description of
# the picture only — no pupil's name, region or school.
ALT_EN = {
    "ui.alt_yac_dragon_kit":      "Young Artists Competition drawing: a red dragon in a white Wales shirt numbered 11, holding a rugby ball, with one foot on a football and a leek in its tail",
    "ui.alt_yac_welsh_symbols":   "Young Artists Competition drawing: symbols of Wales and sport together — a daffodil, a football, a cricket bat and ball, a red dragon, a rugby ball and a leek",
    "ui.alt_yac_balls":           "Young Artists Competition drawing: a row of four balls — a red cricket ball, a black ball with white spots, an orange basketball and a black eight-ball",
    "ui.alt_yac_footballer":      "Young Artists Competition drawing: a footballer with long fair hair, in a blue number 7 shirt, white shorts and pink boots, kicking a football",
    "ui.alt_yac_football_splash": "Young Artists Competition drawing: a football with red and green panels bursting out of a splash of red and green paint",
    "ui.alt_yac_cyclist":         "Young Artists Competition drawing: a mountain biker in a helmet leaning low over a pink bike as it goes over a jump, against a blue watercolour splash",
    "ui.alt_yac_dragon_football": "Young Artists Competition drawing: a smiling red dragon with cream wings, standing beside a football",
    "ui.alt_yac_heart":           "Young Artists Competition drawing: a red heart holding four scenes of a red dragon playing football, rugby, gymnastics and cricket",
    "ui.alt_yac_horse":           "Young Artists Competition drawing: a rider in a red jacket and black helmet jumping a brown horse",
    "ui.alt_yac_tennis_football": "Young Artists Competition drawing: a football above a bright green tennis ball",
    "ui.alt_yac_gymnastics":      "Young Artists Competition drawing: a gymnastics club — one gymnast leaping above a balance beam, another hanging from a high bar, beside a stack of coloured rings",
    "ui.alt_yac_cricket":         "Young Artists Competition drawing: a cricketer in a helmet, gloves and pads, swinging a bat at a red ball",
    "ui.alt_yac_basketball":      "Young Artists Competition drawing: a basketball player with a ponytail, in a red vest and black shorts, leaping to shoot a basketball framed by a red starburst",
    "ui.alt_yac_dragon_wales":    "Young Artists Competition drawing: a red Welsh dragon with the word WALES in green letters across it",
}

RETIRED = ("ui.alt_brain_javelin", "ui.alt_brain_football", "ui.alt_brain_basketball")


def crop_margin(im: Image.Image, pad_frac: float = 0.02) -> Image.Image:
    """Crop the fully transparent margin, keeping a small padding. The
    artwork's own pixels are never changed."""
    im = im.convert("RGBA")
    bbox = im.getchannel("A").point(lambda a: 255 if a > 8 else 0).getbbox()
    if not bbox:
        return im
    pad = int(round(max(im.size) * pad_frac))
    l, t, r, b = bbox
    return im.crop((max(0, l - pad), max(0, t - pad), min(im.width, r + pad), min(im.height, b + pad)))


def clear_background(im: Image.Image) -> Image.Image:
    """Restore the transparency of a drawing whose transparent background was
    supplied flattened to a faint white/grey checker: every near-white,
    unsaturated pixel OUTSIDE the ball's drawn outline becomes transparent.
    The outline is found by ray-casting from the centroid of the dark
    (outline) pixels: the farthest dark pixel on each ray, median-smoothed
    around the circle. Deterministic; the coloured pixels are untouched."""
    import numpy as np
    a = np.array(im.convert("RGBA")).astype(int)
    h, w = a.shape[:2]
    rgb = a[..., :3]
    luma = rgb.mean(axis=2)
    chroma = rgb.max(axis=2) - rgb.min(axis=2)
    dark = (luma < 110) & (chroma < 60)
    ys, xs = np.where(dark)
    cx, cy = xs.mean(), ys.mean()
    n = 1440
    rad = np.zeros(n)
    for k in range(n):
        th = 2 * math.pi * k / n
        far = 0
        for r in range(int(min(h, w) * 0.175), int(min(h, w) * 0.37)):
            x = int(round(cx + r * math.cos(th)))
            y = int(round(cy + r * math.sin(th)))
            if 0 <= x < w and 0 <= y < h and dark[y, x]:
                far = r
        rad[k] = far
    fill = np.median(rad[rad > 0])
    for k in range(n):
        if rad[k] == 0:
            rad[k] = rad[k - 1] if rad[k - 1] else fill
    sm = np.array([np.median(np.take(rad, range(k - 10, k + 11), mode="wrap")) for k in range(n)])
    yy, xx = np.mgrid[0:h, 0:w]
    ang = (np.arctan2(yy - cy, xx - cx) % (2 * math.pi)) * n / (2 * math.pi)
    ridx = np.clip(np.round(ang).astype(int), 0, n - 1)
    dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
    ball = dist <= sm[ridx] + 3
    bg_like = (luma >= 228) & (chroma <= 14)
    transparent = bg_like & ~ball
    alpha = np.full((h, w), 255, int)
    alpha[transparent] = 0
    grown = np.array(Image.fromarray((transparent * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3))) > 0
    ring = grown & ~transparent & ~ball
    ramp = np.clip((252 - luma) * 255 / 60, 0, 255).astype(int)
    alpha[ring] = np.minimum(alpha[ring], np.maximum(ramp[ring], 40))
    out = a.copy()
    out[..., 3] = alpha
    return Image.fromarray(out.astype("uint8"))


def prepared(path: Path, max_w: int, crop: bool, clear_bg: bool) -> Image.Image:
    im = Image.open(path).convert("RGBA")
    if clear_bg:
        im = clear_background(im)
    if crop:
        im = crop_margin(im)
    if im.width > max_w:
        im = im.resize((max_w, round(im.height * max_w / im.width)), Image.LANCZOS)
    return im


def data_uri(path: Path, max_w: int, crop: bool = True, clear_bg: bool = False) -> str:
    im = prepared(path, max_w, crop, clear_bg)
    buf = io.BytesIO()
    im.save(buf, "WEBP", quality=84, method=6)
    return "data:image/webp;base64," + base64.b64encode(buf.getvalue()).decode()


def embed_all(html: str, yac_dir: Path) -> tuple[str, dict]:
    """Replace every artwork token; returns (html, {key: bytes})."""
    sizes = {}
    for key, fname, token, w, crop, clear_bg, _src in YAC:
        p = yac_dir / fname
        if not p.exists():
            raise SystemExit(f"Young Artists Competition file missing: {p}")
        if token not in html:
            raise SystemExit(f"template carries no {token} for {fname}")
        uri = data_uri(p, w, crop, clear_bg)
        sizes[key] = len(uri)
        html = html.replace(token, uri)
    return html, sizes


def main():
    d = Path(sys.argv[1])
    for key, fname, token, w, crop, clear_bg, src in YAC:
        im = prepared(d / fname, w, crop, clear_bg)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=84, method=6)
        print(f"{key:32s} {fname!r:46s} {im.width}x{im.height} webp {len(buf.getvalue())/1024:6.1f} KB  alt: {ALT_EN[key][:60]}…")


if __name__ == "__main__":
    main()
