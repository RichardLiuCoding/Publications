#!/usr/bin/env python3
"""Check release checksums without importing scientific libraries or reading pickle files."""
from pathlib import Path
import argparse,hashlib,json,sys
ROOT=Path(__file__).resolve().parent

def sha(path):
 h=hashlib.sha256()
 with path.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def main():
 a=argparse.ArgumentParser(description=__doc__);a.add_argument('--part',choices=['all','code','data'],default='all');args=a.parse_args()
 manifest=ROOT/('MANIFEST.sha256' if args.part=='all' else f'MANIFEST_{args.part}.sha256')
 missing=[];changed=[];n=0
 for line in manifest.read_text().splitlines():
  expected,rel=line.split('  ',1);p=ROOT/rel;n+=1
  if not p.is_file():missing.append(rel)
  elif sha(p)!=expected:changed.append(rel)
 result={'part':args.part,'checked':n,'missing':missing,'changed':changed,'passed':not(missing or changed)}
 print(json.dumps(result,indent=2));return 0 if result['passed'] else 1
if __name__=='__main__':sys.exit(main())
