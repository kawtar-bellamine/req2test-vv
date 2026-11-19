from req2test.bench import MUTANTS, REF, run, score_on
from req2test.generate import generate, gherkin
from req2test.graph import run_workflow
from req2test.parse import analyse, load_dictionary, load_requirements, quality

D = load_dictionary()
REQS = load_requirements()
PARSED = [analyse(r, D) for r in REQS]


def test_parser_reads_thresholds_delays_and_codes():
    p = next(x for x in PARSED if x.id == "REQ-004")
    assert p.testable and p.trigger.signal == "pressure" and p.trigger.op == ">" and p.trigger.value == 240
    assert p.trigger.hold_ms == 2000
    assert {r.code for r in p.responses if r.action == "set_fault"} == {"E12"}


def test_guard_and_deadline():
    p = next(x for x in PARSED if x.id == "REQ-001")
    assert p.guards == ["no fault is active"] and p.responses[0].within_ms == 500


def test_quality_rules():
    assert "weak_word" in quality("The controller shall respond quickly.", D["units"])
    assert "missing_unit" in quality("When the temperature exceeds 60, the controller shall stop.", D["units"])
    assert quality("When the system pressure exceeds 240 bar, the controller shall stop.", D["units"]) == []


def test_every_ambiguous_requirement_is_sent_back():
    for r, p in zip(REQS, PARSED):
        assert p.testable != bool(r.get("ambiguous")), r["id"]


def test_generated_tests_pass_on_reference_model():
    for t in generate(PARSED):
        assert run(t).passed, (t["id"], run(t).message)


def test_generated_suite_beats_naive_suite():
    full, naive = generate(PARSED), generate(PARSED, naive=True)
    assert score_on(full, MUTANTS)["killed"] > score_on(naive, MUTANTS)["killed"]


def test_boundary_test_catches_off_by_one_operator():
    t = next(t for t in generate(PARSED) if t["id"] == "TC-004-02")
    assert run(t).passed and not run(t, dict(p_high_strict=False)).passed


def test_gherkin_and_workflow():
    s = run_workflow(review={"TC-004-01": "approved"})
    assert len(s["rework"]) == 15 and not s.get("discarded")
    t = next(t for t in s["tests"] if t["id"] == "TC-004-01")
    assert t["status"] == "approved" and "Scenario: TC-004-01" in gherkin(t)


def test_reference_parameters_match_requirements():
    assert REF["p_high"] == 240 and REF["close_latency"] <= 500 and REF["stop_latency"] <= 200
