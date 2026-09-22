# -*- coding: utf-8 -*-
"""State-by-state proof of what moved between two report packages (and, when
given, between the two corpus locks emitted from them).

    python -m tools.state_diff <old.report.json|.pkl> <new.report.json|.pkl> <out.json>
                               [--old-lock <old_lock.json> --new-lock <new_lock.json>]
                               [--label-old "V5.1 …"] [--label-new "V5.2 …"] [--ruling "…"]

Every state record is compared field by field. Module narratives are
classified per module: "removed", "added", "prepended:<n>" (the old
paragraphs follow n new ones, byte-identical), "appended:<n>", or "changed"
(anything else). Everything outside `mod` that differs is listed under
otherFieldDiffs; every other top-level package part is compared whole.
Nothing here decides anything — it states the difference so the ruling that
moved the lock can be checked against it.
"""
from __future__ import annotations

import argparse
import collections
import json
import pickle
from pathlib import Path


def load_package(path: str):
    p = Path(path)
    if p.suffix == ".pkl":
        obj = pickle.load(open(p, "rb"))
        return obj["package"] if isinstance(obj, dict) and "package" in obj else obj
    return json.loads(p.read_text(encoding="utf-8"))


def paras(m):
    if isinstance(m, list):
        return m, {}
    if isinstance(m, dict):
        return m.get("p") or [], {k: v for k, v in m.items() if k != "p"}
    return None, {}


def classify_module(old, new):
    if old is None:
        return "added"
    if new is None:
        return "removed"
    if old == new:
        return "same"
    po, mo = paras(old)
    pn, mn = paras(new)
    if po is not None and pn is not None and mo == mn:
        if len(pn) > len(po) and pn[len(pn) - len(po):] == po:
            return f"prepended:{len(pn) - len(po)}"
        if len(pn) > len(po) and pn[:len(po)] == po:
            return f"appended:{len(pn) - len(po)}"
    return "changed"


def diff_states(a, b):
    sa, sb = a["states"], b["states"]
    ka, kb = set(sa), set(sb)
    removed, added = sorted(ka - kb), sorted(kb - ka)
    per_module = collections.defaultdict(collections.Counter)      # module -> class -> count
    per_module_cohort = collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
    changed_examples = collections.defaultdict(list)
    other = []
    identical = 0
    for k in sorted(ka & kb):
        x, y = sa[k], sb[k]
        if x == y:
            identical += 1
            continue
        for f in sorted(set(x) | set(y)):
            if f == "mod":
                mx, my = x.get("mod") or {}, y.get("mod") or {}
                for m in sorted(set(mx) | set(my)):
                    c = classify_module(mx.get(m), my.get(m))
                    if c == "same":
                        continue
                    per_module[m][c] += 1
                    per_module_cohort[m][c][k.split("|")[2]] += 1
                    if c == "changed" and len(changed_examples[m]) < 5:
                        changed_examples[m].append(k)
            elif x.get(f) != y.get(f):
                other.append([k, f])
    return {
        "oldStates": len(sa), "newStates": len(sb),
        "removedStates": len(removed), "removedStateKeys": removed,
        "removedCohorts": sorted({k.split("|")[2] for k in removed}),
        "addedStates": len(added), "addedStateKeys": added,
        "commonStatesIdentical": identical,
        "moduleChanges": {m: dict(c) for m, c in per_module.items()},
        "moduleChangesByCohort": {m: {c: dict(coh) for c, coh in cc.items()} for m, cc in per_module_cohort.items()},
        "changedModuleExamples": dict(changed_examples),
        "otherFieldDiffs": other,
    }


def diff_parts(a, b):
    out = {}
    for part in sorted(set(a) | set(b)):
        if part == "states":
            continue
        va, vb = a.get(part), b.get(part)
        if va == vb:
            out[part] = "equal"
        elif isinstance(va, dict) and isinstance(vb, dict):
            sub = {}
            for k in sorted(set(va) | set(vb)):
                if va.get(k) == vb.get(k):
                    continue
                xa, xb = va.get(k), vb.get(k)
                if isinstance(xa, dict) and isinstance(xb, dict):
                    sub[k] = {"removed": sorted(set(xa) - set(xb)), "added": sorted(set(xb) - set(xa)),
                              "changed": sorted(q for q in set(xa) & set(xb) if xa[q] != xb[q])}
                elif isinstance(xa, list) and isinstance(xb, list):
                    ja = [json.dumps(e, sort_keys=True, ensure_ascii=False) for e in xa]
                    jb = [json.dumps(e, sort_keys=True, ensure_ascii=False) for e in xb]
                    sub[k] = {"removed": len(set(ja) - set(jb)), "added": len(set(jb) - set(ja)), "oldLen": len(xa), "newLen": len(xb)}
                else:
                    sub[k] = {"old": xa, "new": xb} if len(json.dumps([xa, xb])) < 400 else "changed"
            out[part] = sub
        else:
            out[part] = "changed"
    return out


def diff_locks(old_path, new_path):
    lo = json.loads(Path(old_path).read_text(encoding="utf-8"))
    ln = json.loads(Path(new_path).read_text(encoding="utf-8"))
    out = {}
    for part in ("english", "welsh"):
        a, b = lo.get(part) or {}, ln.get(part) or {}
        moved = sorted(k for k in set(a) & set(b) if a[k] != b[k])
        out[part] = {"oldStates": len(a), "newStates": len(b),
                     "removed": sorted(set(a) - set(b)), "added": sorted(set(b) - set(a)),
                     "moved": len(moved), "movedByCohortPrefix": dict(collections.Counter(
                         k.split("|")[2].split("_")[0] if k.count("|") >= 2 else k for k in moved)),
                     "movedKeys": moved}
    fa, fb = set(lo.get("ft11") or []), set(ln.get("ft11") or [])
    out["ft11"] = {"old": len(fa), "new": len(fb), "removed": sorted(fa - fb), "added": sorted(fb - fa)}
    out["newLockEmitted"] = ln.get("emitted")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("old"); ap.add_argument("new"); ap.add_argument("out")
    ap.add_argument("--old-lock"); ap.add_argument("--new-lock")
    ap.add_argument("--label-old", default=""); ap.add_argument("--label-new", default="")
    ap.add_argument("--ruling", default="")
    args = ap.parse_args()
    a, b = load_package(args.old), load_package(args.new)
    res = {"from": args.label_old or args.old, "to": args.label_new or args.new, "ruling": args.ruling,
           "oldIdentity": {k: a.get(k) for k in ("reportVersion",)}, "newIdentity": {k: b.get(k) for k in ("reportVersion",)},
           "states": diff_states(a, b), "parts": diff_parts(a, b)}
    if args.old_lock and args.new_lock:
        res["locks"] = diff_locks(args.old_lock, args.new_lock)
    Path(args.out).write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding="utf-8")
    s = res["states"]
    print(f"states {s['oldStates']} -> {s['newStates']}: removed {s['removedStates']} {s['removedCohorts']}, added {s['addedStates']}, "
          f"identical {s['commonStatesIdentical']}; module changes {s['moduleChanges']}; other field diffs {len(s['otherFieldDiffs'])}")
    if "locks" in res:
        L = res["locks"]
        print(f"lock english: {L['english']['oldStates']} -> {L['english']['newStates']}, removed {len(L['english']['removed'])}, "
              f"moved {L['english']['moved']} {L['english']['movedByCohortPrefix']}; ft11 {L['ft11']['old']} -> {L['ft11']['new']} "
              f"(-{len(L['ft11']['removed'])}, +{len(L['ft11']['added'])})")


if __name__ == "__main__":
    main()
