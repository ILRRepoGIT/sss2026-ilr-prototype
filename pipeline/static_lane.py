# -*- coding: utf-8 -*-
"""The static translator lane as a BOUND row (Framework v2.2, D79 / D80).

Every translator-owned text node in the static page markup (web/template.html
before the report-data block) is a handoff row keyed ui###. This module is the
one place that (a) finds those text nodes, (b) binds each to its handoff key
by its ENGLISH — the English is the source of the key, so an edit to the
markup that is not carried to the handoff fails the build instead of
silently orphaning a translation — and (c) stamps data-i18n="<key>" on the
node at build time. The client's renderStatic() then swaps the node's text
from the payload manifest welsh.static = {key: {en, cy, consumer}} on every
language change (gates CAT-static-manifest / -bound / -english / -swap;
browser gate v3 BROWSER-toggle).

Nothing here decides what a string says: keys come from the translation
handoff workbook ("Strings" sheet, carried in config/welsh_lexicon.json) and
the text comes from the template. A page text node with no handoff row, or a
ui### row with no page node, is a build failure (D79) — regenerate the
handoff with make_translation_handoff and re-run the lexicon build.

The four fixed text-bearing attributes (D80) — data-ct-key, data-nh-key,
data-also-h-key, data-sh-key — hold manifest keys too; their strings are
sheet-28 rows and the client resolves them through staticStr().
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

STATIC_KEY = re.compile(r"^ui\d{3}$")
ATTR_KEYS = ("data-ct-key", "data-nh-key", "data-also-h-key", "data-sh-key")
# D80: the old language-blind attribute names must not survive in the markup
LEGACY_ATTRS = ("data-ct", "data-nh", "data-also-h", "data-sh")

VOID = {"br", "img", "input", "hr", "meta", "link", "source", "wbr", "col",
        "area", "base", "embed", "param", "track"}
# content of these elements is never translator-owned page text
SKIP_TAGS = {"script", "style", "svg", "noscript", "template", "select"}
PLACEHOLDER = re.compile(r"^__[A-Z0-9_]+__$")
# Containers the CLIENT owns: their content is written from the language
# layer (frames / catalogue / labels) at run time, so a static key on them
# would be overwritten — and the browser gate's fixture toggle would rightly
# report the key as unrendered.
CLIENT_OWNED_IDS = {
    "rail-toggle", "btn-lang", "f-cohort", "rail-base", "vb-desc", "vb-base",
    "h1-view", "intro-count", "intro-years", "overview-note",
    "any-activity-note", "pf-view", "overview-table", "static-profile",
    "profile-extra", "meta-table", "appendices", "h2-list", "h1-an", "h1-ev",
    "h1-ll", "h1-en", "f-scope", "f-gender", "f-group", "live-region",
    "variation-table", "f14-table", "cover-school",
    # V4.11: slot-bearing sentences are sheet-43 frames the client writes
    "intro-sentence", "faq-included", "faq-missing",
    # the Welsh-only review note (already Welsh; shown in Welsh mode only)
    "review-note-cy",
}
CLIENT_OWNED_CLASSES = {
    # the client writes narrative and chart output into these SLOTS only;
    # the static heading / note beside a slot is translator furniture
    "rep-body", "rep-body-also", "chart-slot", "stack-slot",
    "stack-table-slot", "dyn-count", "dyn-rows", "dyn-sportcount",
    # the chapter bands carry a fixed Welsh subtitle beside the English
    # heading — already Welsh, not a translator row (see the V4.9 register)
    "cy",
}
CLIENT_OWNED_ID_PREFIXES = ("rows-",)

# V4.10 (resolves V4.9 register item 6, "inline-markup context-free rows"):
# a paragraph-level element whose only child elements are inline emphasis
# (and whose text carries no client-owned slot, placeholder or link) is ONE
# translator row — the whole paragraph, with its emphasis — instead of a
# chain of context-free fragments that no translator can render in Welsh
# word order. The row's English is the tag-stripped text (exactly what gate
# v7 compares, CAT-static-english); the emphasis travels in `html`.
BLOCK_TAGS = {"p", "li", "summary", "figcaption", "h1", "h2", "h3", "h4",
              "h5", "h6", "dd", "dt"}
INLINE_TAGS = {"strong", "em", "b", "i", "br"}

TOKEN = re.compile(r"<!--.*?-->|<[^>]+>|[^<]+", re.S)
TAG = re.compile(r"<(/?)([A-Za-z][A-Za-z0-9-]*)([^>]*?)(/?)>", re.S)


def norm(s: str) -> str:
    """The comparison form the gates use: whitespace collapsed, stripped
    (tags are never inside a text node)."""
    return re.sub(r"\s+", " ", s).strip()


@dataclass
class El:
    tag: str
    attrs: str
    start: Tuple[int, int]          # span of the start tag in the source
    end: Optional[Tuple[int, int]] = None
    children: list = field(default_factory=list)
    parent: Optional["El"] = None

    def attr(self, name: str) -> Optional[str]:
        m = re.search(r'\s' + re.escape(name) + r'="([^"]*)"', self.attrs)
        return m.group(1) if m else None

    def path(self) -> str:
        i, c = self.attr("id"), self.attr("class")
        return self.tag + ("#" + i if i else "") + \
            ("." + c.split()[0] if c else "")


@dataclass
class Tx:
    span: Tuple[int, int]
    raw: str
    parent: El


@dataclass
class Node:
    """One translator-owned text run in the static markup."""
    text: str                       # normalised English (the key's source)
    consumer: str                   # element path (for the manifest)
    element: Optional[El]           # element to stamp (sole text child) …
    run: Optional[Tx]               # … or the run to wrap in a span
    order: int
    html: Optional[str] = None      # V4.10 block row: inner markup (emphasis)


def _client_owned(el: El) -> bool:
    e = el
    while e is not None:
        if e.tag in SKIP_TAGS:
            return True
        i = e.attr("id") or ""
        if i in CLIENT_OWNED_IDS or i.startswith(CLIENT_OWNED_ID_PREFIXES):
            return True
        cls = set((e.attr("class") or "").split())
        if cls & CLIENT_OWNED_CLASSES:
            return True
        if e.attr("data-frame") is not None:      # V4.11: a frame host
            return True
        e = e.parent
    return False


def _parse(html: str) -> Tuple[El, List[Tx]]:
    """A minimal tree of the (hand-written, well-formed) static markup."""
    root = El("#root", "", (0, 0))
    cur = root
    texts: List[Tx] = []
    for m in TOKEN.finditer(html):
        tok = m.group(0)
        if tok.startswith("<!--"):
            continue
        if tok.startswith("<"):
            t = TAG.match(tok)
            if not t:
                continue
            closing, name, attrs, selfclose = t.groups()
            name = name.lower()
            if closing:
                # pop to the matching open element
                e = cur
                while e is not None and e.tag != name:
                    e = e.parent
                if e is not None:
                    e.end = m.span()
                    cur = e.parent or root
                continue
            el = El(name, attrs, m.span(), parent=cur)
            cur.children.append(el)
            if name in VOID or selfclose:
                el.end = m.span()
                continue
            cur = el
        else:
            tx = Tx(m.span(), tok, cur)
            cur.children.append(tx)
            texts.append(tx)
    return root, texts


def static_head(html: str) -> str:
    """The static markup before the report-data block (what the runner
    reads as the page head)."""
    i = html.find('<script id="report-data"')
    return html if i < 0 else html[:i]


def _block_of(el: El, html: str) -> Optional[str]:
    """V4.10: the inner markup of `el` when it qualifies as ONE translator
    row — a BLOCK_TAGS element with at least one inline emphasis child,
    at least one text run, every descendant element in INLINE_TAGS with no
    id/class, and no placeholder or client-owned content. Else None."""
    if el.tag not in BLOCK_TAGS or el.end is None:
        return None
    if _client_owned(el):
        return None
    has_inline, has_text = False, False
    # the paragraph must carry text of its own OUTSIDE the emphasis: a
    # <li><strong>X</strong></li> is the sole-child row X, not a block
    has_text = any(isinstance(c, Tx) and norm(c.raw) for c in el.children)
    stack = list(el.children)
    while stack:
        c = stack.pop()
        if isinstance(c, Tx):
            if norm(c.raw):
                if PLACEHOLDER.match(norm(c.raw)):
                    return None
        else:
            if c.tag not in INLINE_TAGS or c.attr("id") or c.attr("class"):
                return None
            if c.tag != "br":
                has_inline = True
            stack.extend(c.children)
    if not (has_inline and has_text):
        return None
    inner = html[el.start[1]:el.end[0]]
    # Every emphasis boundary must sit on whitespace: gate v7 compares the
    # tag-stripped text with tags replaced by a SPACE, the browser gate
    # compares textContent — "pupils”</em>." would read differently to the
    # two, so such a paragraph stays a chain of fragment rows (the ingest
    # tool splits the translator's paragraph on their own emphasis runs).
    stripped = inner.strip()
    for m in re.finditer(r"<(/?)([a-z]+)[^>]*>", stripped):
        if m.group(2) == "br":
            continue
        if m.group(1):                                   # closing tag
            after = stripped[m.end():m.end() + 1]
            if after and not after.isspace():
                return None
        else:                                            # opening tag
            before = stripped[m.start() - 1:m.start()]
            if before and not before.isspace():
                return None
    return re.sub(r"\s+", " ", inner).strip()


def block_text(inner_html: str) -> str:
    """The English of a block row: tags stripped, whitespace collapsed —
    the exact comparison form of gate v7 (CAT-static-english)."""
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", inner_html)).strip()


def extract(html: str) -> List[Node]:
    """Every translator-owned text run in the static markup, in document
    order. A run is bound to its ELEMENT when it is the element's only
    non-blank child, otherwise it is a run to be wrapped. V4.10: a
    paragraph with inline emphasis is one BLOCK row (see _block_of)."""
    head = static_head(html)
    body_at = head.find("<body")
    root, texts = _parse(head)
    out: List[Node] = []
    n = 0
    blocks: Dict[int, str] = {}        # id(el) -> inner markup
    claimed: set = set()               # id(tx) runs inside a block
    for tx in texts:
        if tx.span[0] < body_at or id(tx) in claimed:
            continue
        # the nearest BLOCK_TAGS ancestor decides whether this run is part
        # of a block row
        anc = tx.parent
        while anc is not None and anc.tag not in BLOCK_TAGS:
            anc = anc.parent
        if anc is not None and id(anc) not in blocks:
            inner = _block_of(anc, head)
            if inner is not None:
                blocks[id(anc)] = inner
                n += 1
                out.append(Node(block_text(inner), anc.path(), anc, None, n,
                                html=inner))
                st = list(anc.children)
                while st:
                    c = st.pop()
                    if isinstance(c, Tx):
                        claimed.add(id(c))
                    else:
                        st.extend(c.children)
                continue
        if anc is not None and id(anc) in blocks:
            continue
        text = norm(tx.raw)
        if not text or not re.search(r"[A-Za-zÀ-ÿŵŷ]", text):
            continue
        if PLACEHOLDER.match(text):
            continue
        if _client_owned(tx.parent):
            continue
        parent = tx.parent
        siblings = [c for c in parent.children
                    if not (isinstance(c, Tx) and not norm(c.raw))]
        sole = len(siblings) == 1 and siblings[0] is tx and parent.tag != "#root"
        n += 1
        if sole:
            out.append(Node(text, parent.path(), parent, None, n))
        else:
            out.append(Node(text, "span (run) in " + parent.path(), None, tx, n))
    return out


def attribute_literals(html: str) -> List[Tuple[str, str]]:
    """(attribute, value) for every legacy text-bearing attribute still in
    the markup — D80 requires none."""
    head = static_head(html)
    out = []
    for a in LEGACY_ATTRS:
        for m in re.finditer(r'\s' + a + r'="([^"]*)"', head):
            out.append((a, m.group(1)))
    return out


def attribute_keys(html: str) -> List[Tuple[str, str]]:
    """(attribute, key) for every keyed fixed attribute in the markup."""
    head = static_head(html)
    out = []
    for a in ATTR_KEYS:
        for m in re.finditer(r'\s' + a + r'="([^"]*)"', head):
            out.append((a, m.group(1)))
    return out


def bind(html: str, en_to_key: Dict[str, str]) -> Tuple[Dict[str, dict], List[str]]:
    """Bind every static text run to its handoff key by its English.

    Returns (manifest_rows, problems): manifest_rows = {key: {en, consumer,
    count}}; problems lists page runs with no handoff row (D79 key drift)
    and keyed attributes with no row. Callers fail the build on problems.
    """
    rows: Dict[str, dict] = {}
    problems: List[str] = []
    for nd in extract(html):
        k = en_to_key.get(nd.text)
        if not k:
            problems.append(f"static text node with no handoff row "
                            f"({nd.consumer}): {nd.text[:70]!r}")
            continue
        r = rows.setdefault(k, {"en": nd.text, "consumer": nd.consumer,
                                "count": 0})
        if nd.html is not None:
            r["html"] = nd.html
        r["count"] += 1
        if r["consumer"] != nd.consumer and " | " not in r["consumer"] \
                and r["count"] <= 3:
            r["consumer"] += " | " + nd.consumer
    for a, k in attribute_keys(html):
        if k not in en_to_key.values():
            problems.append(f'{a}="{k}" names a key with no handoff row')
    for a, v in attribute_literals(html):
        problems.append(f'{a}="{v[:50]}" is a literal, not a catalogue key (D80)')
    return rows, problems


def stamp(html: str, en_to_key: Dict[str, str]) -> str:
    """The template with data-i18n="<key>" on every bound text node: the
    attribute goes on the element when the run is its only child, else the
    run is wrapped in <span data-i18n>. Whitespace around a wrapped run stays
    outside the span. Fails loudly on an unbound run (D79)."""
    nodes = extract(html)
    inserts: List[Tuple[int, str]] = []
    for nd in nodes:
        k = en_to_key.get(nd.text)
        if not k:
            raise SystemExit(f"D79: static text node has no handoff row "
                             f"({nd.consumer}): {nd.text[:70]!r} — regenerate "
                             f"the translation handoff (make_translation_handoff)")
        if nd.element is not None:
            s, e = nd.element.start
            tag = html[s:e]
            cut = e - 2 if tag.endswith("/>") else e - 1
            if 'data-i18n="' in tag:
                raise SystemExit(f"D79: {nd.consumer} already carries data-i18n")
            inserts.append((cut, f' data-i18n="{k}"'))
        else:
            s, e = nd.run.span
            raw = nd.run.raw
            lead = len(raw) - len(raw.lstrip())
            trail = len(raw) - len(raw.rstrip())
            inserts.append((s + lead, f'<span data-i18n="{k}">'))
            inserts.append((e - trail, "</span>"))
    out = html
    for pos, ins in sorted(inserts, key=lambda x: -x[0]):
        out = out[:pos] + ins + out[pos:]
    return out


def verify(html: str, static: Dict[str, dict]) -> List[str]:
    """Assert the stamped markup against the manifest the way gate v7 does
    (CAT-static-bound / CAT-static-english): every manifest key has an
    element, every element a row, every element's English equals the row."""
    head = static_head(html)
    NORM = lambda x: re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", x)).strip()
    dom: Dict[str, List[str]] = {}
    for m in re.finditer(r'<(\w+)\b[^>]*\sdata-i18n="([^"]+)"[^>]*>(.*?)</\1>',
                         head, re.S):
        dom.setdefault(m.group(2), []).append(NORM(m.group(3)))
    problems = []
    for k in static:
        if k not in dom:
            problems.append(f"{k}: manifest key with no data-i18n element")
    for k, texts in dom.items():
        if k not in static:
            problems.append(f"{k}: data-i18n element names a key with no manifest row")
            continue
        en = NORM(str(static[k].get("en") or ""))
        for tx in texts:
            if tx != en:
                problems.append(f"{k}: page says {tx[:50]!r}; manifest en is {en[:50]!r}")
    return problems
