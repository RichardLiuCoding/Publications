"""Is the tensor's disadvantage on real frames just drift? Register, then retest."""
import json, sys
from pathlib import Path
import numpy as np
PROJ=Path(__file__).resolve().parent.parent; sys.path.insert(0,str(PROJ))
sys.path.insert(0,str(PROJ/"paper_llm"))
import aug_toolkit as T
NS=T.load_toolkit(); ibw, signed = NS["ibw"], NS["signed"]
from estimator_test import w_fft, w_tensor
NUM=json.loads((PROJ/"aug_numbers.json").read_text())

def full(tag):
    d,h=ibw(tag); L=float(h["ScanSize"])*1e6
    S,_,_=signed(d); H=d[0]
    return S,H,L,L/S.shape[0]*1000.0

def shift_of(H0,H1,mx=8):
    A=H0-H0.mean(); B=H1-H1.mean()
    best=(0,0); bv=-9
    for dy in range(-mx,mx+1):
        for dx in range(-mx,mx+1):
            b=np.roll(np.roll(B,dy,0),dx,1)
            v=float((A*b).sum()/np.sqrt((A*A).sum()*(b*b).sum()))
            if v>bv: bv, best = v,(dy,dx)
    return best,bv

def cut(S,L,x0,x1,y0,y1):
    n=S.shape[0]; C=S[int(y0/L*n):int(y1/L*n), int(x0/L*n):int(x1/L*n)]
    m=min(C.shape); return C[:m,:m]

PAIRS=[("R6","LDART_0033","LDART_0034",NUM["R6"]["triad"],
        [("P1",0.6,2.6,3.0,5.0),("P2",3.0,5.0,3.0,5.0),("P3",5.4,7.4,3.0,5.0)]),
       ("R7","LDART_0037","LDART_0038",NUM["R7"]["triad"],
        [("Q1",1.2,3.2,4.8,6.8),("Q2",4.8,6.8,4.8,6.8),("Q3",1.2,3.2,1.2,3.2)])]
print(f"{'region':10s}{'shift(px)':>11s}{'corr':>7s}{'|dw|FFT raw':>13s}{'reg':>8s}{'|dw|TEN raw':>13s}{'reg':>8s}")
rf=[];rt=[];gf=[];gt=[]
for area,t0,t1,tri,regs in PAIRS:
    S0,H0,L,px=full(t0); S1,H1,_,_=full(t1)
    (dy,dx),cv=shift_of(H0,H1)
    S1r=np.roll(np.roll(S1,dy,0),dx,1)
    for nm,x0,x1,y0,y1 in regs:
        Z0=cut(S0,L,x0,x1,y0,y1); Z1=cut(S1,L,x0,x1,y0,y1); Z1r=cut(S1r,L,x0,x1,y0,y1)
        f0,_,_=w_fft(Z0,px,tri); f1,_,_=w_fft(Z1,px,tri); f1r,_,_=w_fft(Z1r,px,tri)
        n0,_,_,_=w_tensor(Z0,px,tri); n1,_,_,_=w_tensor(Z1,px,tri); n1r,_,_,_=w_tensor(Z1r,px,tri)
        a=np.abs(f1-f0).max(); ar=np.abs(f1r-f0).max()
        b=np.abs(n1-n0).max(); br=np.abs(n1r-n0).max()
        rf.append(a);gf.append(ar);rt.append(b);gt.append(br)
        print(f"{area+' '+nm:10s}{f'({dy:+d},{dx:+d})':>11s}{cv:7.2f}{a:13.3f}{ar:8.3f}{b:13.3f}{br:8.3f}")
import numpy as np
print(f"\n{'MEAN':10s}{'':11s}{'':7s}{np.mean(rf):13.3f}{np.mean(gf):8.3f}{np.mean(rt):13.3f}{np.mean(gt):8.3f}")
print(f"\nregistration helps the tensor by {np.mean(rt)/np.mean(gt):.2f}x, the FFT by {np.mean(rf)/np.mean(gf):.2f}x")
print(f"after registration the FFT is still {np.mean(gt)/np.mean(gf):.1f}x more reproducible than the tensor")
