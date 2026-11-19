"""Requirement analysis: EARS parsing against the interface dictionary, and quality checks.

A requirement is testable when its trigger and every response can be mapped to signals of the test bench
with explicit values. Everything else is returned to the author with the reason, instead of being guessed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

DATA = Path(__file__).resolve().parents[1] / "data"


def load_dictionary(path: Path = DATA / "signals.yaml") -> dict:
    return yaml.safe_load(path.read_text())


def load_requirements(path: Path = DATA / "requirements.yaml") -> list[dict]:
    return yaml.safe_load(path.read_text())


@dataclass
class Trigger:
    kind: str                     # analog | event | condition
    phrase: str
    signal: str = ""
    op: str = ""                  # > | <
    value: float = 0.0
    unit: str = ""
    hold_ms: int = 0
    meta: dict = field(default_factory=dict)


@dataclass
class Response:
    action: str                   # open_k1 | close_k1 | keep_k1_open | set_fault | warning | fan_on | fan_off |
                                  # clear_faults | inhibit_start | log_fault
    code: str = ""
    within_ms: int | None = None


@dataclass
class Parsed:
    id: str
    text: str
    pattern: str = ""
    trigger: Trigger | None = None
    guards: list[str] = field(default_factory=list)
    responses: list[Response] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)

    @property
    def testable(self) -> bool:
        return self.trigger is not None and bool(self.responses) and not self.issues


# ---------- quality checks ----------
WEAK = r"\b(quickly|fast|easy|easily|appropriate|adequate|as soon as possible|asap|normally|possibly|" \
       r"user-friendly|robust|sufficient|reasonable|if possible|as required|accordingly|short)\b"
RULES = [
    ("weak_word", WEAK),
    ("should", r"\b(should|may|might|could|will)\b"),
    ("and_or", r"and/or"),
    ("open_list", r"\betc\b|and so on"),
    ("vague_quantifier", r"\b(all relevant|some|several|various|many|most)\b"),
    ("escape_clause", r"\b(if necessary|unless|where possible|if needed|when appropriate)\b"),
    ("passive_no_actor", r"\bshall be \w+ed\b(?!.*\bby\b)"),
    ("vague_condition", r"\b(too high|too low|is low|is high|is hot|is cold|too hot)\b"),
]


def quality(text: str, units: list[str]) -> list[str]:
    tl = text.lower()
    out = [name for name, pat in RULES if re.search(pat, tl)]
    for m in re.finditer(r"(exceeds?|is below|above|below|over|under)\s+(\d+(?:\.\d+)?)(\s*([^\s,.]+))?", text):
        unit = (m.group(4) or "").strip()
        if unit not in units:
            out.append("missing_unit")
    return sorted(set(out))


# ---------- EARS parsing ----------
EARS = [
    ("event", re.compile(r"^When (?P<trig>.+?), the controller shall (?P<resp>.+?)\.$")),
    ("unwanted", re.compile(r"^If (?P<trig>.+?), then the controller shall (?P<resp>.+?)\.$")),
    ("state", re.compile(r"^While (?P<trig>.+?), the controller shall (?P<resp>.+?)\.$")),
]
NUM = r"(\d+(?:\.\d+)?)"


def _time_ms(v: str, unit: str) -> int:
    return int(float(v) * (1000 if unit == "s" else 1))


def parse_trigger(phrase: str, D: dict) -> tuple[Trigger | None, list[str]]:
    guards = []
    for g in re.findall(r"\b(?:and|while) (no fault is active|the motor is running|the fault condition has cleared)",
                        phrase):
        guards.append(g)
    core = re.split(r"\s+(?:and|while)\s+(?:no fault|the motor is running|the fault condition)", phrase)[0]
    core = core.strip()
    for name, spec in D["conditions"].items():
        if core == name:
            return Trigger("condition", core, meta=spec), guards
    core = re.sub(r"^(a|an|the)\s+", "", core)
    for name, spec in D["analog"].items():
        m = re.match(rf"(?:the )?{re.escape(name)} (exceeds?|is below) {NUM} (\S+?)(?: for more than {NUM} (ms|s))?$",
                     core)
        if m:
            t = Trigger("analog", core, spec["signal"], ">" if m.group(1).startswith("exceed") else "<", float(m.group(2)),
                        m.group(3), _time_ms(m.group(4), m.group(5)) if m.group(4) else 0, meta=spec)
            return t, guards
    for name, spec in D["events"].items():
        if core.endswith(name) or core == name:
            return Trigger("event", core, spec["signal"], meta=spec), guards
    for name, spec in D["conditions"].items():
        if core == name:
            return Trigger("condition", core, meta=spec), guards
    return None, guards


RESP = [
    (r"close the motor contactor K1(?: within {n} (ms|s))?", "close_k1"),
    (r"open the motor contactor K1(?: within {n} (ms|s))?", "open_k1"),
    (r"keep the motor contactor K1 open", "keep_k1_open"),
    (r"set fault code (E\d\d)", "set_fault"),
    (r"raise warning (W\d\d)", "warning"),
    (r"start the cooler fan", "fan_on"),
    (r"stop the cooler fan", "fan_off"),
    (r"clear the active faults", "clear_faults"),
    (r"inhibit the motor start", "inhibit_start"),
    (r"write the fault code and a time stamp to the fault log", "log_fault"),
]


def parse_responses(text: str) -> tuple[list[Response], list[str]]:
    out, rest = [], text
    for pat, action in RESP:
        rx = re.compile(pat.format(n=NUM))
        for m in rx.finditer(text):
            g = m.groups()
            r = Response(action)
            if action in ("set_fault", "warning"):
                r.code = g[0]
            elif action in ("close_k1", "open_k1") and g and g[0]:
                r.within_ms = _time_ms(g[0], g[1])
            out.append(r)
            rest = rest.replace(m.group(0), "")
    leftover = re.sub(r"\b(and|,)\b|,", " ", rest).strip(" .")
    issues = [] if not leftover.strip() else ["response_not_in_dictionary"]
    return out, issues


def analyse(req: dict, D: dict) -> Parsed:
    p = Parsed(req["id"], req["text"])
    p.issues = quality(req["text"], D["units"])
    for name, rx in EARS:
        m = rx.match(req["text"])
        if m:
            p.pattern = name
            p.trigger, p.guards = parse_trigger(m.group("trig"), D)
            p.responses, iss = parse_responses(m.group("resp"))
            p.issues += iss
            if p.trigger is None:
                p.issues.append("trigger_not_in_dictionary")
            break
    else:
        p.issues.append("not_ears")
    p.issues = sorted(set(p.issues))
    return p
