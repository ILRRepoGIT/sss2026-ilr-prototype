# -*- coding: utf-8 -*-
"""Collect one real-school build's assurance figures into one JSON + a
markdown table row (V5.0 round). Read-only.

    python tools/school_round_summary.py <work_root> <slug> [<slug> ...]
"""
import hashlib, json, sys
from pathlib import Path


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(root, slug):
    g = root / slug / "generated"; wd = root / slug / "wd"
    pk = json.load(open(g / f"{slug}.report.json", encoding="utf-8"))
    bm = pk["buildMetadata"]; gr = bm["gateResults"]
    bs = json.load(open(g / "bundle_summary.json", encoding="utf-8"))
    vf = json.load(open(root / slug / "verify_figures.json", encoding="utf-8"))
    js = json.load(open(wd / "jsdom_school.json", encoding="utf-8"))
    pv = json.load(open(wd / "browser_gate_jsdom.json", encoding="utf-8"))["summary"]
    pr = json.load(open(root / slug / "probe" / "probe.json", encoding="utf-8"))
    vs = (g / "validation-summary.txt").read_text(encoding="utf-8")
    holds = [l.strip()[2:] for l in vs.splitlines() if "HELD" in l]
    states = pk["states"]
    out = {
        "slug": slug, "school": pk["school"], "reportVersion": pk["reportVersion"],
        "pipeline": bm["pipelineVersion"], "identity": bm["identity"],
        "sourceRows": bm["sourceRows"], "acceptedRows": bm["acceptedRows"], "excludedRows": bm["excludedRows"],
        "acceptedByStatus": bm.get("acceptedByStatus"), "sourceChecksum": bm["sourceChecksum"],
        "anyActivity": pk["anyActivity"], "sportOptionCount": bm["sportOptionCount"],
        "states": len(states), "visible": sum(1 for s in states.values() if not s.get("sup")),
        "paragraphs": bm["surfaceCounts"]["module"], "cohorts": len(pk["cohorts"]),
        "stamp": gr["headline"], "paths": f'{gr["pathsComplete"]}/{gr["pathsTotal"]}',
        "disputed": list((gr.get("disputed") or {}).keys()),
        "rerun_dev": bs["dev"]["headline"], "rerun_release": bs["release"]["headline"], "rerun_paths": bs["dev"]["paths"],
        "rerun_failing_release": bs["release"]["failing"],
        "emittedEqualsBaseline": bs["emittedEqualsBaseline"],
        "report": bs["report"], "reportSha256": bs["reportSha256"], "reportBytes": bs["reportBytes"],
        "lock": bs["baseline"], "lockSha256": bs["baselineSha256"],
        "figuresVerified": vf["allMatch"],
        "jsdom": f'{js["pass"]}/{js["pass"] + js["fail"]}',
        "provenance": f'{pv["english_without_provenance"]} / {pv["welsh_without_provenance"]} / {pv["typography_faults"]}',
        "toggle": f'{pv["toggle"]["failures"]} failures over {pv["toggle"]["en_ok"]}',
        "pdfPages": {k: v["pdfPages"] for k, v in pr.items()},
        "holds": holds,
    }
    return out


def main():
    root = Path(sys.argv[1]); slugs = sys.argv[2:]
    rows = [one(root, s) for s in slugs]
    json.dump(rows, open(root / "school_round_summary.json", "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    hdr = ["School", "Type / years", "Responses (accepted)", "States (visible)", "Paragraphs", "QA stamp", "Reruns dev · release · paths",
           "Lock = baseline", "Figures verified", "jsdom", "Provenance EN/CY/typo", "A4 pages EN/CY", "Report (bytes, sha256)"]
    lines = ["| " + " | ".join(hdr) + " |", "|" + "---|" * len(hdr)]
    for r in rows:
        eq = all(r["emittedEqualsBaseline"].values())
        lines.append("| " + " | ".join([
            f'{r["school"]["name"]} ({r["school"]["localAuthority"]})',
            f'{r["school"]["type"]}, Years {r["school"]["years"][0]}–{r["school"]["years"][-1]}',
            f'{r["acceptedRows"]} of {r["sourceRows"]}' + (f' ({r["acceptedByStatus"]["Complete"]} complete, {r["acceptedByStatus"].get("Partial", 0)} partial)' if r["acceptedByStatus"] else ""),
            f'{r["states"]} ({r["visible"]})', f'{r["paragraphs"]:,}', f'{r["stamp"]}, paths {r["paths"]}',
            f'{r["rerun_dev"]} · {r["rerun_release"]} · {r["rerun_paths"]}', "yes" if eq else "NO",
            "yes" if r["figuresVerified"] else "NO", r["jsdom"], r["provenance"],
            f'{r["pdfPages"]["en"]} / {r["pdfPages"]["cy"]}', f'{r["reportBytes"]:,} · {r["reportSha256"][:16]}…']) + " |")
    (root / "school_round_summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
