#!/usr/bin/env python3
"""Run the packaged revision analyses without modifying archived inputs or reference results."""
from pathlib import Path
import argparse,datetime,json,os,subprocess,sys,time
ROOT=Path(__file__).resolve().parent

def main():
    a=argparse.ArgumentParser(description=__doc__)
    a.add_argument('--stage',choices=['fd','bundles','audit','benchmark','mechanism','learning','grating','encoder-tap300','encoder-multi75','invariance','splits','figures','tables','legacy-figures','all'],default='all')
    a.add_argument('--run-dir',type=Path,default=ROOT/'runs/latest')
    a.add_argument('--verify-local',type=int,default=3)
    args=a.parse_args();run=args.run_dir.resolve()
    for p in [run/'output',run/'figures',run/'logs',run/'manuscript']:p.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update(DTSPM_RUN_DIR=str(run),OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MPLBACKEND='Agg',PYTHONHASHSEED='0')
    tasks={'fd':['rv_build_fd.py'],'bundles':['rv_build_bundles.py','--verify-local',str(args.verify_local)],'audit':['rv_audit.py'],'benchmark':['rv_run_tap300.py'],'mechanism':['rv_mechanism.py'],'learning':['rv_learning_curve.py'],'grating':['rv_grating.py'],'encoder-tap300':['rv_step2_cv.py','tap300'],'encoder-multi75':['rv_step2_cv.py','multi75'],'invariance':['rv_invariance_test.py'],'splits':['rv_manifests.py'],'figures':['rv_figures.py','fig3','fig4','fig5','fig6','fig7','si'],'tables':['rv_si_tables.py'],'legacy-figures':['rv_legacy_figures.py']}
    results=[]
    for stage in (list(tasks) if args.stage=='all' else [args.stage]):
        command=[sys.executable,str(ROOT/'revision_2026-09/codes'/tasks[stage][0]),*tasks[stage][1:]]
        print('Running',stage,flush=True);t=time.time()
        with (run/'logs'/f'{stage}.log').open('w') as log:
            p=subprocess.run(command,cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT)
        result={'stage':stage,'command':['python',*tasks[stage]],'exit_code':p.returncode,'seconds':round(time.time()-t,3),'completed_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
        (run/'logs'/f'{stage}.json').write_text(json.dumps(result,indent=2)+'\n');results.append(result)
        print(stage,'exit',p.returncode,'seconds',result['seconds'],flush=True)
        if p.returncode:raise SystemExit(f'{stage} failed; inspect {run / "logs" / (stage + ".log")}')
    (run/'run_summary.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':main()
