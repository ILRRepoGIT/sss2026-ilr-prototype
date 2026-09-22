# -*- coding: utf-8 -*-
"""The served package: split one school's monolithic report package into a
small core payload plus state chunks, with an identity envelope on every
file, and prove that the chunks reconstruct exactly the states the gates
examined (production deployment plan §2 and Phase 2; review P0.4, P0.7).

    python -m prod.chunker split  <slug.report.json> <out_dir> --release <tag> --recipient <school id> \\
                                  --family school --binding <hash> [--cap-bytes 6291456]
    python -m prod.chunker verify <slug.report.json> <out_dir>

`split` writes into <out_dir>:
    s-<sha256[:16]>.json     one file per (scope|gender) group — or several
                             parts when a group exceeds the size cap —
                             each {"env": {...}, "group": "scope|gender",
                             "part": i, "states": {key: state, ...}}
    package_index.json       PRIVATE build artefact (goes to the attestation,
                             never served): the chunk map, every chunk's
                             sha256/bytes/keys, every state's canonical
                             sha256, and the core payload's sha256
and returns the core payload (the package without its states, plus the
first state inlined, the chunk map and the envelope) for prod.htmlcore.

`verify` re-reads the chunks from disk, reconstructs the state set, and
compares it key by key and byte by byte (canonical JSON) with the monolith:
identical keys, identical states, every chunk's sha256 equal to its name
and to the index, every envelope equal, no key outside its group.

Nothing here changes a state. The grouping is by the state key's scope and
gender, in the monolith's own key order, so the output is deterministic.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from . import SCHEMA_VERSION

FIRST_STATE = "whole|all|none"
INLINE_STATES = ["whole|all|none", "whole|boy|none", "whole|girl|none"]   # the default view reads these
DEFAULT_CAP = 6 * 1024 * 1024          # raw bytes per chunk file (Front Door compresses < 8 MB)
SEP = (",", ":")


def canon(obj) -> bytes:
    """Canonical JSON bytes of a state (sorted keys, no spaces, UTF-8)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=SEP).encode("utf-8")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def envelope(family: str, recipient: str, release: str, binding: str) -> dict:
    return {"family": family, "recipient": str(recipient), "release": release,
            "schema": SCHEMA_VERSION, "binding": binding}


def _dump(obj) -> bytes:
    # chunk files keep the monolith's key ORDER (not sorted) so that a
    # chunk is the exact slice of the package; states inside are copied as-is
    return json.dumps(obj, ensure_ascii=False, separators=SEP).encode("utf-8")


def group_of(key: str) -> str:
    scope, gender, _ = key.split("|")
    return scope + "|" + gender


def split(package: dict, out_dir: Path, env: dict, cap_bytes: int = DEFAULT_CAP) -> tuple[dict, dict]:
    """Write the chunks; return (core_payload, package_index)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    states = package["states"]
    if FIRST_STATE not in states:
        raise SystemExit(f"package has no {FIRST_STATE} state")
    # group in key order
    groups: dict[str, list[str]] = {}
    for k in states:
        groups.setdefault(group_of(k), []).append(k)

    chunk_map: dict[str, dict] = {}
    index_chunks: list[dict] = []
    state_hashes: dict[str, str] = {}
    for k, st in states.items():
        state_hashes[k] = sha256_bytes(canon(st))

    for g, keys in groups.items():
        # size-capped parts: fill a part until the next state would exceed the cap
        parts: list[list[str]] = [[]]
        size = 0
        for k in keys:
            n = len(_dump({k: states[k]}))
            if parts[-1] and size + n > cap_bytes:
                parts.append([]); size = 0
            parts[-1].append(k); size += n
        files = []
        for i, pk in enumerate(parts):
            body = {"env": env, "group": g, "part": i, "parts": len(parts),
                    "states": {k: states[k] for k in pk}}
            data = _dump(body)
            h = sha256_bytes(data)
            name = f"s-{h[:16]}.json"
            (out_dir / name).write_bytes(data)
            files.append({"path": name, "sha256": h, "bytes": len(data), "n": len(pk)})
            index_chunks.append({"path": name, "sha256": h, "bytes": len(data),
                                 "group": g, "part": i, "keys": pk})
        chunk_map[g] = {"files": [{"path": f["path"], "sha256": f["sha256"], "n": f["n"]} for f in files]}

    core = {k: v for k, v in package.items() if k != "states"}
    core["states"] = {k: states[k] for k in INLINE_STATES if k in states}
    core["chunked"] = {"schema": SCHEMA_VERSION, "map": chunk_map, "envelope": env,
                       "stateCount": len(states), "firstState": FIRST_STATE, "inline": list(core["states"])}
    index = {"schema": SCHEMA_VERSION, "envelope": env, "stateCount": len(states),
             "groups": len(groups), "chunks": index_chunks, "stateSha256": state_hashes,
             "chunkMap": chunk_map, "firstState": FIRST_STATE, "capBytes": cap_bytes,
             "totalChunkBytes": sum(c["bytes"] for c in index_chunks)}
    (out_dir / "package_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=0),
                                                encoding="utf-8")
    return core, index


def verify(package: dict, out_dir: Path, env: dict | None = None) -> dict:
    """Reconstruct the states from the chunk files and compare with the monolith.
    Returns a result dict; raises SystemExit with the differences on failure."""
    index = json.loads((out_dir / "package_index.json").read_text(encoding="utf-8"))
    problems = []
    rebuilt: dict[str, dict] = {}
    seen_env = None
    for c in index["chunks"]:
        p = out_dir / c["path"]
        data = p.read_bytes()
        h = sha256_bytes(data)
        if h != c["sha256"] or not c["path"].startswith("s-" + h[:16]):
            problems.append(f"chunk {c['path']}: sha256 mismatch ({h[:16]})")
            continue
        body = json.loads(data.decode("utf-8"))
        if seen_env is None:
            seen_env = body["env"]
        if body["env"] != seen_env or body["env"] != index["envelope"] or (env and body["env"] != env):
            problems.append(f"chunk {c['path']}: envelope differs")
        if body["group"] != c["group"]:
            problems.append(f"chunk {c['path']}: group {body['group']} != {c['group']}")
        for k, st in body["states"].items():
            if group_of(k) != body["group"]:
                problems.append(f"chunk {c['path']}: state {k} outside group {body['group']}")
            if k in rebuilt:
                problems.append(f"state {k} appears in two chunks")
            rebuilt[k] = st
        if list(body["states"].keys()) != c["keys"]:
            problems.append(f"chunk {c['path']}: key list differs from the index")
    mono = package["states"]
    if set(rebuilt) != set(mono):
        missing = sorted(set(mono) - set(rebuilt))[:5]
        extra = sorted(set(rebuilt) - set(mono))[:5]
        problems.append(f"state set differs: missing {len(set(mono)-set(rebuilt))} (e.g. {missing}), "
                        f"extra {len(set(rebuilt)-set(mono))} (e.g. {extra})")
    moved = 0
    for k, st in mono.items():
        if k in rebuilt:
            h = sha256_bytes(canon(st))
            if h != sha256_bytes(canon(rebuilt[k])) or index["stateSha256"].get(k) != h:
                moved += 1
                if moved <= 5:
                    problems.append(f"state {k}: chunk copy differs from the monolith")
    if moved > 5:
        problems.append(f"… {moved} states differ in total")
    if index["stateCount"] != len(mono):
        problems.append(f"index stateCount {index['stateCount']} != {len(mono)}")
    result = {"states": len(mono), "rebuilt": len(rebuilt), "chunks": len(index["chunks"]),
              "groups": index["groups"], "totalChunkBytes": index["totalChunkBytes"],
              "largestChunkBytes": max(c["bytes"] for c in index["chunks"]),
              "statesMoved": moved, "problems": problems, "ok": not problems}
    if problems:
        raise SystemExit("served-package verification FAILED:\n  " + "\n  ".join(problems))
    return result


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("split"); s.add_argument("report_json"); s.add_argument("out_dir")
    s.add_argument("--release", required=True); s.add_argument("--recipient", required=True)
    s.add_argument("--family", default="school"); s.add_argument("--binding", required=True)
    s.add_argument("--cap-bytes", type=int, default=DEFAULT_CAP)
    v = sub.add_parser("verify"); v.add_argument("report_json"); v.add_argument("out_dir")
    a = ap.parse_args(argv)
    package = json.loads(Path(a.report_json).read_text(encoding="utf-8"))
    if a.cmd == "split":
        env = envelope(a.family, a.recipient, a.release, a.binding)
        core, index = split(package, Path(a.out_dir), env, a.cap_bytes)
        print(json.dumps({"states": index["stateCount"], "groups": index["groups"],
                          "chunks": len(index["chunks"]), "totalChunkBytes": index["totalChunkBytes"],
                          "largestChunkBytes": max(c["bytes"] for c in index["chunks"]),
                          "coreBytes": len(_dump(core))}, indent=1))
    else:
        print(json.dumps(verify(package, Path(a.out_dir)), indent=1))


if __name__ == "__main__":
    main()
