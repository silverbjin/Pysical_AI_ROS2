"""Owned G1 validation; bounded export only after truthful native cleanup."""
import argparse,hashlib,json,os,shutil,subprocess,sys,uuid
from pathlib import Path
from native_engine_plan import g1_plan

parser=argparse.ArgumentParser()
parser.add_argument('--engine',choices=('mujoco','gazebo'),required=True)
parser.add_argument('--control-clock-mode',choices=('native','relay100'),default='native')
parser.add_argument('--observer-backend',choices=('python','native_cdr'),default='native_cdr')
parser.add_argument('--seed-g1-result')
parser.add_argument('--plan-only',action='store_true')
args=parser.parse_args();repo=Path.cwd().resolve()
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b')
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
key=str(uuid.uuid4());name='native-g1-'+args.engine+'-'+key
output=native/'evidence'/name;prepared=output.with_name(name+'-prepared')
destination=base/name;prepared_copy=base/prepared.name
scene=prepared/'scene';profile=prepared/'carry_profile.json'
try:plan=g1_plan(args.engine,output,prepared,scene,profile,args.control_clock_mode,args.observer_backend)
except ValueError as error:parser.error(str(error))
if args.plan_only:
    print(json.dumps(dict(executed=False,child_processes_started=0,native_output=str(output),**plan)))
    raise SystemExit(0)
assert os.getuid()==1000 and native.resolve()==native and native.stat().st_uid==os.getuid()
assert (repo/'Ch13').is_dir() and not any(p.exists() for p in (output,prepared,destination,prepared_copy))
if args.seed_g1_result:
    seed_path=Path(args.seed_g1_result).resolve(strict=True)
    seed=json.loads(seed_path.read_text());closed=json.loads((seed_path.parent/'teardown.json').read_text())
    assert seed['engine']==args.engine and seed['gate']=='G1' and seed['status']=='PASS'
    assert all(seed['checks'].get(name) is True for name in seed['required_checks'])
    assert closed['parent_reaped'] and not closed['forced_cleanup'] and not closed['residual_live_pids']
    assert seed['scene'].get('position_reference_mode','native')==plan['position_reference_mode']
    assert seed['execution_mode'].get('dart_contact','native')==plan['dart_contact_mode']
    scene=Path(seed['scene']['robot']['path']).resolve(strict=True).parent
    values=[v.split(':=',1)[1] for v in seed['command'] if v.startswith('carry_profile:=')]
    assert len(values)==1;profile=Path(values[0]).resolve(strict=True)
    plan=g1_plan(args.engine,output,prepared,scene,profile,args.control_clock_mode,args.observer_backend)
    plan['prepare_command']=None
driver=native/'evidence'/('g1-driver-'+key+'.log')
print(json.dumps(dict(native_output=str(output),repository_copy=str(destination),prepared=str(prepared),**plan)),flush=True)
with driver.open('x') as stream:
    stream.write(json.dumps(plan)+'\n');stream.flush()
    if plan['prepare_command'] is not None:
        prepared_result=subprocess.run(plan['prepare_command'],stdout=stream,stderr=subprocess.STDOUT)
        if prepared_result.returncode:
            shutil.copyfile(driver,base/('task8-g1-driver-'+key+'.log'))
            raise SystemExit('preparation failed before engine launch; no retry')
    child=subprocess.run(plan['command'],stdout=stream,stderr=subprocess.STDOUT)
result=json.loads((output/'result.json').read_text());closed=json.loads((output/'teardown.json').read_text())
if not closed.get('parent_reaped') or closed.get('residual_live_pids'):
    raise RuntimeError('owned cleanup unconfirmed; no export/next engine')
from archive_native_storage import export_closed,digest
export=export_closed(output,destination,native/'evidence',archive_large=True)
if plan['prepare_command'] is not None:shutil.copytree(prepared,prepared_copy)
shutil.copyfile(driver,base/('task8-g1-driver-'+key+'.log'))
ledger=dict(**export,prepare_command=plan['prepare_command'],command=plan['command'],
    seed_g1_result=args.seed_g1_result,runner_returncode=child.returncode,
    tool_sha256=digest(Path(__file__)),plan_module_sha256=digest(Path(__file__).with_name('native_engine_plan.py')))
(destination/'storage-copy-ledger.json').write_text(json.dumps(ledger,indent=2))
print(json.dumps(dict(path=str(destination),status=result['status'],runner_returncode=child.returncode,
    forced_cleanup=closed['forced_cleanup'],residual=closed['residual_live_pids'])),flush=True)
raise SystemExit(child.returncode)
