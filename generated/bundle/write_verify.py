#!/usr/bin/env python3
"""Write verify.json from the clean rerun's results (D81, sheet 52).

    python write_verify.py <report.html> results_release.json [results_dev.json]

Gate pack v7 as shipped does not write verify.json itself (raised with the
pack owners, V4.9 register); this script states the rerun's result next to
the report's sha256 and nothing else — it computes no gate.
"""
import hashlib, json, sys, datetime
rep, rel = sys.argv[1], json.load(open(sys.argv[2], encoding="utf-8"))
dev = json.load(open(sys.argv[3], encoding="utf-8")) if len(sys.argv) > 3 else None
fails = lambda j: [{"gate": g["id"], "occurrences": g["occurrences"]} for g in j["gates"] if g["status"] == "FAIL"]
out = {"report": rep.split("/")[-1], "reportSha256": hashlib.sha256(open(rep, "rb").read()).hexdigest(),
       "headline": f'{rel["summary"]["blocking_pass"]}/{rel["summary"]["blocking_total"]}', "mode": rel["summary"]["mode"],
       "runner": rel["summary"]["runner"], "manifestHash": rel["summary"]["manifest_hash"],
       "paths": f'{rel["summary"]["paths"]["complete"]}/{rel["summary"]["paths"]["total"]}',
       "failing": fails(rel), "notes": rel["summary"].get("notes", []),
       "at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")}
if dev:
    out["dev"] = {"headline": f'{dev["summary"]["blocking_pass"]}/{dev["summary"]["blocking_total"]}',
                  "paths": f'{dev["summary"]["paths"]["complete"]}/{dev["summary"]["paths"]["total"]}', "failing": fails(dev)}
json.dump(out, open("verify.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
print(json.dumps(out, indent=1, ensure_ascii=False))
