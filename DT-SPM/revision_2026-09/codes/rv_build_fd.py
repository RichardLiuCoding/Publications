"""Regenerate FD libraries from the supplied IBW files using the source notebook preprocessing.

Tap300: Clean up data to train DT.ipynb, cells 5 and 12–17.
Grating: DT-SPM_FD based_RL_v9.ipynb, cells 3 and 57–64.
Outputs are compared to the archived libraries; the archived inputs remain untouched.
"""
import json,pickle
import numpy as np
import aespm.tools as at
from rv_common import ROOT,OUT

def read_fd(obj):
    i=np.argmax(obj.data[0]);w=min(i,len(obj.data[0])-i)
    f=np.array([obj.data[j][i-w:i] for j in range(3)],dtype=float)
    b=np.array([obj.data[j][i:i+w] for j in range(3)],dtype=float)
    f[1]/=1e-9;b[1]/=1e-9
    return f,b

def convert(files,L,drop_last=False):
    objects=[at.load_ibw(str(f)) for f in files]; pairs=[read_fd(o) for o in objects]
    selected=pairs[:-1] if drop_last else pairs
    d={'height':np.stack([(f[0]-np.min(f[0][-L:]))[-L:]*1e9 for f,b in selected]),
       'amp':np.stack([f[1][-L:][::-1] for f,b in selected]),
       'phase':np.stack([f[2][-L:][::-1] for f,b in selected])}
    if drop_last:
        d.update(height2=np.stack([(b[0]-np.min(b[0][:L]))[:L]*1e9 for f,b in selected]),
                 amp2=np.stack([b[1][:L][::-1] for f,b in selected]),phase2=np.stack([b[2][:L][::-1] for f,b in selected]))
    return objects,d

def compare(d,p):
    z=np.load(p);r={}
    for k in z.files:
        a,b=d[k],z[k];r[k]={'shape':list(a.shape),'reference_shape':list(b.shape)}
        if a.shape==b.shape:r[k].update(allclose=bool(np.allclose(a,b,rtol=1e-10,atol=1e-10,equal_nan=True)),max_abs_diff=float(np.nanmax(np.abs(a-b))))
        else:r[k]['allclose']=False
    return r

def main():
    out=OUT/'fd_libraries';out.mkdir(parents=True,exist_ok=True);report={}
    files=sorted((ROOT/'data/260514/Tap300').glob('AlScN_FD*.ibw'))
    objects,d=convert(files,1000,True)
    d['drive']=np.array([o.header['DriveAmplitude'] for o in objects])*objects[-1].header['AmpInvOLS']*1e9*420/3
    np.savez(out/'Tap300_AlScN.npz',**d);report['Tap300_AlScN']=compare(d,ROOT/'output/Tap300_AlScN.npz')
    files=sorted((ROOT/'data/250315/CaliSample01').glob('Cali_FD*.ibw'))
    objects,d=convert(files,50)
    with open(ROOT/'data/250315/pickles/250315_Cali1_MOBO training.pickle','rb') as f:p=pickle.load(f)
    topo=at.load_ibw(str(ROOT/'data/250315/CaliSample01/Cali_res1_0001.ibw'))
    factor=p['factor']*topo.header['AmpInvOLS']*1e9
    d['drive']=np.array([o.header['DriveAmplitude'] for o in objects])*factor
    np.savez(out/'cali_fd.npz',**d);report['cali_fd']=compare(d,ROOT/'output/cali_fd.npz')
    (out/'fd_regeneration_report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not all(x['allclose'] for r in report.values() for x in r.values()):raise SystemExit('FD library comparison differs: inspect report before proceeding')
if __name__=='__main__':main()
