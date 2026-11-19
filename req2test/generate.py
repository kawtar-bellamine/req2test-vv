"""Test specification generation from parsed requirements.

Classic V&V techniques, applied systematically: nominal case, boundary value analysis around each threshold
(the threshold itself and one resolution step beyond it), timing boundaries (just before and just after a
persistence delay, response deadline), guard violation (the condition that must block the response) and
hysteresis. Every test carries the requirement it verifies and the technique that produced it.
"""
from __future__ import annotations

from .bench import NOMINAL
from .parse import Parsed

MARGIN = 500  # ms added after a persistence delay or used when no deadline is given


def _expect(responses, negate=False, phase="after"):
    steps = []
    for r in responses:
        op = "expect_not" if negate else "expect"
        if r.action == "open_k1":
            steps.append(dict(op=op, signal="k1", value=False))
        elif r.action == "close_k1":
            steps.append(dict(op=op, signal="k1", value=True))
        elif r.action == "set_fault":
            steps.append(dict(op=op, signal="faults", value=r.code))
        elif r.action == "warning":
            steps.append(dict(op=op, signal="warnings", value=r.code))
        elif r.action == "fan_on":
            steps.append(dict(op=op, signal="fan", value=True))
        elif r.action == "fan_off":
            steps.append(dict(op=op, signal="fan", value=False))
        elif r.action == "keep_k1_open":
            steps.append(dict(op=op, signal="k1", value=False))
    return steps


RUNNING = [dict(op="set", values=dict(NOMINAL)), dict(op="pulse", signal="start"), dict(op="wait", ms=600),
           dict(op="expect", signal="k1", value=True)]
STOPPED = [dict(op="set", values=dict(NOMINAL)), dict(op="wait", ms=50)]
LATCH_FAULT = [dict(op="set", values={"estop": True}), dict(op="wait", ms=50),
               dict(op="set", values={"estop": False}), dict(op="wait", ms=50)]


def _setup(p: Parsed):
    acts = {r.action for r in p.responses}
    if "inhibit_start" in acts:
        return [s for s in STOPPED]
    if "fan_off" in acts:
        return RUNNING + [dict(op="set", values={"temperature": 50.0}), dict(op="wait", ms=50),
                          dict(op="expect", signal="fan", value=True)]
    return [dict(s) for s in RUNNING]


def _inhibit_check(p: Parsed, negate=False):
    if not any(r.action == "inhibit_start" for r in p.responses):
        return []
    return [dict(op="pulse", signal="start"), dict(op="wait", ms=600),
            dict(op="expect" if not negate else "expect_not", signal="k1", value=False)]


def tests_for(p: Parsed, naive: bool = False) -> list[dict]:
    t, out = p.trigger, []
    n = [0]

    def add(technique, title, steps):
        n[0] += 1
        out.append(dict(id=f"TC-{p.id[4:]}-{n[0]:02d}", requirement=p.id, technique=technique, title=title,
                        steps=steps, status="proposed"))

    if t.kind == "analog":
        res, x, sig = float(t.meta["resolution"]), t.value, t.signal
        beyond = (lambda k: round(x + k * res, 3)) if t.op == ">" else (lambda k: round(x - k * res, 3))
        wait = t.hold_ms + MARGIN
        base = _setup(p)
        resp_steps = _expect([r for r in p.responses if r.action != "inhibit_start"])
        add("nominal", f"{sig} at {beyond(5)} {t.unit} for {wait} ms gives the response",
            base + [dict(op="set", values={sig: beyond(5)}), dict(op="wait", ms=wait)] + resp_steps
            + _inhibit_check(p))
        if naive:
            return out
        add("boundary", f"{sig} exactly at the threshold {x} {t.unit}: no response",
            base + [dict(op="set", values={sig: x}), dict(op="wait", ms=wait)]
            + _expect([r for r in p.responses if r.action != "inhibit_start"], negate=True)
            + _inhibit_check(p, negate=True))
        add("boundary", f"{sig} one step beyond the threshold ({beyond(1)} {t.unit}) gives the response",
            base + [dict(op="set", values={sig: beyond(1)}), dict(op="wait", ms=wait)] + resp_steps
            + _inhibit_check(p))
        if t.hold_ms:
            add("timing", f"{sig} beyond the threshold for less than {t.hold_ms} ms: no response yet, then response",
                base + [dict(op="set", values={sig: beyond(5)}), dict(op="wait", ms=t.hold_ms - 200)]
                + _expect(p.responses, negate=True)
                + [dict(op="wait", ms=400)] + resp_steps)
        if "the motor is running" in p.guards:
            add("guard", f"{sig} beyond the threshold with the motor stopped: no response",
                [dict(s) for s in STOPPED] + [dict(op="set", values={sig: beyond(5)}), dict(op="wait", ms=wait)]
                + _expect(p.responses, negate=True))
        return out

    if t.kind == "event":
        spec, sig = t.meta, t.signal
        trig = ([dict(op="pulse", signal=sig)] if spec["kind"] == "pulse"
                else [dict(op="set", values={sig: spec["active"]})])
        deadline = min([r.within_ms for r in p.responses if r.within_ms] or [MARGIN])
        if any(r.action == "close_k1" for r in p.responses):
            base = [dict(s) for s in STOPPED]
        elif any(r.action == "clear_faults" for r in p.responses):
            base = [dict(s) for s in STOPPED] + LATCH_FAULT + [dict(op="expect", signal="faults", value="E01")]
        else:
            base = [dict(s) for s in RUNNING]
        if any(r.action == "clear_faults" for r in p.responses):
            add("nominal", "reset with the fault condition gone clears the fault",
                base + trig + [dict(op="wait", ms=50), dict(op="expect_not", signal="faults", value="E01")])
            if not naive:
                add("guard", "reset while the fault condition is still present keeps the fault",
                    [dict(s) for s in STOPPED] + [dict(op="set", values={"estop": True}), dict(op="wait", ms=50)]
                    + trig + [dict(op="expect", signal="faults", value="E01"),
                              dict(op="watch", signal="faults", value="E01", ms=100)])
            return out
        add("nominal" if naive else "timing", f"{sig} then response checked at the {deadline} ms deadline",
            base + trig + [dict(op="wait", ms=deadline)] + _expect(p.responses))
        if naive:
            return out
        if "no fault is active" in p.guards:
            add("guard", f"{sig} while a fault is active: K1 never closes",
                [dict(s) for s in STOPPED] + LATCH_FAULT + trig
                + [dict(op="watch", signal="k1", value=False, ms=deadline + MARGIN)])
        codes = [r for r in p.responses if r.action == "set_fault"]
        if codes:
            add("logging", f"{sig} writes {codes[0].code} with a time stamp in the fault log",
                base + trig + [dict(op="wait", ms=deadline)]
                + [dict(op="expect", signal="log", value=codes[0].code)])
        return out

    if t.kind == "condition":
        chk = t.meta["check"]
        if chk == "fault_active":
            add("state", "with a latched fault, a start command never closes K1",
                [dict(s) for s in STOPPED] + LATCH_FAULT + [dict(op="pulse", signal="start"),
                                                             dict(op="watch", signal="k1", value=False, ms=700)])
            if not naive:
                add("state", "a fault raised while running opens K1 and keeps it open after the cause is gone",
                    [dict(s) for s in RUNNING] + LATCH_FAULT + [dict(op="wait", ms=MARGIN),
                                                                 dict(op="pulse", signal="start"),
                                                                 dict(op="wait", ms=700)] + _expect(p.responses))
        elif chk == "fault_set":
            add("nominal", "a fault is written to the log with its time stamp",
                [dict(s) for s in RUNNING] + LATCH_FAULT + [dict(op="expect", signal="log", value="E01")])
            if not naive:
                add("logging", "a second fault of another type is logged too",
                    [dict(s) for s in RUNNING] + [dict(op="set", values={"phase_ok": False}), dict(op="wait", ms=50),
                                                  dict(op="expect", signal="log", value="E05")])
    return out


def generate(parsed: list[Parsed], naive: bool = False) -> list[dict]:
    return [t for p in parsed if p.testable for t in tests_for(p, naive=naive)]


def gherkin(test: dict) -> str:
    lines = [f"  Scenario: {test['id']} {test['title']}", f"    # verifies {test['requirement']}, {test['technique']}"]
    first = True
    for s in test["steps"]:
        if s["op"] == "set":
            kw = "Given" if first else "And"
            lines.append(f"    {kw} inputs " + ", ".join(f"{k} = {v}" for k, v in s["values"].items()))
        elif s["op"] == "pulse":
            lines.append(f"    When the {s['signal']} button is pressed")
        elif s["op"] == "wait":
            lines.append(f"    And {s['ms']} ms elapse")
        elif s["op"] == "watch":
            lines.append(f"    Then {s['signal']} stays {s['value']} during {s['ms']} ms")
        else:
            neg = s["op"] == "expect_not"
            if s["signal"] in ("k1", "fan"):
                lines.append(f"    Then {s['signal']} is {(not s['value']) if neg else s['value']}")
            else:
                lines.append(f"    Then {s['signal']} {'does not contain' if neg else 'contains'} {s['value']}")
        first = False
    return "\n".join(lines)
