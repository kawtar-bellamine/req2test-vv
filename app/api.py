"""FastAPI service for the review: requirements with their quality issues, generated tests, approve/reject,
mutation score of the approved suite, traceability matrix."""
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from req2test.bench import MUTANTS, score_on
from req2test.generate import gherkin
from req2test.graph import export, run_workflow

ROOT = Path(__file__).resolve().parents[1]
REVIEW = ROOT / "data" / "review.json"
app = FastAPI(title="Requirements to test specifications")


def _review() -> dict:
    return json.loads(REVIEW.read_text()) if REVIEW.exists() else {}


def _state():
    return run_workflow(review=_review())


@app.get("/api/requirements")
def requirements():
    s = _state()
    rework = {r["id"]: r for r in s["rework"]}
    out = []
    for p in s["parsed"]:
        ts = [t for t in s["tests"] if t["requirement"] == p.id]
        out.append(dict(id=p.id, text=p.text, testable=p.testable, issues=p.issues,
                        suggestions=rework.get(p.id, {}).get("suggestions", []),
                        tests=[dict(t, gherkin=gherkin(t)) for t in ts]))
    return out


class Decision(BaseModel):
    id: str
    status: str   # approved | rejected | proposed


@app.post("/api/review")
def review(d: Decision):
    r = _review(); r[d.id] = d.status
    REVIEW.write_text(json.dumps(r, indent=1))
    return {"ok": True}


@app.get("/api/summary")
def summary():
    s = _state()
    approved = [t for t in s["tests"] if t["status"] == "approved"]
    ms = score_on(approved, MUTANTS) if approved else dict(score=0, killed=0, total=len(MUTANTS))
    return dict(requirements=len(s["parsed"]), testable=sum(p.testable for p in s["parsed"]),
                rework=len(s["rework"]), tests=len(s["tests"]), approved=len(approved),
                rejected=sum(t["status"] == "rejected" for t in s["tests"]),
                mutation=dict(score=ms["score"], killed=ms["killed"], total=ms["total"]))


@app.get("/api/matrix", response_class=PlainTextResponse)
def matrix():
    out = ROOT / "results" / "export_review"
    export(_state(), out)
    return (out / "traceability_matrix.csv").read_text()


dist = ROOT / "web" / "dist"
if dist.exists():
    app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/")
    def index():
        return FileResponse(dist / "index.html")
