"""Autopilot and sensor mode logic, written from the informal description of FRET's FiniteStateMachine case study
(from the Lockheed Martin Cyber-Physical challenge problems). 'state' and 'senstate' are the current modes (inputs
of the step), STATE and SENSTATE the next modes. Autopilot modes: 0 transition, 1 nominal, 2 maneuver, 3 standby;
sensor modes: 0 nominal, 1 transition, 2 fault."""
TRANSITION, NOMINAL, MANEUVER, STANDBY = 0, 1, 2, 3
SEN_NOMINAL, SEN_TRANSITION, SEN_FAULT = 0, 1, 2


def init():
    return dict()


def step(s, i):
    st = i["state"]
    nxt = st
    if st == TRANSITION:
        if i["standby"]:
            nxt = STANDBY
        elif i["good"] and i["supported"]:
            nxt = NOMINAL
    elif st == NOMINAL:
        if i["standby"]:
            nxt = STANDBY
        elif not i["good"]:
            nxt = MANEUVER
    elif st == MANEUVER:
        if i["standby"] and i["good"]:
            nxt = STANDBY
        elif i["supported"] and i["good"]:
            nxt = TRANSITION
    elif st == STANDBY:
        if i["apfail"]:
            nxt = MANEUVER
        elif not i["standby"]:
            nxt = TRANSITION
    sen = i["senstate"]
    snext = sen
    if sen == SEN_NOMINAL:
        if i["limits"]:
            snext = SEN_FAULT
        elif not i["request"]:
            snext = SEN_TRANSITION
    elif sen == SEN_FAULT:
        if not i["request"] and not i["limits"]:
            snext = SEN_TRANSITION
    elif sen == SEN_TRANSITION:
        if i["request"]:
            snext = SEN_NOMINAL
    pullup = i["limits"] and not i["standby"] and not i["apfail"] and i["supported"]
    return s, dict(STATE=nxt, SENSTATE=snext, pullup=pullup)
