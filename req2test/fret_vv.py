"""V&V on real requirements (FRET case studies): consistency check, requirement-based test generation, execution on
an implementation written from the informal description, and mutation testing of that implementation.

    python -m req2test.fret_vv
"""
from __future__ import annotations

import ast
import importlib
import itertools
import json
import random
import types
from pathlib import Path

from .fret import ROOT, load, parse, triggers, violations

SYSTEMS = {
    "LiquidMixer": dict(module="req2test.sut.liquid_mixer",
                        bool_in=["emergency_button", "liquid_level_1", "liquid_level_2", "start_button",
                                 "timer_120sec_expire", "timer_60sec_expire"], enum_in={},
                        outputs=dict(valve_0=[False, True], valve_1=[False, True], valve_2=[False, True],
                                     stirring_motor=[False, True], timer_60sec_start=[False, True],
                                     timer_120sec_start=[False, True]), consts={}),
    "FSM": dict(module="req2test.sut.fsm", bool_in=["apfail", "good", "limits", "request", "standby", "supported"],
                enum_in=dict(state=[0, 1, 2, 3], senstate=[0, 1, 2]),
                outputs=dict(STATE=[0, 1, 2, 3], SENSTATE=[0, 1, 2], pullup=[False, True]),
                consts=dict(ap_transition_state=0, ap_nominal_state=1, ap_maneuver_state=2, ap_standby_state=3,
                            sen_nominal_state=0, sen_transition_state=1, sen_fault_state=2)),
}
# environment assumptions: the physics the requirements take for granted (level 2 is above level 1)
ASSUME = {"LiquidMixer": lambda s: not (s["liquid_level_2"] and not s["liquid_level_1"]), "FSM": lambda s: True}

# a realistic cycle, written by hand: start, fill to level 1, to level 2, stir 60 s, drain through valve 2
CYCLE = [dict(start_button=True), dict(), dict(liquid_level_1=True), dict(liquid_level_1=True),
         dict(liquid_level_1=True, liquid_level_2=True), dict(liquid_level_1=True, liquid_level_2=True),
         dict(liquid_level_1=True, liquid_level_2=True, timer_60sec_expire=True),
         dict(liquid_level_1=True, liquid_level_2=True), dict(liquid_level_1=True), dict(),
         dict(timer_120sec_expire=True), dict()]


def requirements(case):
    reqs, _ = load(case)
    return [parse(r["id"], r["text"], r["rationale"]) for r in reqs]


def all_inputs(cfg):
    names = cfg["bool_in"] + list(cfg["enum_in"])
    doms = [[False, True]] * len(cfg["bool_in"]) + list(cfg["enum_in"].values())
    for vals in itertools.product(*doms):
        yield dict(zip(names, vals))


# ---------- 1. review: consistency and scope of each requirement ----------
def review(case):
    cfg = SYSTEMS[case]
    R = requirements(case)
    notes = []
    for r in R:
        if r.cond is None and r.timing in ("within", "for", "next", "immediately"):
            notes.append(dict(req=r.id, issue="applies only at the start of the run",
                              detail=f"'{r.timing} {r.n or ''}' without a condition constrains the first "
                                     f"{r.n + 1 if r.n else 1} step(s) only; the rationale describes a rule that "
                                     "holds at all times"))
    # one-step conflicts: for every input valuation, the obligations at that step must be satisfiable together
    first = [r for r in R if r.timing in ("immediately", "always", "until", "for")]
    outs = [dict(zip(cfg["outputs"], v)) for v in itertools.product(*cfg["outputs"].values())]
    conflicts = {}
    for inp in all_inputs(cfg):
        if not ASSUME[case](inp):
            continue
        env0 = {**cfg["consts"], **inp}
        active = []
        for r in first:
            if r.cond is None and r.timing in ("for",):
                continue                                     # start-of-run only, reported above
            if r.cond is not None and not r.cond(env0):
                continue
            if r.timing == "until" and r.until({**env0, **outs[0]}):
                continue
            active.append(r)
        sat = [o for o in outs if all(r.resp({**env0, **o}) for r in active)]
        if sat:
            continue
        for a, b in itertools.combinations(active, 2):      # name the smallest conflicting pairs
            if not any(a.resp({**env0, **o}) and b.resp({**env0, **o}) for o in outs):
                key = (a.id, b.id)
                conflicts.setdefault(key, dict(reqs=[a.id, b.id], texts=[a.text, b.text], witnesses=0,
                                               example={k: v for k, v in inp.items() if v is not False}))
                conflicts[key]["witnesses"] += 1
    return dict(scope_notes=notes, conflicts=list(conflicts.values()))


# ---------- 2. test generation ----------
def random_step(cfg, rng, p=0.2):
    case = next(c for c, v in SYSTEMS.items() if v is cfg)
    while True:
        s = {k: rng.random() < p for k in cfg["bool_in"]}
        s.update({k: rng.choice(v) for k, v in cfg["enum_in"].items()})
        if ASSUME[case](s):
            return s


def satisfying(cfg, expr, rng, tries=400, value=True):
    for _ in range(tries):
        s = random_step(cfg, rng, p=0.5)
        if bool(expr({**cfg["consts"], **s})) == value:
            return s
    return None


def generate(case, per_req=8, seed=0):
    """Requirement-based tests: for each requirement, traces that trigger it (condition false then true), with the
    other inputs varied, and for 'until' requirements the release condition held off for a few steps first."""
    cfg = SYSTEMS[case]; rng = random.Random(seed)
    tests = []
    for r in requirements(case):
        for k in range(per_req):
            pre = []
            for _ in range(rng.randint(1, 3)):
                s = satisfying(cfg, r.cond, rng, value=False) if r.cond is not None else random_step(cfg, rng)
                pre.append(s or random_step(cfg, rng))
            trig = satisfying(cfg, r.cond, rng) if r.cond is not None else random_step(cfg, rng)
            if trig is None:
                continue
            post = []
            for j in range(rng.randint(3, 7)):
                if r.until is not None and j < 3:
                    s = satisfying(cfg, r.until, rng, value=False) or random_step(cfg, rng)
                else:
                    s = random_step(cfg, rng)
                post.append(s)
            tests.append(dict(target=r.id, inputs=pre + [trig] + post))
    return tests


def random_tests(case, n_steps, seed=1):
    cfg = SYSTEMS[case]; rng = random.Random(seed)
    tests, total = [], 0
    while total < n_steps:
        L = rng.randint(5, 11)
        tests.append(dict(target="random", inputs=[random_step(cfg, rng) for _ in range(L)])); total += L
    return tests


# ---------- 3. execution ----------
def execute(module, case, tests):
    cfg = SYSTEMS[case]
    R = [r for r in requirements(case) if not r.error]
    out = set()
    for ti, t in enumerate(tests):
        s = module.init(); trace = []
        for inp in t["inputs"]:
            s, o = module.step(s, inp)
            trace.append({**cfg["consts"], **inp, **o})
        for r in R:
            for v in violations(r, trace):
                out.add((r.id, ti, v))
    return out


def coverage(case, tests):
    cfg = SYSTEMS[case]
    R = [r for r in requirements(case) if not r.error]
    mod = importlib.import_module(cfg["module"])
    hit = set()
    for t in tests:
        s = mod.init(); trace = []
        for inp in t["inputs"]:
            s, o = mod.step(s, inp); trace.append({**cfg["consts"], **inp, **o})
        hit |= {r.id for r in R if r.cond is not None and triggers(r, trace)}
    return len(hit), sum(r.cond is not None for r in R)


# ---------- 4. mutation testing ----------
class Mutator(ast.NodeTransformer):
    """Single-point mutants of the controller: and/or swapped, comparison inverted, condition negated,
    boolean constant flipped, assignment deleted, integer constant changed."""

    def __init__(self, target):
        self.target, self.k, self.desc = target, -1, None

    def _hit(self, d):
        self.k += 1
        if self.k == self.target:
            self.desc = d
            return True
        return False

    def visit_BoolOp(self, n):
        self.generic_visit(n)
        if self._hit(f"line {n.lineno}: and/or swapped"):
            n.op = ast.Or() if isinstance(n.op, ast.And) else ast.And()
        return n

    def visit_Compare(self, n):
        self.generic_visit(n)
        swap = {ast.Eq: ast.NotEq, ast.NotEq: ast.Eq, ast.Lt: ast.GtE, ast.GtE: ast.Lt, ast.Gt: ast.LtE,
                ast.LtE: ast.Gt}
        if type(n.ops[0]) in swap and self._hit(f"line {n.lineno}: comparison inverted"):
            n.ops = [swap[type(n.ops[0])]()]
        return n

    def visit_If(self, n):
        self.generic_visit(n)
        if self._hit(f"line {n.lineno}: condition negated"):
            n.test = ast.UnaryOp(op=ast.Not(), operand=n.test)
        return n

    def visit_UnaryOp(self, n):
        self.generic_visit(n)
        if isinstance(n.op, ast.Not) and self._hit(f"line {n.lineno}: 'not' removed"):
            return n.operand
        return n

    def visit_Constant(self, n):
        if isinstance(n.value, bool) and self._hit(f"line {n.lineno}: {n.value} -> {not n.value}"):
            return ast.copy_location(ast.Constant(not n.value), n)
        return n

    def visit_Assign(self, n):
        self.generic_visit(n)
        if self._hit(f"line {n.lineno}: assignment deleted"):
            return ast.copy_location(ast.Pass(), n)
        return n


def mutants(module_name):
    src = Path(importlib.import_module(module_name).__file__).read_text()
    tree = ast.parse(src)
    step = next(f for f in tree.body if isinstance(f, ast.FunctionDef) and f.name == "step")
    k = 0
    while True:
        t = ast.parse(src)
        m = Mutator(k)
        st = next(f for f in t.body if isinstance(f, ast.FunctionDef) and f.name == "step")
        m.visit(st)
        if m.desc is None:
            break
        ast.fix_missing_locations(t)
        mod = types.ModuleType(f"mutant_{k}")
        exec(compile(t, f"<mutant {k}>", "exec"), mod.__dict__)        # our own controller code, mutated
        yield m.desc, mod
        k += 1
    del step


def mutation_score(case, tests):
    cfg = SYSTEMS[case]
    orig = importlib.import_module(cfg["module"])
    base = execute(orig, case, tests)
    killed, total, survivors = 0, 0, []
    for desc, mod in mutants(cfg["module"]):
        total += 1
        try:
            res = execute(mod, case, tests)
        except Exception:  # noqa: BLE001  (a crashing mutant is killed)
            res = None
        if res != base:
            killed += 1
        else:
            survivors.append(desc)
    return dict(mutants=total, killed=killed, score=round(killed / max(total, 1), 3), survivors=survivors)


def scenario(case="LiquidMixer"):
    """Run the realistic cycle and report which requirements the implementation violates, and when."""
    cfg = SYSTEMS[case]
    mod = importlib.import_module(cfg["module"])
    inputs = [{**{k: False for k in cfg["bool_in"]}, **x} for x in CYCLE]
    s = mod.init(); trace = []
    for inp in inputs:
        s, o = mod.step(s, inp); trace.append({**inp, **o})
    viol = {r.id: violations(r, trace) for r in requirements(case) if not r.error}
    return dict(steps=[dict(inputs=sorted(k for k, v in t.items() if v and k in cfg["bool_in"]),
                            outputs=sorted(k for k, v in t.items() if v and k in cfg["outputs"])) for t in trace],
                violated={k: v for k, v in viol.items() if v})


def budget_curve(case, seeds=(0, 1, 2)):
    rows = []
    for per in (1, 2, 4, 8):
        for sd in seeds:
            gen = generate(case, per_req=per, seed=sd)
            steps = sum(len(t["inputs"]) for t in gen)
            rnd = random_tests(case, steps, seed=100 + sd)
            rows.append(dict(per_req=per, seed=sd, steps=steps, generated=mutation_score(case, gen)["score"],
                             random=mutation_score(case, rnd)["score"]))
    return rows


def main():
    res = {}
    for case in SYSTEMS:
        R = requirements(case)
        rv = review(case)
        gen = generate(case)
        steps = sum(len(t["inputs"]) for t in gen)
        rnd = random_tests(case, steps)
        orig = importlib.import_module(SYSTEMS[case]["module"])
        fails = sorted({v[0] for v in execute(orig, case, gen)})
        res[case] = dict(requirements=len(R), parsed=sum(not r.error for r in R), review=rv,
                         generated=dict(tests=len(gen), steps=steps, triggered=coverage(case, gen),
                                        **mutation_score(case, gen)),
                         random=dict(tests=len(rnd), steps=sum(len(t["inputs"]) for t in rnd),
                                     triggered=coverage(case, rnd), **mutation_score(case, rnd)),
                         requirements_failed_by_the_implementation=fails, budget=budget_curve(case))
        if case == "LiquidMixer":
            res[case]["realistic_cycle"] = scenario(case)
        print(case, json.dumps({k: v for k, v in res[case].items() if k != "review"}, default=str)[:600], flush=True)
    for case in ("LiftPlusCruise", "LMCPS"):
        R = requirements(case)
        res[case] = dict(requirements=len(R), parsed=sum(not r.error for r in R),
                         not_parsed={r.id: r.error for r in R if r.error})
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results/fret_metrics.json").write_text(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
