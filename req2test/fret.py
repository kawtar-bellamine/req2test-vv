"""Real requirements: the case studies shipped with NASA's FRET (Formal Requirements Elicitation Tool,
github.com/NASA-SW-VnV/fret), fetched at a pinned commit. Written in FRETish, FRET's structured English:

    [when|whenever|upon|if CONDITION] COMPONENT shall [TIMING] satisfy RESPONSE

This module parses that subset into an expression tree (no eval: a small recursive-descent parser) and gives each
requirement a semantics on finite traces, so a requirement can be checked on the outputs of an implementation.

Semantics used (FRET's, on a finite trace): "when/upon/if" trigger on the rising edge of the condition (or at the
first step if it is already true), "whenever" at every step where it holds; TIMING is immediately (same step),
at the next timepoint, within N ticks (at least once in [t, t+N]), for N ticks (every step of [t, t+N]), always
(every step from t), until Q (every step from t until Q holds), eventually, never. Without a condition, the
requirement is triggered once at the first step, except "always" and "never", which hold at every step.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data/fret"
REPO = "https://github.com/NASA-SW-VnV/fret.git"
COMMIT = "cf0f913cc15c41705e803593297e89cd6056b839"
CASES = {"LiquidMixer": "caseStudies/LiquidMixer/LM_reqts_and_vars.json",
         "FSM": "caseStudies/FiniteStateMachine/fsm_reqts_and_vars.json",
         "LiftPlusCruise": "caseStudies/LiftPlusCruise/LPC_full_reqts_and_vars.json",
         "LMCPS": "caseStudies/LMCPS/LM_requirements.json"}


def fetch() -> Path:
    if not (DEST / "caseStudies").exists():
        DEST.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["git", "clone", "-q", "--filter=blob:none", "--no-checkout", REPO, str(DEST)], check=True)
        subprocess.run(["git", "-C", str(DEST), "checkout", "-q", COMMIT, "--", "caseStudies"], check=True)
    return DEST


def load(case: str) -> tuple[list[dict], list[dict]]:
    d = json.loads((fetch() / CASES[case]).read_text())
    reqs = d["requirements"] if isinstance(d, dict) else d
    vars_ = [v for v in (d.get("variables", []) if isinstance(d, dict) else []) if v.get("idType")]
    return [dict(id=r["reqid"], text=" ".join(r["fulltext"].split()), rationale=r.get("rationale", ""))
            for r in reqs], vars_


# ---------- expressions ----------
TOK = re.compile(r"\s*(=>|<=>|!=|<=|>=|[()!&|=<>+\-*/,]|\d+(?:\.\d+)?|[A-Za-z_][A-Za-z0-9_]*)")


class ParseError(Exception):
    pass


def tokenize(s: str) -> list[str]:
    s = s.strip(); out, i = [], 0
    while i < len(s):
        m = TOK.match(s, i)
        if not m:
            raise ParseError(f"unexpected character {s[i]!r}")
        out.append(m.group(1)); i = m.end()
    return out


class Expr:
    """Recursive-descent parser for FRETish expressions; evaluation over a dict of signal values."""

    def __init__(self, text: str):
        self.text = text
        self.t = tokenize(text); self.i = 0
        self.ast = self._implies()
        if self.i != len(self.t):
            raise ParseError(f"trailing tokens: {' '.join(self.t[self.i:])}")
        self.names = sorted(self._names(self.ast))

    def _peek(self):
        return self.t[self.i] if self.i < len(self.t) else None

    def _eat(self, tok=None):
        x = self._peek()
        if x is None or (tok and x != tok):
            raise ParseError(f"expected {tok or 'a token'}, got {x}")
        self.i += 1
        return x

    def _implies(self):
        if self._peek() == "if":
            self._eat("if"); a = self._or()
            if self._peek() != "then":
                raise ParseError("if without then")
            self._eat("then"); b = self._implies()
            return ("=>", a, b)
        a = self._or()
        if self._peek() in ("=>", "<=>"):
            op = self._eat(); return (op, a, self._implies())
        return a

    def _or(self):
        a = self._and()
        while self._peek() in ("|", "or", "xor"):
            op = self._eat(); a = ("|" if op != "xor" else "xor", a, self._and())
        return a

    def _and(self):
        a = self._not()
        while self._peek() in ("&", "and"):
            self._eat(); a = ("&", a, self._not())
        return a

    def _not(self):
        if self._peek() in ("!", "not"):
            self._eat(); return ("!", self._not())
        return self._cmp()

    def _cmp(self):
        a = self._add()
        if self._peek() in ("=", "!=", "<", "<=", ">", ">="):
            op = self._eat(); return (op, a, self._add())
        return a

    def _add(self):
        a = self._mul()
        while self._peek() in ("+", "-"):
            op = self._eat(); a = (op, a, self._mul())
        return a

    def _mul(self):
        a = self._unary()
        while self._peek() in ("*", "/"):
            op = self._eat(); a = (op, a, self._unary())
        return a

    def _unary(self):
        if self._peek() == "-":
            self._eat(); return ("neg", self._unary())
        return self._atom()

    def _atom(self):
        x = self._eat()
        if x == "(":
            e = self._implies(); self._eat(")"); return e
        if re.fullmatch(r"\d+(?:\.\d+)?", x):
            return ("num", float(x))
        if x in ("true", "TRUE"):
            return ("num", 1.0)
        if x in ("false", "FALSE"):
            return ("num", 0.0)
        if re.fullmatch(r"[A-Za-z_]\w*", x):
            if self._peek() == "(":
                raise ParseError(f"function {x}() not supported")
            return ("var", x)
        raise ParseError(f"unexpected {x}")

    def _names(self, n):
        if n[0] == "var":
            return {n[1]}
        if n[0] == "num":
            return set()
        return set().union(*(self._names(c) for c in n[1:]))

    def __call__(self, env: dict):
        return self._ev(self.ast, env)

    def _ev(self, n, e):
        op = n[0]
        if op == "num":
            return n[1]
        if op == "var":
            return e[n[1]]
        if op == "!":
            return not self._ev(n[1], e)
        if op == "neg":
            return -self._ev(n[1], e)
        a = self._ev(n[1], e)
        if op == "&":
            return bool(a) and bool(self._ev(n[2], e))
        if op == "|":
            return bool(a) or bool(self._ev(n[2], e))
        if op == "=>":
            return (not a) or bool(self._ev(n[2], e))
        b = self._ev(n[2], e)
        return {"<=>": lambda: bool(a) == bool(b), "xor": lambda: bool(a) != bool(b), "=": lambda: a == b,
                "!=": lambda: a != b, "<": lambda: a < b, "<=": lambda: a <= b, ">": lambda: a > b,
                ">=": lambda: a >= b, "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
                "/": lambda: a / b}[op]()


# ---------- requirements ----------
TIMING = re.compile(r"^(immediately|always|never|eventually|at the next timepoint|within (\d+) ticks?|"
                    r"for (\d+) ticks?|until (.+?))\s+satisfy\s+(.+)$", re.I)


@dataclass
class Req:
    id: str
    text: str
    trigger: str | None = None          # when | whenever | upon | if | None
    cond: Expr | None = None
    component: str = ""
    timing: str = "immediately"
    n: int = 0
    until: Expr | None = None
    resp: Expr | None = None
    error: str = ""
    rationale: str = ""
    names: list = field(default_factory=list)


def parse(rid: str, text: str, rationale: str = "") -> Req:
    r = Req(rid, text, rationale=rationale)
    try:
        if " shall " not in f" {text} ":
            raise ParseError("no 'shall'")
        left, right = re.split(r"\bshall\b", text, maxsplit=1)
        left, right = left.strip().rstrip(","), right.strip()
        m = re.match(r"^(when|whenever|upon|if)\s+(.*)$", left, re.I)
        if m:
            r.trigger = m.group(1).lower()
            rest = m.group(2).strip()
            mm = re.match(r"^(.*?)[,\s]+(?:the\s+)?([A-Za-z_]\w*)$", rest)
            if not mm:
                raise ParseError("cannot separate the condition from the component")
            r.cond, r.component = Expr(mm.group(1).strip().rstrip(",")), mm.group(2)
        elif re.match(r"^(in|during|before|after|while|only)\b", left, re.I):
            raise ParseError("scopes (in / before / after mode ...) not supported")
        else:
            r.component = left.split()[-1]
        right = re.sub(r"\s+", " ", right)
        t = TIMING.match(right) or (re.match(r"^satisfy\s+(.+)$", right) and None)
        if t is None:
            m2 = re.match(r"^satisfy\s+(.+)$", right)
            if not m2:
                raise ParseError(f"timing not supported: {right.split(' satisfy')[0]}")
            r.timing, r.resp = "immediately" if r.trigger else "always", Expr(m2.group(1))
        else:
            kw = t.group(1).lower()
            r.timing = ("next" if kw.startswith("at the next") else "within" if kw.startswith("within") else
                        "for" if kw.startswith("for") else "until" if kw.startswith("until") else kw)
            r.n = int(t.group(2) or t.group(3) or 0)
            if r.timing == "until":
                r.until = Expr(t.group(4))
            r.resp = Expr(t.group(5))
        r.names = sorted(set(r.resp.names) | set(r.cond.names if r.cond else []) | set(r.until.names if r.until else []))
    except ParseError as e:
        r.error = str(e)
    return r


def triggers(r: Req, trace: list[dict]) -> list[int]:
    if r.cond is None:
        return list(range(len(trace))) if r.timing in ("always", "never") else [0]
    c = [bool(r.cond(s)) for s in trace]
    if r.trigger == "whenever":
        return [t for t, v in enumerate(c) if v]
    return [t for t, v in enumerate(c) if v and (t == 0 or not c[t - 1])]


def violations(r: Req, trace: list[dict]) -> list[int]:
    """Trigger times at which the requirement is violated on this (finite) trace."""
    out, T = [], len(trace)
    for t in triggers(r, trace):
        ok = None
        if r.timing == "immediately":
            ok = bool(r.resp(trace[t]))
        elif r.timing == "next":
            ok = True if t + 1 >= T else bool(r.resp(trace[t + 1]))
        elif r.timing == "within":
            win = [bool(r.resp(trace[k])) for k in range(t, min(T, t + r.n + 1))]
            ok = any(win) or t + r.n >= T                      # not yet decided at the end of the trace
        elif r.timing == "for":
            ok = all(bool(r.resp(trace[k])) for k in range(t, min(T, t + r.n + 1)))
        elif r.timing == "always":
            ok = all(bool(r.resp(trace[k])) for k in range(t, T)) if r.cond is not None else bool(r.resp(trace[t]))
        elif r.timing == "never":
            ok = not any(bool(r.resp(trace[k])) for k in range(t, T)) if r.cond is not None else not r.resp(trace[t])
        elif r.timing == "until":
            ok = True
            for k in range(t, T):
                if r.until(trace[k]):
                    break
                if not r.resp(trace[k]):
                    ok = False; break
        elif r.timing == "eventually":
            ok = True                                          # cannot be violated on a finite prefix
        if ok is False:
            out.append(t)
    return out
