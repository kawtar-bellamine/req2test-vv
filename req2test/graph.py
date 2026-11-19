"""The V&V assistant as a LangGraph workflow.

parse -> quality gate -> generate -> verify on the reference model -> human review -> export

Requirements that fail the quality gate are not guessed: they go back to the author with the reason and a
suggested rewrite. Generated tests that fail on the reference model are discarded before review (a test that
fails on a correct implementation is a wrong test). The engineer approves or rejects each remaining test; only
approved tests are exported to the traceability matrix and the Gherkin files.
"""
from __future__ import annotations

import csv
import json
import os
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, StateGraph

from .bench import run
from .generate import generate, gherkin
from .parse import analyse, load_dictionary, load_requirements

SUGGEST = {
    "weak_word": "replace the vague word by a measurable value, for example 'within 200 ms'",
    "no_timing": "add the response deadline, for example 'within 500 ms'",
    "should": "use 'shall' for a mandatory requirement",
    "and_or": "split into two requirements or choose 'and' or 'or'",
    "open_list": "list every case explicitly, remove 'etc.'",
    "vague_quantifier": "name the items, for example the fault codes E01 to E40",
    "escape_clause": "state the exact condition instead of 'if necessary' or 'unless'",
    "passive_no_actor": "name the actor: 'the controller shall ...'",
    "vague_condition": "give the signal and its threshold, for example 'system pressure exceeds 240 bar'",
    "missing_unit": "add the unit of the value",
    "not_ears": "rewrite with an EARS pattern: 'When <trigger>, the controller shall <response>.'",
    "trigger_not_in_dictionary": "use a signal of the interface dictionary, or add the signal to it",
    "response_not_in_dictionary": "use an output of the interface dictionary, or add the output to it",
}


class State(TypedDict, total=False):
    requirements: list
    parsed: list
    rework: list
    tests: list
    discarded: list
    review: dict


def node_parse(s: State) -> State:
    D = load_dictionary()
    return {"parsed": [analyse(r, D) for r in s["requirements"]]}


def node_quality(s: State) -> State:
    rework = []
    for p in s["parsed"]:
        if not p.testable:
            rework.append(dict(id=p.id, text=p.text, issues=p.issues,
                               suggestions=[SUGGEST[i] for i in p.issues if i in SUGGEST],
                               llm_rewrite=llm_rewrite(p.text, p.issues)))
    return {"rework": rework}


def node_generate(s: State) -> State:
    return {"tests": generate(s["parsed"])}


def node_verify(s: State) -> State:
    keep, drop = [], []
    for t in s["tests"]:
        (keep if run(t).passed else drop).append(t)
    return {"tests": keep, "discarded": drop}


def node_review(s: State) -> State:
    """Apply the engineer's decisions saved by the review interface; tests without a decision stay proposed."""
    review = s.get("review") or {}
    for t in s["tests"]:
        t["status"] = review.get(t["id"], "proposed")
    return {}


def build_graph():
    g = StateGraph(State)
    for name, fn in [("parse", node_parse), ("quality", node_quality), ("generate", node_generate),
                     ("verify", node_verify), ("review", node_review)]:
        g.add_node(name, fn)
    g.set_entry_point("parse")
    g.add_edge("parse", "quality"); g.add_edge("quality", "generate"); g.add_edge("generate", "verify")
    g.add_edge("verify", "review"); g.add_edge("review", END)
    return g.compile()


def run_workflow(review: dict | None = None, requirements: list | None = None) -> State:
    return build_graph().invoke({"requirements": requirements or load_requirements(), "review": review or {}})


def llm_rewrite(text: str, issues: list[str]) -> str | None:
    """Optional: ask an OpenAI-compatible model (Azure OpenAI or other) for a testable rewrite. The suggestion is
    shown to the author, never applied automatically."""
    base, key, model = os.getenv("LLM_BASE_URL"), os.getenv("LLM_API_KEY"), os.getenv("LLM_MODEL")
    if not (base and key and model):
        return None
    import urllib.request
    prompt = (f"Rewrite this software requirement with the EARS pattern so that it is testable. Problems found: "
              f"{', '.join(issues)}. Do not invent values: write <value> where a number is missing.\n\n{text}")
    body = {"model": model, "temperature": 0, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(base.rstrip("/") + "/chat/completions", data=json.dumps(body).encode(),
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.loads(r.read())["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001
        return None


def export(state: State, out: Path, only_approved: bool = True):
    out.mkdir(parents=True, exist_ok=True)
    tests = [t for t in state["tests"] if t["status"] == "approved" or not only_approved]
    reqs = [p for p in state["parsed"]]
    with open(out / "traceability_matrix.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["requirement", "testable", "issues", "tests", "techniques"])
        for p in reqs:
            ts = [t for t in tests if t["requirement"] == p.id]
            w.writerow([p.id, p.testable, ";".join(p.issues), ";".join(t["id"] for t in ts),
                        ";".join(sorted({t["technique"] for t in ts}))])
    by_req: dict[str, list] = {}
    for t in tests:
        by_req.setdefault(t["requirement"], []).append(t)
    feat = ["Feature: HPU-200 unit controller, generated test specifications", ""]
    for rid, ts in by_req.items():
        feat.append(f"  # ---- {rid}")
        feat += [gherkin(t) + "\n" for t in ts]
    (out / "hpu200_controller.feature").write_text("\n".join(feat))
    (out / "tests.json").write_text(json.dumps(tests, indent=1, ensure_ascii=False))
    (out / "rework.json").write_text(json.dumps(state["rework"], indent=1, ensure_ascii=False))
