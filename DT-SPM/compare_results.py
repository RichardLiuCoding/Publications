#!/usr/bin/env python3
"""Numerically compare a new run to the archived revised analyses.

Tolerance is explicit: rtol=1e-6, atol=1e-8. NaN locations must agree.
Timings are excluded; strings, booleans, IDs, array shapes and schemas are exact.
The historical Qsafety neural audit is also checked at three-decimal report
precision. Any such variation is retained in the report, not called a strict match.
"""
from pathlib import Path
import argparse,json,math,sys
import numpy as np
import pandas as pd
ROOT=Path(__file__).resolve().parent
SKIP={'seconds','local_fit_verification','not_regenerated'}

def compare(a,b,label='',details=None):
 if details is None:details=[]
 if isinstance(a,dict) and isinstance(b,dict):
  if set(a)!=set(b):details.append({'field':label,'issue':'keys differ'});return details
  for k in a:
   if k not in SKIP:compare(a[k],b[k],label+'/'+k,details)
 elif isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
  if len(a)!=len(b):details.append({'field':label,'issue':'length differs'})
  else:
   for i,(x,y) in enumerate(zip(a,b)):compare(x,y,f'{label}/{i}',details)
 elif isinstance(a,(float,int,np.number)) and isinstance(b,(float,int,np.number)):
  if not np.isclose(a,b,rtol=1e-6,atol=1e-8,equal_nan=True):details.append({'field':label,'reference':float(a),'new':float(b)})
 elif a!=b:details.append({'field':label,'issue':'value differs','reference':str(a),'new':str(b)})
 return details

def arrays(a,b):
 if set(a)!=set(b):return [{'issue':'keys differ','reference':list(a),'new':list(b)}]
 bad=[]
 for k in a:
  x,y=np.asarray(a[k]),np.asarray(b[k])
  if x.shape!=y.shape:bad.append({'field':k,'issue':'shape differs'});continue
  if x.dtype.kind in 'fcui' and y.dtype.kind in 'fcui':
   if not np.allclose(x,y,rtol=1e-6,atol=1e-8,equal_nan=True):
    m=np.isfinite(x)&np.isfinite(y);bad.append({'field':k,'issue':'numeric difference','max_abs_diff':float(np.max(np.abs(x[m]-y[m]))) if m.any() else None})
  elif not np.array_equal(x,y):bad.append({'field':k,'issue':'value differs'})
 return bad

def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('run_dir',type=Path);args=a.parse_args();run=args.run_dir.resolve();ref=ROOT/'reference/revised/output'
 files=list(sorted(ref.glob('*.json')))+list(sorted(ref.glob('*.npz')))+list(sorted(ref.glob('*.csv')))
 files += [ref/f'step2_cv_{s}/cv_predictions.npz' for s in ['tap300','multi75']]
 report=[]
 for p in files:
  rel=p.relative_to(ref);q=run/'output'/rel
  if not q.exists():diff=[{'issue':'missing output'}]
  elif p.suffix=='.json':diff=compare(json.loads(p.read_text()),json.loads(q.read_text()))
  elif p.suffix=='.npz':
   with np.load(p,allow_pickle=False) as x,np.load(q,allow_pickle=False) as y:diff=arrays(x,y)
  else:
   x,y=pd.read_csv(p),pd.read_csv(q);diff=arrays({k:x[k].to_numpy() for k in x},{k:y[k].to_numpy() for k in y})
  historical_rounding = bool(diff) and str(rel)=='audit_summary.json' and all(
   d.get('field','').startswith(('/qsafety_force/submitted_corrected/','/qsafety_force/target_lines_permuted/'))
   and isinstance(d.get('reference'),float) and isinstance(d.get('new'),float)
   and round(d['reference'],3)==round(d['new'],3) for d in diff)
  report.append({'path':str(rel),'passed':not diff or historical_rounding,'strict_match':not diff,
                 'historical_audit_matches_three_decimal_reporting':historical_rounding,'differences':diff})
 for name in ['alscn_split_manifest.csv','grating_split_manifest.csv']:
  p=ROOT/'splits'/name;q=run/'release_R1/splits'/name
  if not q.exists():diff=[{'issue':'missing split manifest'}]
  else:
   x,y=pd.read_csv(p),pd.read_csv(q);diff=arrays({k:x[k].to_numpy() for k in x},{k:y[k].to_numpy() for k in y})
  report.append({'path':'splits/'+name,'passed':not diff,'differences':diff})
 out={'rtol':1e-6,'atol':1e-8,'passed':all(r['passed'] for r in report),'comparisons':report}
 (run/'numerical_comparison.json').write_text(json.dumps(out,indent=2)+'\n')
 print(json.dumps({'passed':out['passed'],'files_checked':len(report),'failed':[r['path'] for r in report if not r['passed']], 'reported_variation':[r['path'] for r in report if r.get('historical_audit_matches_three_decimal_reporting')]},indent=2))
 return 0 if out['passed'] else 1
if __name__=='__main__':sys.exit(main())
