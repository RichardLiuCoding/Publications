# -*- coding: utf-8 -*-
"""Flowchart content, one row per cluster. Every node cites a turn or a run.

Row tuple: (date label, {lane: (text, citation)}, decision or None).
Lanes: H operator input, A agent construction, E experiment, T understanding.
Every label wraps to at most two lines of 28 characters.
"""

ROWS = [
 ("3 Aug",
  {"H": ("five theory documents. I run\nthe instrument", "t1"), "A": ("reads the documents,\nproposes six sessions", "")}, None),
 ("3 Aug",
  {"H": ("corrects the paper figure:\nphase, not direction", "t2"), "T": ("goal restated: move the\ndirection, not the phase", "")}, None),
 ("3 to 7 Aug",
  {"E": ("angle series, AC plus DC\nrasters, trajectory writes", ""), "T": ("a trajectory alone does not\nsteer an ordered state", "")}, None),
 ("7 Aug",
  {"A": ("derives pitch = half the\nlamellar period", "t3")}, None),
 ("11 Aug",
  {"H": ("proposes point pulses to\nbreak the long range order", "t4"), "T": ("action grammar moves to\nisolated pulses", "")}, "stop pushing continuous trajectories"),
 ("13 Aug",
  {"H": ("challenges the claim that\nthe area was already poled", "t5"), "A": ("designs a test instead of\nkeeping the phrase", "")}, None),
 ("13 Aug",
  {"H": ("asks how phase and the\ndirection are extracted", "t6"), "A": ("finds the channel sign\nerror, 10 of 46 pairs", "")}, None),
 ("13 Aug",
  {"H": ("Canny or Fourier, and which\nresists noise?", "t7"), "A": ("races three estimators on\nsynthetic truth", ""), "T": ("keep Fourier. The tensor is\nuntried on real frames", "")}, None),
 ("13 Aug",
  {"H": ("asks for the same location,\nnot the aggregate", "t8"), "A": ("builds the paired same\nlocation map", ""), "T": ("the aggregate reading is\noverturned", "")}, None),
 ("14 Aug",
  {"A": ("oriented lattice, matched\ncontrols, abort gate", ""), "E": ("R4: 576 sites, 208 min,\nvoid. No bias at the tip", "")}, "stage every run and add a positive control"),
 ("14 Aug",
  {"E": ("R5, R6, R7: 136 min, the\nwhole result", ""), "T": ("selector, eliminator,\nconsolidator", "")}, None),
 ("14 Aug",
  {"H": ("the write should have used\nthe opposite sign", "t9"), "A": ("finds the sign of the write\nvoltage was dropped", "")}, None),
 ("14 Aug",
  {"H": ("write the findings down and\ngrade them", "t10"), "T": ("report contrasts, not states\n(this paper)", "")}, "grade every claim in a persistent file"),
 ("20 Aug",
  {"H": ('propose a theory, generate\na hypothesis, refine it', 't11'), "A": ('writes T3: commensurate\ntemplate above a threshold', '')}, None),
 ("20 Aug",
  {"H": ('writing a 10 um area kills\nthe probe. Use less', 't12'), "A": ('packs more panels into one\nsmaller frame', '')}, None),
 ("21 Aug",
  {"H": ('again, only the directions\nof the superdomains', 't13'), "T": ('every amplitude result is\nrescored as a direction', '')}, None),
 ("21 Aug",
  {"H": ('scan centre plus size\ncannot exceed 50 um', 't14'), "A": ('codes it as a check that\nraises before any write', '')}, None),
 ("21 Aug",
  {"H": ('moved to a new area.\nConfirmed. Go', 't15'), "A": ('takes the actuator: propose,\npreflight, write, read', '')}, 'the handover: the agent now drives the instrument'),
 ("21 Aug",
  {"A": ('solves the dwell per panel\nso sigma is matched', ''), "E": ('IT1 to IT4: 4 halts, 3\nresults, 96 write min', ''), "T": ('period is irrelevant, but\nthe sign must alternate', '')}, None),
 ("21 Aug",
  {"H": ('what went wrong in IT1 and\nIT2? Avoid it', 't16'), "A": ('replays its own code offline\nand finds five defects', '')}, None),
 ("22 Aug",
  {"A": ('derives the null of the\nstatistic it actually uses', ''), "T": ('the threshold was three\ntimes too wide', '')}, 'measure the null, do not import it'),
 ("22 Aug",
  {"H": ('a terrace edge. Write UTK.\nby the morning', 't17'), "A": ('checks the height channel,\nsizes the letters from 4L', '')}, None),
 ("22 Aug",
  {"E": ('IT5: sigma ladder, 3 rungs\nfrom 0.70 to 1.52', ''), "T": ('no threshold, and w settles\nat 0.47 whatever sigma', '')}, None),
 ("22 Aug",
  {"E": ('IT6: raster canvas, then\nS9 refuses its own area', ''), "T": ('the raster aligns virgin\nfilm, it does not deplete', '')}, None),
 ("22 Aug",
  {"A": ('declares the reuse instead\nof renaming to dodge S9', ''), "E": ('IT10b: UTK at 11.1 x the\nnull, 63 % on target', ''), "T": ('orientation is writable,\nreadable, addressable', '')}, None),
 ("22 Aug",
  {"E": ('IT9: set, reverse, hold.\n34 min unchanged', ''), "T": ('three states, set and reset\nat will. A memory', '')}, 'report contrasts, grade every claim, keep the halts'),
]

# arrows drawn inside a row, as (row index, from lane, to lane)
LINKS = [(0, "H", "A"), (1, "H", "T"), (2, "E", "T"), (4, "H", "T"), (5, "H", "A"), (6, "H", "A"), (7, "H", "A"), (7, "A", "T"), (8, "H", "A"), (8, "A", "T"), (9, "A", "E"), (10, "E", "T"), (11, "H", "A"), (12, "H", "T"), (13, "H", "A"), (14, "H", "A"), (15, "H", "T"), (16, "H", "A"), (17, "H", "A"), (18, "A", "E"), (19, "H", "A"), (20, "A", "T"), (21, "H", "A"), (22, "E", "T"), (23, "E", "T"), (24, "A", "E"), (25, "E", "T")]


# the row at which the operator handed over the actuator
# the first row whose transcript position belongs to the second campaign
CAMPAIGN2_ROW = 13
PHASE2_ROW = 17

# the sequential transcript labels used in every figure. The mapping to the
# released transcript turn numbers is released with it.
TURN_MAP = {
 't1':  'campaign 1, turn 28',    't2':  'campaign 1, turns 66 and 71',
 't3':  'campaign 1, turn 373',   't4':  'campaign 1, turn 381',
 't5':  'campaign 1, turn 547',   't6':  'campaign 1, turn 555',
 't7':  'campaign 1, turn 574',   't8':  'campaign 1, turn 588',
 't9':  'campaign 1, turn 697',   't10': 'campaign 1, turn 705',
 't11': 'campaign 2, turn 131',   't12': 'campaign 2, turn 159',
 't13': 'campaign 2, turn 523',   't14': 'campaign 2, turn 750',
 't15': 'campaign 2, turn 845',   't16': 'campaign 2, turn 1033',
 't17': 'campaign 2, turn 1419',
}

