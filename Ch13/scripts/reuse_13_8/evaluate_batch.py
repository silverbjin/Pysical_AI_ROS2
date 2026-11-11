"""Prepare/run/report a fixed schedule. Failures consume slots; no retries."""
import argparse,csv,hashlib,json,os,shutil,subprocess,sys,time
from pathlib import Path
from ch13_system_validation.batch import make_plan,assess_batch
from ch13_system_validation.scenarios import get_scenario
from ch13_system_validation.criteria import PROFILES


def write(path,value):
    with path.open('x',encoding='utf-8') as stream:stream.write(json.dumps(value,indent=2,allow_nan=False)+'\n')


def main():
    ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['prepare','run','report'])
    ap.add_argument('--repo-root',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--batch',type=Path,required=True);ap.add_argument('--case-root',type=Path,required=True)
    ap.add_argument('--criteria-profile',choices=tuple(PROFILES),
                    help='Prepare default: education_v1; run/report must match the frozen plan')
    args=ap.parse_args();root=args.repo_root.resolve();batch=args.batch.resolve();cases=args.case_root.resolve()
    digest=hashlib.sha256(args.manifest.read_bytes()).hexdigest()
    subprocess.run([sys.executable,str(root/'Ch13/scripts/reuse_13_8/freeze_runtime.py'),'verify',str(args.manifest)],check=True)
    if args.mode=='prepare':
        if batch.exists():raise ValueError('new batch directory required')
        if shutil.disk_usage(cases).free<10*1024**3:raise ValueError('at least10GiB evidence space required')
        batch.mkdir(parents=True)
        hashes={name:hashlib.sha256((json.dumps(get_scenario(name).record(),sort_keys=True,indent=2)+'\n').encode()).hexdigest()
                for name in ('level2_obstacles','level3_house')}
        plan=make_plan(digest,hashes,criteria_profile=args.criteria_profile or 'education_v1')
        if any((cases/s['uuid']).exists() for s in plan['slots']):raise ValueError('UUID collision')
        write(batch/'plan.json',plan);print(json.dumps(plan));return 0
    plan=json.loads((batch/'plan.json').read_text());assert plan['source_manifest_sha256']==digest
    assess_batch(plan,[])  # validate the exact immutable schema before launch
    criteria_profile=plan.get('criteria',{}).get('profile','book_v1')
    if args.criteria_profile is not None and args.criteria_profile!=criteria_profile:
        raise ValueError('criteria cannot be changed after the schedule is frozen')
    if args.mode=='run':
        for slot in plan['slots']:
            journal=batch/('attempt_%02d.json'%slot['index']);folder=cases/slot['uuid']
            if journal.exists() or folder.exists():raise ValueError('attempt already used; never replace a slot')
            before=batch/('before_%02d.json'%slot['index'])
            subprocess.run(['/usr/bin/python3',str(root/'Ch13/scripts/reuse_13_5/inspect_r2_residuals.py'),str(before)],check=True)
            record=dict(slot=slot,start_wall=time.monotonic(),state='STARTED')
            write(journal,record)
            environment=dict(os.environ,CH13_REUSE_STARTUP_TRACE=str(folder/'startup_trace'))
            with (batch/('attempt_%02d.log'%slot['index'])).open('x') as log:
                process=subprocess.run([sys.executable,'-u',str(root/'Ch13/scripts/reuse_13_8/run_mission.py'),
                    '--repo-root',str(root),'--manifest',str(args.manifest),'--evidence',str(folder),
                    '--scenario',slot['scenario'],'--criteria-profile',criteria_profile,'--auto-start'],cwd=root,env=environment,stdout=log,stderr=subprocess.STDOUT)
            write(batch/('exit_%02d.json'%slot['index']),dict(returncode=process.returncode,end_wall=time.monotonic()))
            print('ATTEMPT_FINISHED',slot['index'],slot['scenario'],slot['uuid'],'exit',process.returncode,flush=True)
            subprocess.run(['/usr/bin/python3',str(root/'Ch13/scripts/reuse_13_5/inspect_r2_residuals.py'),
                str(batch/('after_%02d.json'%slot['index']))],check=True)
    trials=[]
    for slot in plan['slots']:
        path=cases/slot['uuid']/'trial.json'
        if path.exists():trials.append(json.loads(path.read_text()))
    verdict=assess_batch(plan,trials);write(batch/'evaluation.json',verdict)
    with (batch/'trials.csv').open('x',newline='',encoding='utf-8') as stream:
        fields=['index','scenario','uuid','started','complete','success','sim_s','wall_s','position_error_m','max_tilt_rad','cpu_percent']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for slot in plan['slots']:
            trial=next((r for r in trials if r['uuid']==slot['uuid']),{})
            writer.writerow(dict(index=slot['index'],scenario=slot['scenario'],uuid=slot['uuid'],
                started=(batch/('attempt_%02d.json'%slot['index'])).exists(),
                **{k:trial.get(k) for k in fields[4:]}))
    print(json.dumps(verdict,indent=2));return 0 if verdict['result']=='PASS' else 1


if __name__=='__main__':sys.exit(main())
