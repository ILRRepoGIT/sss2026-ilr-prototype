# -*- coding: utf-8 -*-
"""Reduced 8-state payload + stamped template for the jsdom runs.

    python -m tests.jsdom.make_mini <wd>     (REPO = this checkout)

Then: JSDOM=<path to node_modules/jsdom> WD=<wd> node tests/jsdom/jsdom_test.js
      JSDOM=… WD=<wd> node tests/jsdom/jsdom_provenance.js
"""
import io, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline import static_lane as SL
wd = Path(sys.argv[1]); wd.mkdir(parents=True, exist_ok=True)
# v6 (0.28.0): REPORT names another build's package (a real school); the
# state set adapts to the scopes that package offers
import os
report = os.environ.get("REPORT") or str(ROOT / "generated" / "ysgol-penrhyn-dewi.report.json")
D = json.load(io.open(report, encoding="utf-8"))
offered = [o["key"] for o in D["filterOptions"]["scope"]]
first_year = next(k for k in offered if k.startswith("y"))
keep = {k: D["states"][k] for k in ("whole|all|none", "whole|girl|none", "whole|boy|none")}
extra = ([k for k, v in D["states"].items() if v.get("sup")][:1]
         + [k for k in D["states"] if k.endswith("|sp_football")][:1]
         # V4.18: one setting-selection state (whole|all|st_*) for the frequency-chart rule
         + [k for k in D["states"] if k.startswith("whole|all|st_")][:1]
         + [f"{first_year}|girl|none"]
         + [f"{s}|all|none" for s in ("primary", "secondary") if s in offered])
for k in extra:
    if k in D["states"]: keep[k] = D["states"][k]
mini = {k: v for k, v in D.items() if k != "states"}; mini["states"] = keep
json.dump(mini, io.open(wd / "mini_data.json", "w", encoding="utf-8"), ensure_ascii=False)
tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
(wd / "template_stamped.html").write_text(SL.stamp(tpl, {v["en"]: k for k, v in D["welsh"]["static"].items()}), encoding="utf-8")
print("mini states:", list(keep), "->", wd)
