"""Empirical noise floor of each estimator: back-to-back frames, nothing done between.

This is the test the md-574 race predicted the answer to, on synthetic data,
and that was never run on the real frames.
"""
import json, sys
from pathlib import Path
import numpy as np
PROJ=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(PROJ))
sys.path.insert(0,str(PROJ/"paper_llm"))
from estimator_test import get, crop, w_fft, w_tensor          # reuse exactly
NUM=json.loads((PROJ/"aug_numbers.json").read_text())

PAIRS=[("R6 (-15,+10)", "LDART_0033","LDART_0034", NUM["R6"]["triad"],
        {"P1":(0.6,2.6),"P2":(3.0,5.0),"P3":(5.4,7.4)}, (3.0,5.0)),
       ("R7 (+15,+15)", "LDART_0037","LDART_0038", NUM["R7"]["triad"],
        {"Q1":(1.2,3.2),"Q2":(4.8,6.8),"Q3":(1.2,3.2)}, (4.8,6.8))]
print("Frame-to-frame |dw| on an UNCHANGED state (should be 0)\n")
print(f"{'area / region':22s}{'|dw| FFT':>10s}{'|dw| TENSOR':>13s}{'ratio':>8s}")
allf=[];allt=[]
for area,t0,t1,tri,pans,yr in PAIRS:
    for pn,(x0,x1) in pans.items():
        y0,y1=(3.0,5.0) if area.startswith("R6") else ((1.2,3.2) if pn=="Q3" else (4.8,6.8))
        S0,L0,px0=get(t0); S1,L1,px1=get(t1)
        Z0=crop(S0,L0,x0,x1,y0,y1); Z1=crop(S1,L1,x0,x1,y0,y1)
        f0,_,_=w_fft(Z0,px0,tri); f1,_,_=w_fft(Z1,px1,tri)
        n0,_,_,_=w_tensor(Z0,px0,tri); n1,_,_,_=w_tensor(Z1,px1,tri)
        df=np.abs(f1-f0).max(); dt=np.abs(n1-n0).max()
        allf.append(df); allt.append(dt)
        print(f"{area+' '+pn:22s}{df:10.3f}{dt:13.3f}{df/max(dt,1e-9):8.1f}")
af=np.array(allf); at=np.array(allt)
print(f"\n{'MEAN':22s}{af.mean():10.3f}{at.mean():13.3f}{af.mean()/at.mean():8.1f}")
print(f"{'MAX':22s}{af.max():10.3f}{at.max():13.3f}")
print(f"\nSynthetic prediction from the md-574 race (SNR 10->1, per realization):")
print(f"  FFT 0.162   Canny 0.045   TENSOR 0.016   -> predicted ratio FFT/TENSOR = 10.1")
print(f"Measured on these six unchanged-state region pairs:  ratio = {af.mean()/at.mean():.1f}")
json.dump(dict(fft=af.tolist(), tensor=at.tolist()),
          open(PROJ/"paper_llm"/"noise_compare.json","w"), indent=1)
