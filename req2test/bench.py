"""Software-in-the-loop test bench: a reference model of the HPU-200 unit controller, its mutants, and the
runner that plays a test specification against them.

The reference model is written from the intended behaviour, independently of the requirement parser. The
mutants are the bugs a real implementation could have (a threshold off by a few units, >= instead of >, a
timer forgotten, a wrong fault code). A test suite is good if it passes on the reference and fails on the mutants.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field

DT = 10  # ms per step

REF = dict(
    p_high=240.0, p_high_t=2000, p_high_strict=True, p_low=150.0, p_low_t=10000, p_low_needs_run=True,
    t_trip=70.0, t_trip_strict=True, fan_on=45.0, fan_off=40.0, t_cold=10.0, t_warn=60.0, p_warn=230.0,
    ma_low=3.6, ma_high=21.0, i_trip=32.0, i_trip_t=5000, filter_h=500.0,
    close_latency=100, stop_latency=20, estop_latency=20, level_latency=20,
    code_estop="E01", code_phigh="E12", code_temp="E34", code_level="E40", code_ma="E21", code_phase="E05",
    code_cur="E07", w_plow="W03", w_cold="W07", w_filter="W20", w_temp="W30", w_pwarn="W11",
    start_needs_no_fault=True, cold_inhibits=True, reset_checks_condition=True, log_timestamp=True,
    estop_sets_code=True, phase_sets_code=True,
)

MUTANTS = {
    "M01 pressure trip at 245 bar": dict(p_high=245.0),
    "M02 pressure trip on >= instead of >": dict(p_high_strict=False),
    "M03 pressure trip delay 1 s instead of 2 s": dict(p_high_t=1000),
    "M04 pressure trip without delay": dict(p_high_t=0),
    "M05 low-pressure warning after 5 s": dict(p_low_t=5000),
    "M06 low-pressure warning also when stopped": dict(p_low_needs_run=False),
    "M07 temperature trip at 72 °C": dict(t_trip=72.0),
    "M08 temperature trip on >= 70 °C": dict(t_trip_strict=False),
    "M09 fan starts at 50 °C": dict(fan_on=50.0),
    "M10 fan without hysteresis": dict(fan_off=45.0),
    "M11 cold-start warning at 5 °C": dict(t_cold=5.0),
    "M12 transmitter low limit 3.8 mA": dict(ma_low=3.8),
    "M13 transmitter high limit 22 mA": dict(ma_high=22.0),
    "M14 current trip at 35 A": dict(i_trip=35.0),
    "M15 current trip delay 3 s": dict(i_trip_t=3000),
    "M16 filter warning at 600 h": dict(filter_h=600.0),
    "M17 contactor closes after 700 ms": dict(close_latency=700),
    "M18 stop opens after 300 ms": dict(stop_latency=300),
    "M19 emergency stop opens after 150 ms": dict(estop_latency=150),
    "M20 low level opens after 1.5 s": dict(level_latency=1500),
    "M21 wrong code for temperature trip (E33)": dict(code_temp="E33"),
    "M22 wrong code for pressure trip (E21)": dict(code_phigh="E21"),
    "M23 start allowed with an active fault": dict(start_needs_no_fault=False),
    "M24 cold start not inhibited": dict(cold_inhibits=False),
    "M25 reset clears a fault still present": dict(reset_checks_condition=False),
    "M26 fault log without time stamp": dict(log_timestamp=False),
    "M27 emergency stop sets no fault code": dict(estop_sets_code=False),
    "M28 phase loss sets no fault code": dict(phase_sets_code=False),
    "M29 temperature warning at 65 °C": dict(t_warn=65.0),
    "M30 pressure warning at 235 bar": dict(p_warn=235.0),
}

NOMINAL = dict(pressure=210.0, temperature=35.0, pt_current=12.4, motor_current=24.0, filter_hours=100.0,
               estop=False, level_ok=True, phase_ok=True)


@dataclass
class Controller:
    p: dict = field(default_factory=lambda: dict(REF))
    t: int = 0
    k1: bool = False
    fan: bool = False
    faults: set = field(default_factory=set)
    warnings: set = field(default_factory=set)
    log: list = field(default_factory=list)
    timers: dict = field(default_factory=dict)
    pending: list = field(default_factory=list)   # (time, action)
    inputs: dict = field(default_factory=lambda: dict(NOMINAL))

    def _held(self, key: str, cond: bool, ms: int) -> bool:
        if cond:
            self.timers.setdefault(key, self.t)
            return self.t - self.timers[key] > ms if ms > 0 else True
        self.timers.pop(key, None)
        return False

    def _fault(self, code: str):
        if code not in self.faults:
            self.faults.add(code)
            self.log.append((self.t, code) if self.p["log_timestamp"] else (None, code))

    def _open_after(self, ms: int):
        self.pending.append((self.t + ms, "open"))

    def conditions(self) -> dict:
        p, x = self.p, self.inputs
        gt = (lambda a, b, strict: a > b if strict else a >= b)
        return {
            p["code_estop"]: x["estop"],
            p["code_phigh"]: gt(x["pressure"], p["p_high"], p["p_high_strict"]),
            p["code_temp"]: gt(x["temperature"], p["t_trip"], p["t_trip_strict"]),
            p["code_level"]: not x["level_ok"],
            p["code_ma"]: x["pt_current"] < p["ma_low"] or x["pt_current"] > p["ma_high"],
            p["code_phase"]: not x["phase_ok"],
            p["code_cur"]: x["motor_current"] > p["i_trip"],
        }

    def step(self, pulses: set):
        p, x = self.p, self.inputs
        self.t += DT
        # analog supervision
        if x["estop"]:
            if p["estop_sets_code"]:
                self._fault(p["code_estop"])
            if self.k1 and "estop" not in self.timers:
                self.timers["estop"] = self.t; self._open_after(p["estop_latency"])
        else:
            self.timers.pop("estop", None)
        if self._held("phigh", self.conditions()[p["code_phigh"]], p["p_high_t"]):
            self._fault(p["code_phigh"])
        if self.conditions()[p["code_temp"]]:
            self._fault(p["code_temp"])
        if not x["level_ok"]:
            if "level" not in self.timers:
                self.timers["level"] = self.t; self._fault(p["code_level"]); self._open_after(p["level_latency"])
        else:
            self.timers.pop("level", None)
        if self.conditions()[p["code_ma"]]:
            self._fault(p["code_ma"])
        if not x["phase_ok"] and p["phase_sets_code"]:
            self._fault(p["code_phase"])
        if self._held("cur", x["motor_current"] > p["i_trip"], p["i_trip_t"]):
            self._fault(p["code_cur"])
        # warnings (not latched)
        w = set()
        if self._held("plow", x["pressure"] < p["p_low"] and (self.k1 or not p["p_low_needs_run"]), p["p_low_t"]):
            w.add(p["w_plow"])
        if x["temperature"] < p["t_cold"]:
            w.add(p["w_cold"])
        if x["filter_hours"] > p["filter_h"]:
            w.add(p["w_filter"])
        if x["temperature"] > p["t_warn"]:
            w.add(p["w_temp"])
        if x["pressure"] > p["p_warn"]:
            w.add(p["w_pwarn"])
        self.warnings = w
        # fan with hysteresis
        if x["temperature"] > p["fan_on"]:
            self.fan = True
        elif x["temperature"] < p["fan_off"]:
            self.fan = False
        # commands
        if "reset" in pulses:
            cond = self.conditions()
            self.faults = {f for f in self.faults if p["reset_checks_condition"] and cond.get(f, False)}
        if "stop" in pulses and self.k1:
            self._open_after(p["stop_latency"])
        if "start" in pulses and not self.k1:
            ok = (not self.faults or not p["start_needs_no_fault"]) and not (
                p["cold_inhibits"] and x["temperature"] < p["t_cold"]) and x["phase_ok"]
            if ok:
                self.pending.append((self.t + p["close_latency"], "close"))
        # faults force the contactor open (after the latency already scheduled for estop / level)
        if self.faults and self.k1 and not any(a == "open" for _, a in self.pending):
            self._open_after(p["stop_latency"])
        for when, action in sorted(self.pending):
            if when <= self.t:
                if action == "close" and (not self.faults or not p["start_needs_no_fault"]):
                    self.k1 = True
                elif action == "open":
                    self.k1 = False
        self.pending = [(w_, a) for w_, a in self.pending if w_ > self.t]


# ---------- test runner ----------
@dataclass
class Result:
    passed: bool
    failed_step: int | None = None
    message: str = ""


def observe(c: Controller, what: str):
    if what == "k1":
        return c.k1
    if what == "fan":
        return c.fan
    if what == "faults":
        return c.faults
    if what == "warnings":
        return c.warnings
    if what == "log":
        return c.log
    raise KeyError(what)


def run(test: dict, params: dict | None = None) -> Result:
    c = Controller(p=dict(REF, **(params or {})))
    for i, s in enumerate(test["steps"]):
        op = s["op"]
        if op == "set":
            c.inputs.update(s["values"])
        elif op == "pulse":
            c.step({s["signal"]})
        elif op == "wait":
            for _ in range(max(1, int(s["ms"]) // DT)):
                c.step(set())
        elif op == "watch":            # invariant: the value must hold at every step of the window
            for _ in range(max(1, int(s["ms"]) // DT)):
                c.step(set())
                v = observe(c, s["signal"])
                ok = (s["value"] in v) if s["signal"] in ("faults", "warnings") else v == s["value"]
                if not ok:
                    return Result(False, i, f"step {i}: watch {s['signal']}={s['value']!r} broken at t={c.t} ms")
        elif op in ("expect", "expect_not"):
            v = observe(c, s["signal"])
            if s["signal"] in ("faults", "warnings"):
                ok = s["value"] in v
            elif s["signal"] == "log":
                ok = any(code == s["value"] and ts is not None for ts, code in v)
            else:
                ok = v == s["value"]
            if op == "expect_not":
                ok = not ok
            if not ok:
                return Result(False, i, f"step {i}: {op} {s['signal']}={s['value']!r}, observed {v!r}")
        else:
            raise ValueError(op)
    return Result(True)


def mutation_score(tests: list[dict]) -> dict:
    killed = {}
    for name, m in MUTANTS.items():
        killers = [t["id"] for t in tests if not run(t, m).passed]
        killed[name] = killers
    n_k = sum(1 for v in killed.values() if v)
    return dict(score=n_k / len(MUTANTS), killed=n_k, total=len(MUTANTS), detail=killed)


def clone(test: dict) -> dict:
    return copy.deepcopy(test)


# ---------- random mutants, generated without looking at the tests ----------
THRESHOLDS = {"p_high": 1, "p_low": 1, "t_trip": 0.5, "fan_on": 0.5, "fan_off": 0.5, "t_cold": 0.5, "t_warn": 0.5,
              "p_warn": 1, "ma_low": 0.1, "ma_high": 0.1, "i_trip": 0.5, "filter_h": 1}
HOLDS = ["p_high_t", "p_low_t", "i_trip_t"]
DEADLINES = {"close_latency": 500, "stop_latency": 200, "estop_latency": 100, "level_latency": 1000}
FLAGS = ["p_high_strict", "t_trip_strict", "p_low_needs_run", "start_needs_no_fault", "cold_inhibits",
         "reset_checks_condition", "log_timestamp", "estop_sets_code", "phase_sets_code"]
CODES = [k for k in REF if k.startswith(("code_", "w_"))]


def random_mutants(n: int = 200, seed: int = 0) -> dict:
    """Each mutant breaks exactly one requirement: a threshold moved by 1 to 5 resolution steps, a persistence
    delay changed by 15% to 50%, a response slower than its deadline, a flag inverted, or a code swapped."""
    import random
    rng = random.Random(seed)
    out = {}
    while len(out) < n:
        kind = rng.choice(["threshold", "threshold", "hold", "deadline", "flag", "code"])
        if kind == "threshold":
            k = rng.choice(list(THRESHOLDS)); step = rng.choice([-5, -3, -2, -1, 1, 2, 3, 5])
            m = {k: round(REF[k] + step * THRESHOLDS[k], 3)}
        elif kind == "hold":
            k = rng.choice(HOLDS); f = rng.choice([0.5, 0.7, 0.85, 1.15, 1.3, 1.5])
            m = {k: int(REF[k] * f)}
        elif kind == "deadline":
            k = rng.choice(list(DEADLINES)); m = {k: int(DEADLINES[k] * rng.uniform(1.1, 2.0))}
        elif kind == "flag":
            k = rng.choice(FLAGS); m = {k: not REF[k]}
        else:
            k = rng.choice(CODES); other = rng.choice([REF[c] for c in CODES if REF[c] != REF[k]])
            m = {k: other}
        name = "R " + ", ".join(f"{a}={b}" for a, b in m.items())
        out[name] = m
    return out


def score_on(tests: list[dict], mutants: dict) -> dict:
    surv = [name for name, m in mutants.items() if all(run(t, m).passed for t in tests)]
    return dict(score=1 - len(surv) / len(mutants), killed=len(mutants) - len(surv), total=len(mutants),
                survivors=surv)
