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
D = json.load(io.open(ROOT / "generated" / "ysgol-penrhyn-dewi.report.json", encoding="utf-8"))
keep = {k: D["states"][k] for k in ("whole|all|none", "primary|all|none", "whole|girl|none", "whole|boy|none")}
extra = ([k for k, v in D["states"].items() if v.get("sup")][:1]
         + [k for k in D["states"] if k.endswith("|sp_football")][:1] + ["y5|girl|none", "secondary|all|none"])
for k in extra:
    if k in D["states"]: keep[k] = D["states"][k]
mini = {k: v for k, v in D.items() if k != "states"}; mini["states"] = keep
json.dump(mini, io.open(wd / "mini_data.json", "w", encoding="utf-8"), ensure_ascii=False)
tpl = (ROOT / "web" / "template.html").read_text(encoding="utf-8")
(wd / "template_stamped.html").write_text(SL.stamp(tpl, {v["en"]: k for k, v in D["welsh"]["static"].items()}), encoding="utf-8")
print("mini states:", list(keep), "->", wd)
