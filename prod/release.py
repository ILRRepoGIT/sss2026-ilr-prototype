# -*- coding: utf-8 -*-
"""The frozen release (deployment plan §6, rule 1): every file that takes
part in a build, with its sha256, written once at tag time and recomputed
at the start of every production run; any difference refuses the run.

    python -m prod.release build  [--repo .] [--tag v6.0]      # writes prod/release_manifest.json
    python -m prod.release verify [--repo .] [--tag v6.0]      # recomputes and compares; exit 1 on any difference
    python -m prod.release show   [--repo .]

The manifest covers: pipeline/, web/, prod/ (this package), config/ (every
framework workbook, the lexicon, the locks, the yml/json configuration and
the cover media, the school profiles), inputs/fonts, the artwork pack,
build_school.sh, tests/jsdom and tests/browser (the assurance harnesses),
and the pinned requirements. It deliberately excludes generated/, docs/,
the pupil-level inputs (never in the repository) and pycache.

The manifest's own sha256 (`manifestSha256`, over the sorted file table) is
the release identity every attestation and every served envelope binds to.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

INCLUDE_DIRS = ["pipeline", "web", "prod", "config", "inputs/fonts", "inputs/yac images V4.16",
                "tests/jsdom", "tests/browser"]
INCLUDE_FILES = ["build_school.sh", "prod/requirements.lock", "generated/bundle/write_verify.py"]
EXCLUDE_SUFFIX = (".pyc",)
EXCLUDE_PARTS = ("__pycache__", ".pytest_cache")
MANIFEST = "prod/release_manifest.json"


def _sha(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def file_table(repo: Path) -> dict:
    files = {}
    for d in INCLUDE_DIRS:
        base = repo / d
        if not base.exists():
            continue
        for p in sorted(base.rglob("*")):
            if not p.is_file() or p.suffix in EXCLUDE_SUFFIX or any(x in p.parts for x in EXCLUDE_PARTS):
                continue
            rel = p.relative_to(repo).as_posix()
            if rel == MANIFEST:
                continue
            files[rel] = {"sha256": _sha(p), "bytes": p.stat().st_size}
    for f in INCLUDE_FILES:
        p = repo / f
        if p.exists():
            files[p.relative_to(repo).as_posix()] = {"sha256": _sha(p), "bytes": p.stat().st_size}
    return files


def table_hash(files: dict) -> str:
    s = json.dumps({k: v["sha256"] for k, v in sorted(files.items())}, separators=(",", ":"))
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


def git(repo: Path, *args) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else ""


def build(repo: Path, tag: str) -> dict:
    files = file_table(repo)
    from pipeline.build_report_package import PIPELINE_VERSION_V2
    from pipeline.common import latest_framework
    from . import PROD_VERSION, SCHEMA_VERSION
    man = {
        "tag": tag,
        # no commit hash here: the manifest is itself part of the tagged commit,
        # so the identity is the tag (checked against HEAD at run time) and the
        # file table's own hash
        "releasedAt": git(repo, "log", "-1", "--format=%cI") or "",
        "pipelineVersion": PIPELINE_VERSION_V2,
        "prodVersion": PROD_VERSION,
        "servedSchema": SCHEMA_VERSION,
        "framework": latest_framework().name,
        "frameworkSha256": _sha(latest_framework()),
        "gateRunner": "pipeline/vendor_welsh_gates_v8.py",
        "gateRunnerSha256": files["pipeline/vendor_welsh_gates_v8.py"]["sha256"],
        "fileCount": len(files),
        "manifestSha256": table_hash(files),
        "files": files,
    }
    return man


def verify(repo: Path, tag: str | None) -> tuple[bool, list]:
    mp = repo / MANIFEST
    if not mp.exists():
        return False, [f"{MANIFEST} is missing — this is not a tagged release"]
    man = json.loads(mp.read_text(encoding="utf-8"))
    problems = []
    if tag and man.get("tag") != tag:
        problems.append(f"manifest tag {man.get('tag')} != requested {tag}")
    now = file_table(repo)
    for rel, v in man["files"].items():
        if rel not in now:
            problems.append(f"missing: {rel}")
        elif now[rel]["sha256"] != v["sha256"]:
            problems.append(f"changed: {rel}")
    for rel in now:
        if rel not in man["files"]:
            problems.append(f"unlisted file present: {rel}")
    if table_hash(now) != man["manifestSha256"]:
        problems.append("manifestSha256 differs")
    dirty = git(repo, "status", "--porcelain")
    if dirty:
        problems.append("working copy has uncommitted changes:\n    " + "\n    ".join(dirty.splitlines()[:10]))
    if tag:
        tags_here = git(repo, "tag", "--points-at", "HEAD").split()
        if tags_here and tag not in tags_here:
            problems.append(f"HEAD is tagged {tags_here}, not {tag}")
        elif not tags_here:
            problems.append(f"HEAD carries no tag (expected {tag}) — a production build runs only from the tagged commit")
    return (not problems), problems


def load(repo: Path) -> dict:
    return json.loads((repo / MANIFEST).read_text(encoding="utf-8"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["build", "verify", "show"])
    ap.add_argument("--repo", default=".")
    ap.add_argument("--tag", default=None)
    a = ap.parse_args(argv)
    repo = Path(a.repo).resolve()
    sys.path.insert(0, str(repo))
    if a.cmd == "build":
        man = build(repo, a.tag or git(repo, "describe", "--tags", "--always"))
        (repo / MANIFEST).write_text(json.dumps(man, indent=1), encoding="utf-8")
        print(f"{MANIFEST}: {man['fileCount']} files, manifestSha256 {man['manifestSha256'][:16]}…, tag {man['tag']}")
    elif a.cmd == "verify":
        ok, problems = verify(repo, a.tag)
        if ok:
            man = load(repo)
            print(f"release manifest verified: tag {man['tag']}, {man['fileCount']} files, "
                  f"manifestSha256 {man['manifestSha256'][:16]}…, framework {man['framework']}")
        else:
            print("release manifest NOT verified:\n  " + "\n  ".join(problems))
            sys.exit(1)
    else:
        man = load(repo)
        print(json.dumps({k: v for k, v in man.items() if k != "files"}, indent=1))


if __name__ == "__main__":
    main()
