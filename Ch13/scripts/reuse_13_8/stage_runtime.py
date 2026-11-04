"""Prepare a hash-verified native source snapshot before launching a mission."""
import argparse,json,os,subprocess,sys
from pathlib import Path
root=Path(__file__).resolve().parents[3]
from ch13_system_validation.runtime_staging import stage_runtime


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);ap.add_argument('--repo-root',type=Path,default=root)
    ap.add_argument('--build',default=os.environ.get('CH13_REUSE_BUILD','/home/jinho/ch13_reuse_13_8_build'))
    args=ap.parse_args()
    if args.output.exists():raise ValueError('new staging report output required')
    result=stage_runtime(args.repo_root,args.manifest,args.build);runtime=Path(result['runtime_root'])
    subprocess.run([sys.executable,str(runtime/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),
        'verify',str(runtime/result['manifest_relative_path'])],cwd=runtime,check=True)
    result['runtime_source_verified']=True;args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x') as output:output.write(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
