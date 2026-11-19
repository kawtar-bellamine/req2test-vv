"""Evaluation: quality gate against the reviewer's labels, coverage, and mutation scores of the generated
test suite against a naive suite (one nominal test per requirement)."""
from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from .bench import MUTANTS, random_mutants, run, score_on
from .generate import generate
from .graph import export, run_workflow
from .parse import analyse, load_dictionary, load_requirements

ROOT = Path(__file__).resolve().parents[1]


def main():
    reqs = load_requirements(); D = load_dictionary()
    parsed = [analyse(r, D) for r in reqs]
    lab = {r["id"]: bool(r.get("ambiguous")) for r in reqs}
    flagged = {p.id: not p.testable for p in parsed}
    tp = sum(lab[i] and flagged[i] for i in lab); fp = sum(flagged[i] and not lab[i] for i in lab)
    fn = sum(lab[i] and not flagged[i] for i in lab)
    issue_hits = Counter(); issue_total = Counter()
    for r, p in zip(reqs, parsed):
        for i in r.get("issues", []):
            issue_total[i] += 1; issue_hits[i] += i in p.issues
    res = dict(requirements=len(reqs), labelled_ambiguous=sum(lab.values()),
               quality_gate=dict(precision=tp / max(tp + fp, 1), recall=tp / max(tp + fn, 1), tp=tp, fp=fp, fn=fn,
                                 issue_type_recall={k: f"{issue_hits[k]}/{v}" for k, v in issue_total.items()}))
    full, naive = generate(parsed), generate(parsed, naive=True)
    testable = [p for p in parsed if p.testable]
    res["coverage"] = dict(testable=len(testable), with_tests=len({t["requirement"] for t in full}),
                           tests=len(full), naive_tests=len(naive),
                           by_technique=dict(Counter(t["technique"] for t in full)),
                           fail_on_reference=sum(not run(t).passed for t in full))
    R = random_mutants(200)
    res["mutation"] = {
        "designed_mutants": dict(naive=score_on(naive, MUTANTS), generated=score_on(full, MUTANTS)),
        "random_mutants": dict(naive=score_on(naive, R), generated=score_on(full, R)),
    }
    # contribution of each technique: random-mutant score of the suite without that technique
    contrib = {}
    for tech in sorted({t["technique"] for t in full}):
        contrib[f"without_{tech}"] = round(score_on([t for t in full if t["technique"] != tech], R)["score"], 3)
    res["mutation"]["random_by_technique"] = contrib
    kinds = Counter(n.split("=")[0].replace("R ", "") for n in res["mutation"]["random_mutants"]["naive"]["survivors"])
    res["mutation"]["naive_survivors_by_parameter"] = dict(kinds.most_common())
    state = run_workflow(review={t["id"]: "approved" for t in full})
    export(state, ROOT / "results/export")
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/metrics.json").write_text(json.dumps(res, indent=1, ensure_ascii=False))
    print(json.dumps({k: v for k, v in res.items() if k != "mutation"}, indent=1, ensure_ascii=False))
    m = res["mutation"]
    print({k: (m[k]["naive"]["killed"], m[k]["generated"]["killed"], m[k]["naive"]["total"])
           for k in ("designed_mutants", "random_mutants")}, m["random_by_technique"],
          m["naive_survivors_by_parameter"])


if __name__ == "__main__":
    main()
