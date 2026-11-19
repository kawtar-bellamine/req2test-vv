"""Liquid mixer controller, written from the informal description of FRET's LiquidMixer case study (the
requirements' rationale): fill through valve 0 until level 1, through valve 1 until level 2, then stir for 60 s,
then drain through valve 2 for 120 s; the emergency button closes every valve and stops the motor.
One call = one controller cycle; outputs react in the same cycle as their inputs."""


def init():
    return dict(v0=False, v1=False, v2=False, motor=False)


def step(s, i):
    s = dict(s)
    t60_start = False
    t120_start = False
    if i["start_button"] and not i["liquid_level_1"]:
        s["v0"] = True
    if i["liquid_level_1"]:
        s["v0"] = False
        if not i["liquid_level_2"]:
            s["v1"] = True
    if i["liquid_level_2"]:
        s["v1"] = False
        s["motor"] = True
        t60_start = True
    if i["timer_60sec_expire"]:
        s["motor"] = False
        s["v2"] = True
        t120_start = True
    if i["timer_120sec_expire"]:
        s["v2"] = False
    if i["emergency_button"]:
        s["v0"] = False
        s["v1"] = False
        s["v2"] = False
        s["motor"] = False
    out = dict(valve_0=s["v0"], valve_1=s["v1"], valve_2=s["v2"], stirring_motor=s["motor"],
               timer_60sec_start=t60_start, timer_120sec_start=t120_start)
    return s, out
