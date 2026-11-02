"""One explicit migration of the two owned evidence roots; no recursive delete."""
import argparse,hashlib,importlib.util,json,os,sys,time,uuid
from pathlib import Path

repo=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('retention',repo/'Ch13/scripts/evidence_retention_13_5.py')
retention=importlib.util.module_from_spec(spec);spec.loader.exec_module(retention)
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
parser=argparse.ArgumentParser();parser.add_argument('--apply-plan');parser.add_argument('--refresh-plan');args=parser.parse_args()


def no_live_engine():
    for path in Path('/proc').iterdir():
        if not path.name.isdigit():continue
        try:raw=(path/'cmdline').read_bytes().split(b'\0');exe=Path(os.fsdecode(raw[0])).name
        except (OSError,IndexError):continue
        if exe in ('mujoco_ros2_control','navigation_evidence_recorder','gz','gz-sim-server') or (
                exe.startswith('python') and any(b'run_navigation_13_5.py' in arg for arg in raw[1:])):
            raise RuntimeError('live engine/runtime; retention prohibited: '+path.name)


def closed(root):
    try:
        result=json.loads((root/'result.json').read_text());end=json.loads((root/'teardown.json').read_text())
        return result,end
    except (OSError,ValueError):return None,None


def make_plan():
    no_live_engine();trials={};skipped=[]
    for evidence in (base,native):
        for root in sorted(evidence.glob('native-g[12]-*')):
            if not root.is_dir() or root.name.endswith('-prepared'):continue
            result,end=closed(root)
            if not result or end.get('parent_reaped') is not True or end.get('residual_live_pids')!=[]:
                skipped.append(dict(path=str(root),reason='closed cleanup not confirmed'));continue
            key=(result.get('engine'),result.get('gate'),result.get('status'))
            if key[0] not in ('mujoco','gazebo') or key[1] not in ('G1','G2') or key[2] not in ('PASS','FAIL'):continue
            item=trials.setdefault(root.name,dict(name=root.name,key=key,paths=[],rank=0))
            item['paths'].append(str(root))
            # The actual native file is authoritative; a later export must not
            # make an older experiment look newer than its original.
            rank=(root/'result.json').stat().st_mtime_ns
            if evidence==native or not item['rank']:item['rank']=rank
    latest={}
    for item in trials.values():
        key=tuple(item['key'])
        if key not in latest or item['rank']>latest[key]['rank']:latest[key]=item
    representatives=sorted(item['name'] for item in latest.values())
    selected=[];raw_bytes=0
    for item in trials.values():
        item['representative']=item['name'] in representatives
        for name in item['paths']:
            root=Path(name);size=sum(path.stat().st_size for path in root.rglob('*')
                if path.is_file() and not path.is_symlink() and retention.bulk(path.name,path.stat().st_size))
            selected.append(dict(root=name,representative=item['representative'],raw_bytes=size))
            if not item['representative']:raw_bytes+=size
    archives=[]
    for path in sorted(base.glob('*.zip')):
        if path.name.endswith('.metadata.zip'):continue
        ledger=path.with_suffix('.json');trial=None
        if ledger.exists():
            try:trial=json.loads(ledger.read_text()).get('trial')
            except (ValueError,AttributeError):pass
        archives.append(dict(path=str(path),trial=trial,representative=trial in representatives,
            bytes=path.stat().st_size,parts=[str(p) for p in sorted(base.glob(path.name+'.part*'))]))
    result=dict(schema=1,id=str(uuid.uuid4()),created_system_ns=time.time_ns(),roots=[str(base),str(native)],
        rule='latest_closed_per_engine_gate_outcome',representatives=representatives,trials=selected,
        skipped=skipped,archives=archives,raw_reclaimable_bytes=raw_bytes,
        source_policy_sha256=retention.digest(repo/'Ch13/docs/EVIDENCE_RETENTION_POLICY_KO.md'),
        tool_sha256=retention.digest(repo/'Ch13/scripts/evidence_retention_13_5.py'))
    target=base/('retention-plan-'+result['id']+'.json');retention.save(target,result)
    print(json.dumps(dict(plan=str(target),representatives=representatives,trial_copies=len(selected),
        skipped=len(skipped),archives=len(archives),raw_reclaimable_bytes=raw_bytes),indent=2),flush=True)


def apply(plan_path):
    no_live_engine();plan_path=retention.bounded(plan_path,base)
    plan=json.loads(plan_path.read_text())
    if plan['roots']!=[str(base),str(native)]:raise RuntimeError('unapproved roots')
    if plan['tool_sha256']!=retention.digest(repo/'Ch13/scripts/evidence_retention_13_5.py'):
        raise RuntimeError('tool changed after plan; regenerate')
    record=dict(id=str(uuid.uuid4()),plan=str(plan_path),started_system_ns=time.time_ns(),
        state='running',trials=[],archives=[],errors=[])
    target=base/('retention-application-'+record['id']+'.json');retention.save(target,record)
    for item in plan['trials']:
        no_live_engine();root=Path(item['root']);allowed=base if root.is_relative_to(base) else native
        try:
            result=retention.compact_trial(root,allowed_root=allowed,representative=item['representative'])
            record['trials'].append(dict(root=str(root),representative=item['representative'],
                removed_bytes=result['removed_bytes'],marker=str(root/'retention.json')))
            print('TRIAL',root.name,'KEEP' if item['representative'] else result['removed_bytes'],flush=True)
        except Exception as error:
            record['errors'].append(dict(path=str(root),error=repr(error)));retention.save(target,record);raise
        retention.save(target,record)
    for item in plan['archives']:
        no_live_engine();path=retention.bounded(item['path'],base)
        parts=[retention.bounded(part,base) for part in item['parts']]
        original_sha=retention.digest(path);part_records=[];combined=hashlib.sha256()
        for part in parts:
            sha=hashlib.sha256()
            with part.open('rb') as source:
                for block in iter(lambda:source.read(4*retention.MIB),b''):sha.update(block);combined.update(block)
            part_records.append(dict(path=str(part),size=part.stat().st_size,sha256=sha.hexdigest()))
        if parts and combined.hexdigest()!=original_sha:raise RuntimeError('parts differ; no deletion')
        if item['representative']:
            if not parts:continue
            value=dict(path=str(path),original_bytes=path.stat().st_size,original_sha256=original_sha,
                reason='representative whole ZIP cache duplicates verified retained parts',parts=part_records)
            record['archives'].append(value);retention.save(target,record)
            path.unlink();value['whole_zip_removed']=True
        else:
            value=retention.compact_archive(path,allowed_root=base)
            value['parts']=part_records;record['archives'].append(value);retention.save(target,record)
            for part,row in zip(parts,part_records):
                if retention.digest(part)!=row['sha256']:raise RuntimeError('part changed before deletion')
                part.unlink();row['removed']=True;retention.save(target,record)
        retention.save(target,record)
        print('ARCHIVE',path.name,flush=True)
    record['state']='complete';record['finished_system_ns']=time.time_ns();retention.save(target,record)
    print(json.dumps(dict(application=str(target),state=record['state'],trials=len(record['trials']),
        archives=len(record['archives']),errors=record['errors'])),flush=True)


if args.refresh_plan:
    old=retention.bounded(args.refresh_plan,base);value=json.loads(old.read_text())
    value['previous_plan']=str(old);value['id']=str(uuid.uuid4());value['created_system_ns']=time.time_ns()
    value['tool_sha256']=retention.digest(repo/'Ch13/scripts/evidence_retention_13_5.py')
    value['source_policy_sha256']=retention.digest(repo/'Ch13/docs/EVIDENCE_RETENTION_POLICY_KO.md')
    target=base/('retention-plan-'+value['id']+'.json');retention.save(target,value)
    print(str(target),flush=True)
elif args.apply_plan:apply(args.apply_plan)
else:make_plan()
