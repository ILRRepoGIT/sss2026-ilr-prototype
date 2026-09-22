# -*- coding: utf-8 -*-
"""A local static server for the served-package gate and the browser probe
(review P0.7: "load through an HTTP staging origin with production headers
and compression"). Serves a site tree with the same headers Front Door adds
in production, gzip for JSON/HTML/JS, 404 for directory listings and
unknown paths, and never lists a directory.

    python -m prod.serve_local <site_dir> [--port 8765]
"""
from __future__ import annotations

import argparse
import gzip
import mimetypes
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HEADERS = {
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data:; font-src 'self' data:; connect-src 'self'; base-uri 'none'; "
                                "frame-ancestors 'none'; form-action 'none'"),
}
COMPRESS = {".json", ".html", ".js", ".css", ".svg", ".txt"}


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, root: Path, **k):
        self.root = root
        super().__init__(*a, directory=str(root), **k)

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))

    def do_GET(self):
        path = self.path.split("?", 1)[0].split("#", 1)[0]
        fs = (self.root / path.lstrip("/")).resolve()
        if path.endswith("/"):
            fs = fs / "index.html"
        try:
            fs.relative_to(self.root.resolve())
        except ValueError:
            return self._404()
        if not fs.is_file() or fs.name == "package_index.json":
            return self._404()
        data = fs.read_bytes()
        ctype = mimetypes.guess_type(str(fs))[0] or "application/octet-stream"
        if fs.suffix == ".js":
            ctype = "application/javascript"
        self.send_response(200)
        self.send_header("Content-Type", ctype + ("; charset=utf-8" if ctype.startswith("text/") or "json" in ctype or "javascript" in ctype else ""))
        for k, v in HEADERS.items():
            self.send_header(k, v)
        if path.startswith("/r/"):
            self.send_header("Cache-Control", "public, max-age=31536000, immutable")
        else:
            self.send_header("Cache-Control", "no-cache, must-revalidate")
        ae = self.headers.get("Accept-Encoding", "")
        if fs.suffix in COMPRESS and "gzip" in ae:
            data = gzip.compress(data, 6)
            self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        if not getattr(self, "_head_only", False):
            self.wfile.write(data)

    def do_HEAD(self):
        self._head_only = True
        try:
            self.do_GET()
        finally:
            self._head_only = False

    def _404(self):
        body = (self.root / "404.html").read_bytes() if (self.root / "404.html").exists() else b"not found"
        self.send_response(404)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        for k, v in HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def serve(root: Path, port: int):
    httpd = ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, root=root))
    print(f"serving {root} at http://127.0.0.1:{port}/", flush=True)
    httpd.serve_forever()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("site_dir"); ap.add_argument("--port", type=int, default=8765)
    a = ap.parse_args(argv)
    serve(Path(a.site_dir), a.port)


if __name__ == "__main__":
    main()
