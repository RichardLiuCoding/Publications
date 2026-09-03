"""Does the headline result survive the estimator the model validated but never adopted?

FFT annulus  -> what score()/aug_numbers.json use (and what every document reports)
Structure tensor -> what the md-574 synthetic race showed to be ~10x less noisy
Both are binned into the same three 60-deg classes on the same regions.
"""
import json, sys
from pathlib import Path
import numpy as np
from scipy.ndimage import gaussian_filter, gaussian_filter1d

PROJ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ))
import aug_toolkit as T
NS = T.load_toolkit(); ibw, signed = NS["ibw"], NS["signed"]
NUM = json.loads((PROJ/"aug_numbers.json").read_text())

def get(tag):
    d, h = ibw(tag)
    L = float(h["ScanSize"])*1e6
    S, _, _ = signed(d)
    return S, L, L/S.shape[0]*1000.0          # map, um, nm/px

def crop(S, L, x0,x1,y0,y1):
    n=S.shape[0]
    C=S[int(y0/L*n):int(y1/L*n), int(x0/L*n):int(x1/L*n)]
    m=min(C.shape); return C[:m,:m]

# ---------------------------------------------------------------- FFT annulus
def w_fft(Z, px, tri):
    m=Z.shape[0]; Z=(Z-Z.mean())*np.hanning(m)[:,None]*np.hanning(m)[None,:]
    P=np.abs(np.fft.fftshift(np.fft.fft2(Z)))**2
    yy,xx=np.indices(P.shape); dy,dx=yy-m//2, xx-m//2
    q=np.hypot(dy,dx)/(m*px/1000.0)
    dirn=np.mod(np.rad2deg(np.arctan2(dy,dx))+90.0,180.0)
    sel=(q>=1.5)&(q<=14.0)
    tot=P[sel].sum()
    w=[]; 
    for t in tri:
        dd=np.abs((dirn-t+90)%180-90)
        w.append(P[sel&(dd<=30.0)].sum()/tot)
    w=np.array(w); w=w/w.sum()
    pw=[P[sel&(np.abs((dirn-t+90)%180-90)<=15.0)].sum()/tot for t in tri]
    e=np.arange(0.,185.,5.); c=e[:-1]+2.5
    hh=np.array([P[sel&(dirn>=e[i])&(dirn<e[i+1])].sum() for i in range(len(c))])
    return w, np.array(pw), float(c[int(np.argmax(hh))])

# ------------------------------------------------------- structure tensor
def w_tensor(Z, px, tri, sg_grad_nm=45.0, sg_tens_nm=150.0, coh_min=0.10):
    Z=Z-Z.mean()
    sg=sg_grad_nm/px
    Gy=gaussian_filter1d(gaussian_filter1d(Z,sg,axis=0,order=1),sg,axis=1,order=0)
    Gx=gaussian_filter1d(gaussian_filter1d(Z,sg,axis=1,order=1),sg,axis=0,order=0)
    st=sg_tens_nm/px
    Jxx=gaussian_filter(Gx*Gx,st); Jyy=gaussian_filter(Gy*Gy,st); Jxy=gaussian_filter(Gx*Gy,st)
    tr=Jxx+Jyy
    coh=np.sqrt((Jxx-Jyy)**2+4*Jxy**2)/np.maximum(tr,1e-30)
    thg=0.5*np.rad2deg(np.arctan2(2*Jxy, Jxx-Jyy))       # dominant gradient dir
    thd=np.mod(thg+90.0,180.0)                            # stripe director
    msk=coh>=coh_min
    if msk.sum()<50: return None,None,None,0.0
    wgt=coh[msk]; th=thd[msk]
    w=[]; pw=[]
    for t in tri:
        dd=np.abs((th-t+90)%180-90)
        w.append(wgt[dd<=30.0].sum()); pw.append(wgt[dd<=15.0].sum())
    W=np.array(w); PW=np.array(pw)/wgt.sum()
    e=np.arange(0.,185.,5.); c=e[:-1]+2.5
    hh=np.array([wgt[(th>=e[i])&(th<e[i+1])].sum() for i in range(len(c))])
    return W/W.sum(), PW, float(c[int(np.argmax(hh))]), float(msk.mean())

# ---------------------------------------------------------------- run it
R6=NUM["R6"]; tri=R6["triad"]; A,B=R6["A"],R6["B"]
FR=[("virgin","LDART_0034"),("+A","LDART_0035"),("+B","LDART_0036")]
PAN={"P1":(0.6,2.6),"P2":(3.0,5.0),"P3":(5.4,7.4)}
out={}
print(f"R6 triad {tri}   A={A:.0f}  B={B:.0f}   (uniform: w=0.333, wedge=0.167)\n")
hdr=f"{'panel':6s}{'stage':7s}| {'w_FFT (A/64/B)':>22s} {'pkF':>5s} | {'w_TEN (A/64/B)':>22s} {'pkT':>5s} {'cov':>5s}"
print(hdr); print("-"*len(hdr))
for pn,(x0,x1) in PAN.items():
    out[pn]={}
    for lab,tag in FR:
        S,L,px=get(tag); Z=crop(S,L,x0,x1,3.0,5.0)
        wf,pf,kf=w_fft(Z,px,tri)
        wt,pt,kt,cov=w_tensor(Z,px,tri)
        out[pn][lab]=dict(w_fft=wf.tolist(),pw_fft=pf.tolist(),pk_fft=kf,
                          w_ten=wt.tolist(),pw_ten=pt.tolist(),pk_ten=kt,cov=cov)
        print(f"{pn:6s}{lab:7s}| {wf[0]:6.3f}{wf[1]:7.3f}{wf[2]:7.3f}  {kf:5.0f} |"
              f" {wt[0]:6.3f}{wt[1]:7.3f}{wt[2]:7.3f}  {kt:5.0f} {cov*100:4.0f}%")
json.dump(out, open(PROJ/"paper_llm"/"estimator_compare.json","w"), indent=1)

# ============================================================ effect sizes
print("\n\n============ do the CONCLUSIONS survive the estimator swap? ============")
iA, iB = 0, 2
def d(pn, s0, s1, i): 
    return out[pn][s1]["w_fft"][i]-out[pn][s0]["w_fft"][i], out[pn][s1]["w_ten"][i]-out[pn][s0]["w_ten"][i]
rows=[("write A on P1 (196 pulses)","P1","virgin","+A",iA),
      ("write A on P3 (196 pulses)","P3","virgin","+A",iA),
      ("untouched control P2, pass 1","P2","virgin","+A",iA),
      ("write B on written P1 (144)","P1","+A","+B",iB),
      ("write B on virgin P2 (144)","P2","virgin","+B",iB),
      ("P3 retention through pass 2","P3","+A","+B",iA)]
print(f"{'contrast':32s}{'dw_FFT':>9s}{'dw_TEN':>9s}   agree on sign?")
for lab,pn,s0,s1,i in rows:
    a,b=d(pn,s0,s1,i)
    print(f"{lab:32s}{a:+9.3f}{b:+9.3f}   {'yes' if a*b>0 or (abs(a)<0.03 and abs(b)<0.03) else 'NO'}")

print("\n============ the dose split ============")
print(f"{'case':30s}{'pulses':>7s}{'w@cmd FFT':>11s}{'w@cmd TEN':>11s}")
for lab,pn,st,i,np_ in (("R6 P3 write A","P3","+A",iA,196),("R6 P1 write A","P1","+A",iA,196),
                        ("R6 P2 write B","P2","+B",iB,144),("R6 P1 write B","P1","+B",iB,144)):
    print(f"{lab:30s}{np_:7d}{out[pn][st]['w_fft'][i]:11.3f}{out[pn][st]['w_ten'][i]:11.3f}")

print("\n============ absolute agreement ============")
import itertools
af=[];at=[]
for pn in PAN:
    for lab,_ in FR:
        af+=out[pn][lab]["w_fft"]; at+=out[pn][lab]["w_ten"]
af=np.array(af); at=np.array(at)
print(f"  mean |w_FFT - w_TEN| over all 27 components : {np.abs(af-at).mean():.3f}")
print(f"  max                                          : {np.abs(af-at).max():.3f}")
dfft=[];dten=[]
for lab,pn,s0,s1,i in rows:
    a,b=d(pn,s0,s1,i); dfft.append(a); dten.append(b)
dfft=np.array(dfft);dten=np.array(dten)
print(f"  mean |dw_FFT - dw_TEN| over the 6 contrasts  : {np.abs(dfft-dten).mean():.3f}")
print(f"  correlation of the six contrasts             : {np.corrcoef(dfft,dten)[0,1]:.3f}")
