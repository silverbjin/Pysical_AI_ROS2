"""Run the frozen matrix sequentially; never retry failures or overlap engines."""
from pathlib import Path
import argparse,hashlib,json,os,subprocess,sys,uuid
root=Path(__file__).resolve().parents[3];scripts=root/'Ch13/scripts/reuse_13_5'
def frozen(f):
 for asset in f['upstream_lock_files']:
  p=root.parent/'upstream-iit-locomanipulation-d010212'/asset['path'];assert p.stat().st_size==asset['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==asset['sha256'],asset['path']
 for row in f['files']:
  p=root/row['path'];assert p.stat().st_size==row['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],row['path']
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);ap.add_argument('--out',required=True);args=ap.parse_args();f=json.loads(Path(args.freeze).read_text());out=Path(args.out);assert not out.exists(),'new matrix directory required';out.mkdir(parents=True)
 matrix={'freeze':str(Path(args.freeze).resolve()),'freeze_sha256':hashlib.sha256(Path(args.freeze).read_bytes()).hexdigest(),'cases':[],'result':'IN_PROGRESS'}
 for case in f['scenarios']:
  frozen(f);run=root/'Ch13/evidence/section_13_5_reuse'/str(uuid.uuid4());runlog=out/(case+'.log')
  with runlog.open('w') as log:
   code=subprocess.call(['bash',str(scripts/'run_navigation.sh'),case,str(run),str(f['vision_inference_wall_hz'])],stdout=log,stderr=subprocess.STDOUT)
  frozen(f)
  # The driver always recovers its launch group, also on a failed assertion.
  post=subprocess.call(['bash',str(scripts/'env_r2.sh'),str(scripts/'inspect_r2_residuals.py'),str(run/'residual_processes.json')],stdout=subprocess.DEVNULL)
  subprocess.check_call([sys.executable,str(scripts/'write_run_report.py'),str(run)])
  matrix['cases'].append({'case':case,'uuid':run.name,'exit_code':code,'post_cleanup_exit_code':post});(out/'matrix.json').write_text(json.dumps(matrix,indent=2)+'\n');print(case,run.name,code,'cleanup',post,flush=True)
  if post:break
 matrix['result']='PASS' if len(matrix['cases'])==len(f['scenarios']) and all(c['exit_code']==0 and c['post_cleanup_exit_code']==0 for c in matrix['cases']) else 'FAIL';(out/'matrix.json').write_text(json.dumps(matrix,indent=2)+'\n')
 return subprocess.call([sys.executable,str(scripts/'verify_acceptance.py'),str(args.freeze),str(out)])
if __name__=='__main__':sys.exit(main())
