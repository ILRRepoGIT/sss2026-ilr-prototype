# -*- coding: utf-8 -*-
"""Publication: private staging → verification → publication index → atomic
activation, and genuine withdrawal and rollback (deployment plan §3, §9
Phase 8; review P0.8, P0.9, P0.10, G13, G14).

    python -m prod.publish stage        --release <tag> --out <out_root> --account <web account>
    python -m prod.publish verify-staging --release <tag> --evidence <root> --account <web account>
    python -m prod.publish index        --release <tag> --evidence <root> --approver "<name>" --approver2 "<name>" [--waiver <file>]
    python -m prod.publish promote      --release <tag> --evidence <root> --account <web account> --profile <afd> --rg <rg> --endpoint <ep>
    python -m prod.publish withdraw     --release <tag> --evidence <root> --account <web account> --profile <afd> --rg <rg> --endpoint <ep> --school <id> --reason "<text>"
    python -m prod.publish rollback     --release <tag> --to <previous tag> --evidence <root> --account <web account> --profile <afd> --rg <rg> --endpoint <ep>

All commands print what they do and take --dry-run. They use the Azure CLI
and AzCopy. --auth chooses whose identity AzCopy uses: `identity` (default —
the VM's managed identity, for stage/verify-staging) or `azcli` (the account
that ran `az login` on this machine — the named publisher, for promote /
withdraw / rollback after the runbook has moved the $web and purge roles
away from the VM, so that the machine that built cannot also publish).
`az afd endpoint purge` always runs as the Azure CLI's signed-in account.

The model (P0.8): the release tree — /r/<tag>/assets/… and /r/<tag>/<token>/…,
every file content-hashed and immutable — is uploaded to the PRIVATE
`staging` container, verified against the attestations, then copied
server-side into $web. Nothing is reachable at that point, because the
entry pages do not exist yet. Activation writes the ~1,000 small entry pages
/2026/<token>/index.html (Cache-Control: no-cache) — each one a single PUT
that points at the complete, already-verified release tree — then purges
the Front Door cache for /2026/*. A reader therefore sees either the previous
release (complete) or the new one (complete), never a mixture. Rollback
rewrites the entry pages from the previous release's evidence; withdrawal of
one report deletes its entry page (and its chunk directory) and purges its
path, so the link returns 404 at the edge and the origin.

Rule 9: `index` refuses a report whose mode is not "release" unless a signed
waiver file is given; the waiver's sha256 and the two approvers are written
into the publication index and the ledger.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from prod.ledger import Ledger, now


def sh(cmd: list, dry: bool, check=True, capture=False):
    print("$ " + " ".join(str(c) for c in cmd), flush=True)
    if dry:
        return ""
    r = subprocess.run([str(c) for c in cmd], capture_output=capture, text=True)
    if check and r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode}): {(r.stderr or '')[-800:]}")
    return r.stdout if capture else ""


def azcopy_login(a):
    """AzCopy authentication for this command. identity: `azcopy login --identity`
    (the VM's system-assigned identity). azcli: AzCopy auto-login through the
    Azure CLI's signed-in account (AZCOPY_AUTO_LOGIN_TYPE=AZCLI) — the publisher
    ran `az login` as themselves on this machine; nothing is stored."""
    import os
    mode = getattr(a, "auth", "identity") or "identity"
    if mode == "azcli":
        os.environ["AZCOPY_AUTO_LOGIN_TYPE"] = "AZCLI"
        os.environ.pop("AZCOPY_AUTO_LOGIN_TYPE_MSI", None)
        who = sh(["az", "account", "show", "--query", "user.name", "-o", "tsv"], a.dry_run, check=False, capture=True).strip()
        print(f"azcopy auth: Azure CLI account {who or '(dry run)'}", flush=True)
    else:
        azcopy_login(a)


def blob_url(account: str, container: str, path: str = "") -> str:
    return f"https://{account}.blob.core.windows.net/{container}/{path}".rstrip("/")


# --------------------------------------------------------------------------- stage
def stage(a):
    out = Path(a.out) / a.release
    azcopy_login(a)
    # the release tree only — never the private index, the evidence or the entry pages
    sh(["azcopy", "sync", str(out / "r" / a.release), blob_url(a.account, "staging", f"{a.release}/r/{a.release}"),
        "--recursive", "--put-md5", "--exclude-pattern", "package_index.json"], a.dry_run)
    sh(["azcopy", "sync", str(out / "2026"), blob_url(a.account, "staging", f"{a.release}/2026"),
        "--recursive", "--put-md5"], a.dry_run)
    for f in ("404.html", "robots.txt", "health.txt"):
        sh(["azcopy", "copy", str(out / f), blob_url(a.account, "staging", f"{a.release}/{f}"), "--put-md5"], a.dry_run)
    L = Ledger(Path(a.evidence) / a.release / "ledger.sqlite") if a.evidence else None
    if L and not a.dry_run:
        for j in L.jobs(a.release, "built"):
            L.mark(a.release, j["school_id"], "staged")
        L.event(a.release, None, "staging.uploaded", blob_url(a.account, "staging", a.release))


# --------------------------------------------------------------------------- verify staging
def verify_staging(a):
    """Every served file's size and Content-MD5 (stored by azcopy --put-md5) against the attestation inventory (sha256 + md5)."""
    L = Ledger(Path(a.evidence) / a.release / "ledger.sqlite")
    atts = L.attestations(a.release)
    listing = sh(["az", "storage", "blob", "list", "--account-name", a.account, "--container-name", "staging",
                  "--prefix", f"{a.release}/", "--auth-mode", "login", "--num-results", "*",
                  "--query", "[].{n:name,b:properties.contentLength,m:properties.contentSettings.contentMd5}", "-o", "json"],
                 a.dry_run, capture=True)
    if a.dry_run:
        return
    blobs = {b["n"]: b for b in json.loads(listing or "[]")}
    problems = []
    checked = 0
    for sid, att in atts.items():
        for f in att["inventory"]:
            b = blobs.get(f"{a.release}/{f['path']}")
            if not b:
                problems.append(f"{att['slug']}: missing {f['path']}")
            elif int(b["b"]) != f["bytes"]:
                problems.append(f"{att['slug']}: size differs {f['path']}")
            elif f.get("md5") and (b.get("m") or "") != f["md5"]:
                problems.append(f"{att['slug']}: Content-MD5 differs {f['path']}")
            checked += 1
    res = {"release": a.release, "filesChecked": checked, "blobsListed": len(blobs), "problems": problems, "ok": not problems}
    (Path(a.evidence) / a.release / "staging_verify.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(json.dumps({k: v for k, v in res.items() if k != "problems"} | {"problems": problems[:20]}, indent=1))
    if problems:
        sys.exit(1)
    for j in L.jobs(a.release, "staged"):
        L.mark(a.release, j["school_id"], "verified")
    L.event(a.release, None, "staging.verified", f"{checked} files")


# --------------------------------------------------------------------------- publication index
def index(a):
    L = Ledger(Path(a.evidence) / a.release / "ledger.sqlite")
    atts = L.attestations(a.release)
    jobs = {j["school_id"]: j for j in L.jobs(a.release)}
    waiver = None
    if a.waiver:
        wp = Path(a.waiver)
        waiver = {"file": wp.name, "sha256": hashlib.sha256(wp.read_bytes()).hexdigest(), "text": wp.read_text(encoding="utf-8")[:2000]}
    rows = []
    refused = []
    for sid, att in sorted(atts.items()):
        st = jobs.get(sid, {}).get("status")
        if st not in ("verified", "published"):
            refused.append((att["slug"], f"status {st}")); continue
        if not att.get("releaseVerified", False):
            refused.append((att["slug"], "built from an unverified release (--allow-dirty)")); continue
        if att["mode"] != "release" and not waiver:
            refused.append((att["slug"], f"mode {att['mode']} (rule 9: dev builds are not published without a signed waiver)")); continue
        rows.append({"school_id": sid, "slug": att["slug"], "name": att["name"], "token": att["token"],
                     "binding": att["binding"], "entrySha256": next(f["sha256"] for f in att["inventory"] if f["path"].endswith("index.html")),
                     "mode": att["mode"], "files": len(att["inventory"])})
    idx = {"release": a.release, "createdAt": now(), "approvers": [a.approver, a.approver2], "waiver": waiver,
           "reports": rows, "refused": refused, "count": len(rows)}
    body = json.dumps(idx, ensure_ascii=False, indent=1, sort_keys=True)
    idx["sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    p = Path(a.evidence) / a.release / "publication_index.json"
    p.write_text(json.dumps(idx, ensure_ascii=False, indent=1, sort_keys=True), encoding="utf-8")
    L.event(a.release, None, "publication.index", f"{len(rows)} reports, {len(refused)} refused, sha256 {idx['sha256'][:16]}, approvers {a.approver} / {a.approver2}")
    print(f"publication index: {len(rows)} reports approved, {len(refused)} refused -> {p} (sha256 {idx['sha256'][:16]}…)")
    for slug, why in refused[:20]:
        print(f"  refused {slug}: {why}")


# --------------------------------------------------------------------------- promote (atomic activation)
def promote(a):
    ev = Path(a.evidence) / a.release
    idx_p = ev / "publication_index.json"
    if idx_p.exists():
        idx = json.loads(idx_p.read_text(encoding="utf-8"))
    elif a.dry_run:
        print(f"no publication index yet ({idx_p}) — dry run shows the release-tree copy only; "
              "the entry pages are planned once `index` has run (Phase F2)", flush=True)
        idx = {"reports": []}
    else:
        raise SystemExit(f"no publication index for {a.release}: run `prod.publish index` first (Phase F2)")
    L = Ledger(ev / "ledger.sqlite")
    azcopy_login(a)
    # 1. the immutable release tree into $web (server-side copy; nothing reachable yet)
    sh(["azcopy", "copy", blob_url(a.account, "staging", f"{a.release}/r/{a.release}"), blob_url(a.account, "$web", "r"),
        "--recursive", "--overwrite=ifSourceNewer"], a.dry_run)
    for f in ("404.html", "robots.txt", "health.txt"):
        sh(["azcopy", "copy", blob_url(a.account, "staging", f"{a.release}/{f}"), blob_url(a.account, "$web", f), "--overwrite=true"], a.dry_run)
    # 2. activation: one small PUT per approved report
    for r in idx["reports"]:
        src = blob_url(a.account, "staging", f"{a.release}/2026/{r['token']}/index.html")
        dst = blob_url(a.account, "$web", f"2026/{r['token']}/index.html")
        sh(["azcopy", "copy", src, dst, "--overwrite=true", "--cache-control", "no-cache, must-revalidate",
            "--content-type", "text/html; charset=utf-8"], a.dry_run)
        if not a.dry_run:
            L.mark(a.release, r["school_id"], "published")
    # 3. purge the edge so no reader keeps a previous entry page
    sh(["az", "afd", "endpoint", "purge", "--profile-name", a.profile, "--resource-group", a.rg, "--endpoint-name", a.endpoint,
        "--content-paths", "/2026/*", "/404.html", "/robots.txt"], a.dry_run)
    if not a.dry_run:
        L.event(a.release, None, "publication.activated", f"{len(idx['reports'])} reports, index sha256 {idx.get('sha256', '')[:16]}")
    print(f"activated {len(idx['reports'])} reports for {a.release}")


def withdraw(a):
    ev = Path(a.evidence) / a.release
    L = Ledger(ev / "ledger.sqlite")
    att = L.attestation(a.release, a.school)
    if not att:
        raise SystemExit("no attestation for that school")
    tok = att["token"]
    azcopy_login(a)
    sh(["azcopy", "remove", blob_url(a.account, "$web", f"2026/{tok}/index.html")], a.dry_run)
    sh(["azcopy", "remove", blob_url(a.account, "$web", f"r/{a.release}/{tok}"), "--recursive"], a.dry_run)
    sh(["az", "afd", "endpoint", "purge", "--profile-name", a.profile, "--resource-group", a.rg, "--endpoint-name", a.endpoint,
        "--content-paths", f"/2026/{tok}/*", f"/r/{a.release}/{tok}/*"], a.dry_run)
    if not a.dry_run:
        L.mark(a.release, a.school, "withdrawn", error=a.reason)
        L.event(a.release, a.school, "publication.withdrawn", a.reason)
    print(f"withdrawn {att['slug']} ({a.reason})")


def rollback(a):
    """Rewrite every entry page from the previous release's publication index."""
    prev = Path(a.evidence) / a.to / "publication_index.json"
    if not prev.exists():
        raise SystemExit(f"no publication index for {a.to}")
    idx = json.loads(prev.read_text(encoding="utf-8"))
    cur_p = Path(a.evidence) / a.release / "publication_index.json"
    cur = json.loads(cur_p.read_text(encoding="utf-8")) if cur_p.exists() else {"reports": []}
    prev_tokens = {r["token"] for r in idx["reports"]}
    azcopy_login(a)
    # entry pages that exist only in the current release come down (no previous page to restore)
    L = Ledger(Path(a.evidence) / a.release / "ledger.sqlite")
    for r in cur["reports"]:
        if r["token"] not in prev_tokens:
            sh(["azcopy", "remove", blob_url(a.account, "$web", f"2026/{r['token']}/index.html")], a.dry_run, check=False)
            if not a.dry_run:
                L.mark(a.release, r["school_id"], "withdrawn", error=f"rolled back to {a.to}")
    for r in idx["reports"]:
        sh(["azcopy", "copy", blob_url(a.account, "staging", f"{a.to}/2026/{r['token']}/index.html"),
            blob_url(a.account, "$web", f"2026/{r['token']}/index.html"), "--overwrite=true",
            "--cache-control", "no-cache, must-revalidate", "--content-type", "text/html; charset=utf-8"], a.dry_run)
    sh(["az", "afd", "endpoint", "purge", "--profile-name", a.profile, "--resource-group", a.rg, "--endpoint-name", a.endpoint,
        "--content-paths", "/2026/*"], a.dry_run)
    if not a.dry_run:
        for r in cur["reports"]:
            if r["token"] in prev_tokens:
                L.mark(a.release, r["school_id"], "withdrawn", error=f"rolled back to {a.to}")
        L.event(a.release, None, "publication.rolledback", f"to {a.to}: {len(idx['reports'])} entry pages")
    print(f"rolled back to {a.to}: {len(idx['reports'])} entry pages")


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    def common(p, *need):
        p.add_argument("--release", required=True); p.add_argument("--dry-run", action="store_true")
        p.add_argument("--auth", choices=["identity", "azcli"], default="identity",
                       help="AzCopy identity: the VM's managed identity (default) or the Azure CLI's signed-in account (the publisher)")
        for n in need:
            p.add_argument("--" + n, required=True)
    p = sub.add_parser("stage"); common(p, "out", "account"); p.add_argument("--evidence"); p.set_defaults(func=stage)
    p = sub.add_parser("verify-staging"); common(p, "evidence", "account"); p.set_defaults(func=verify_staging)
    p = sub.add_parser("index"); common(p, "evidence", "approver", "approver2"); p.add_argument("--waiver"); p.set_defaults(func=index)
    p = sub.add_parser("promote"); common(p, "evidence", "account", "profile", "rg", "endpoint"); p.set_defaults(func=promote)
    p = sub.add_parser("withdraw"); common(p, "evidence", "account", "profile", "rg", "endpoint", "school", "reason"); p.set_defaults(func=withdraw)
    p = sub.add_parser("rollback"); common(p, "evidence", "account", "profile", "rg", "endpoint", "to"); p.set_defaults(func=rollback)
    a = ap.parse_args(argv)
    a.func(a)


if __name__ == "__main__":
    main()
