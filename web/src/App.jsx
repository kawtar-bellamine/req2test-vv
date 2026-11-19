import React, { useEffect, useState } from "react";

const TECH_COLORS = { nominal: "#1f5fa8", boundary: "#e69138", timing: "#6aa84f", guard: "#a64d79",
                      state: "#45818e", logging: "#7a7a7a" };

export default function App() {
  const [reqs, setReqs] = useState([]);
  const [sel, setSel] = useState(null);
  const [sum, setSum] = useState(null);

  async function load() {
    const r = await (await fetch("/api/requirements")).json();
    setReqs(r);
    setSum(await (await fetch("/api/summary")).json());
    if (!sel && r.length) setSel(r[3].id);
  }
  useEffect(() => { load(); }, []);

  async function decide(id, status) {
    await fetch("/api/review", { method: "POST", headers: { "Content-Type": "application/json" },
                                 body: JSON.stringify({ id, status }) });
    load();
  }

  const cur = reqs.find((r) => r.id === sel);
  return (
    <div className="page">
      <header>
        <div>
          <div className="brand">Requirements → test specifications</div>
          <div className="sub">HPU-200 unit controller · generated tests checked on the reference model, approved by the engineer</div>
        </div>
        {sum && (
          <div className="kpis">
            <div><b>{sum.testable}/{sum.requirements}</b><span>testable</span></div>
            <div className="warn"><b>{sum.rework}</b><span>back to author</span></div>
            <div><b>{sum.approved}/{sum.tests}</b><span>tests approved</span></div>
            <div className="ok"><b>{Math.round(sum.mutation.score * 100)} %</b><span>bugs caught by approved tests</span></div>
          </div>
        )}
      </header>
      <div className="grid">
        <aside>
          {reqs.map((r) => (
            <button key={r.id} className={"req " + (r.id === sel ? "sel " : "") + (r.testable ? "" : "bad")}
                    onClick={() => setSel(r.id)}>
              <div className="rid">{r.id}
                <span className="badge">{r.testable ? `${r.tests.length} test${r.tests.length > 1 ? "s" : ""}` : "rework"}</span>
              </div>
              <div className="rtext">{r.text}</div>
            </button>
          ))}
        </aside>
        <main>
          {cur && (
            <>
              <h2>{cur.id}</h2>
              <p className="rtextbig">{cur.text}</p>
              {!cur.testable && (
                <div className="rework">
                  <b>Not testable as written</b>
                  <ul>{cur.issues.map((i, k) => <li key={i}><code>{i}</code> {cur.suggestions[k] || ""}</li>)}</ul>
                </div>
              )}
              {cur.tests.map((t) => (
                <div key={t.id} className={"test " + t.status}>
                  <div className="th">
                    <span className="tid">{t.id}</span>
                    <span className="tech" style={{ background: TECH_COLORS[t.technique] }}>{t.technique}</span>
                    <span className="ttitle">{t.title}</span>
                    <span className="actions">
                      <button className="approve" onClick={() => decide(t.id, "approved")}>Approve</button>
                      <button className="reject" onClick={() => decide(t.id, "rejected")}>Reject</button>
                    </span>
                  </div>
                  <pre>{t.gherkin}</pre>
                </div>
              ))}
            </>
          )}
        </main>
      </div>
    </div>
  );
}
