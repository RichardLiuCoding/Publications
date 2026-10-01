"""Regenerate the historical supplementary panels from their archived source arrays.

These panels document the submitted encoder and post-acquisition correction.
They do not represent the revised candidate-condition benchmark.
"""
import sys
from rv_common import ROOT, FIG
sys.path.insert(0,str(ROOT/'codes'))
import matplotlib
matplotlib.use('Agg')
OUT=FIG/'legacy_supplement';OUT.mkdir(parents=True,exist_ok=True)
import _make_pro_figures as fp
import _make_comparison_figures as fc
fp.OUT=OUT;fc.OUT=OUT
fp.make_fig2_pro()
fc.make_c1();fc.make_c2();fc.make_c3();fc.make_c4()
p=ROOT/'codes/_make_pub_figures.py'
s=p.read_text().replace('OUT = ROOT / "output" / "pub_figures"','OUT = LEGACY_OUT')
exec(compile(s,str(p),'exec'),{'__name__':'__legacy_supplement__','__file__':str(p),'LEGACY_OUT':OUT})
