# -*- coding: utf-8 -*-
"""Verbatim agent excerpts for the provenance figure.

Each entry is quoted verbatim from the released transcript. Panels are
labelled by campaign and stage rather than by date, and the transcript position
of each is released with it. Three
normalizations are applied and nothing else. Bold and italic emphasis is
dropped, a long dash in the original becomes a comma, and a symbol is spelled
out in square brackets. Wording, contractions and word order are as sent.
"""

PANELS = [
 dict(tag="a", turn="excerpt 1", when="campaign 1, before the pulse lattice",
      claim="The agent derived the design rule the working recipe rests on, "
            "seven days before the write that used it.",
      quote=(
        "The same-sign mode leaves a standing sign template whose stripes run "
        "along the write direction, and that is what the in-plane variant "
        "selection couples to. It is the Vasudevan mechanism you corrected me "
        "on: the trajectory controls the sign/phase pattern, and the in-plane "
        "direction follows from the geometry of that pattern. Note it is also "
        "half the dose, one pass per line instead of two. Structured dose, not "
        "more dose."),
      after=("Two things are confounded with within_cycle and I can't "
             "separate them from n = 1: voltage went 6 to 7 V, and 90 degrees "
             "is exactly on a triad member while 0 and 60 sit midway between "
             "two."),
      after_label="and in the same turn, unprompted"),

 dict(tag="b", turn="excerpt 2", when="campaign 1, building the state",
      claim="Asked to compare two estimators, the agent rejected the "
            "operator's own suggestion with a structural argument, then "
            "misattributed a variance it had not measured.",
      quote=(
        "But Canny measures the wrong quantity. This is the more important "
        "finding, and it's why I wouldn't adopt it regardless of noise. "
        "Walls run parallel to stripes, so edge orientation gives the right "
        "direction, but edge length per unit area scales as area/[period]. "
        "So a finer-period family is over-counted. The control settles it."),
      after=("The FFT is nearly unbiased but very high-variance. With only "
             "14 to 20 periods across the region it's classic "
             "spectral-estimation variance, few independent samples per "
             "family. That explains the 0.014 to 0.047 frame-to-frame "
             "[population change] we measured on unchanged real states."),
      after_label="four sentences earlier, the error this paper corrects"),

 dict(tag="c", turn="excerpt 3", when="campaign 1, after the void run",
      claim="After the void run, the agent converted a missing control into a "
            "check that prints a hardware verdict instead of a physical one.",
      quote=(
        "Without the positive control, a null from the ladder is ambiguous "
        "between \u201cpulses can\u2019t reopen the gate\u201d and \u201cthis probe or "
        "area can\u2019t switch at all\u201d. I\u2019ve changed pulse_discs so a complete "
        "null now prints a hardware/area verdict, check the bias path and "
        "coating, move at least 50 micrometres, rather than sending you up the "
        "dwell/density/repeat escalation ladder, which only applies once "
        "something has switched."),
      after=None, after_label=None),

 dict(tag="d", turn="excerpt 4", when="campaign 2, autonomous phase",
      claim="Once it held the actuator, it replayed its own code against real "
            "frames and reported that the check encoding every safety rule "
            "had never run.",
      quote=(
        "Five defects found by simulating the real code path offline, the "
        "thing PITFALLS section 10.1 already told me to do and I hadn't been. "
        "Four had been live since IT1. IT2's written area was missing from the "
        "state file. It crashed in the verdict block before save_state, so "
        "used_areas never recorded (-14, 0), meaning S9 and check_area_fresh "
        "were both blind to it and IT4 could have written straight on top. "
        "preflight(), the S1 to S29 envelope as code, has never been called by "
        "any driver. grep -c gives 0, 0, 0 for IT1 to IT3. It crashed on "
        "prop['offset'] being None, which every driver's design guarantees, so "
        "it was unusable for exactly the case it was written for. The control "
        "tiles sat on a written panel. Audited against IT3's own frames: 3 of "
        "14 tiles overlapped P8. Excesses move by at most 0.022 and no verdict "
        "changes, C41 stands, but that was luck."),
      after=None, after_label=None),
]
