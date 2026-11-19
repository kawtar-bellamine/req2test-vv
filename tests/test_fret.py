from req2test.fret import Expr, parse, violations
from req2test.fret_vv import SYSTEMS, review, requirements


def test_expression_parser_is_safe_and_correct():
    e = Expr("(standby & state = ap_transition_state) => STATE = ap_standby_state")
    env = dict(standby=True, state=0, ap_transition_state=0, STATE=3, ap_standby_state=3)
    assert e(env) and not e({**env, "STATE": 1})
    assert Expr("if ! liquid_level_1 then valve_0")(dict(liquid_level_1=True, valve_0=False))


def test_fretish_timings():
    r = parse("X", "when a, the c shall until (b | e) satisfy p")
    assert r.timing == "until" and r.cond.names == ["a"]
    tr = [dict(a=0, b=0, e=0, p=0), dict(a=1, b=0, e=0, p=1), dict(a=1, b=0, e=0, p=0), dict(a=1, b=1, e=0, p=0)]
    assert violations(r, tr) == [1]
    r = parse("Y", "FSM shall within 5 ticks satisfy p")
    assert r.timing == "within" and r.n == 5 and r.cond is None


def test_case_studies_parse_completely():
    for case in SYSTEMS:
        assert all(not r.error for r in requirements(case)), case


def test_review_finds_the_known_conflicts():
    lm = review("LiquidMixer")["conflicts"]
    assert any(set(c["reqs"]) == {"LM-001", "LM-009"} for c in lm)
    fsm = review("FSM")
    assert len(fsm["conflicts"]) == 4 and {n["req"] for n in fsm["scope_notes"]} == {"FSM-006", "FSM-007"}
