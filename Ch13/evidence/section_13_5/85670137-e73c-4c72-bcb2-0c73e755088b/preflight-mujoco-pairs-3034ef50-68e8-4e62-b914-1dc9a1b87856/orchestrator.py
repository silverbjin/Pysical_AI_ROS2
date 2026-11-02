"""One bounded clock admission, then fixed-source serial G1/G2 pairs.

Predeclared independent acceptance runs, never retries: first failure stops.
No next engine before normal reap, residual inspection and archive verification.
The parent keeps this same WSL boot alive without a background keepalive daemon.
"""
import argparse,hashlib,json,os,subprocess,sys,threading,time,uuid
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('--seed-g1-result',required=True)
parser.add_argument('--pairs',type=int,choices=(1,3),default=3)
args=parser.parse_args();repo=Path.cwd().resolve()
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
task=repo/'.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO'
root=base/('preflight-mujoco-pairs-'+str(uuid.uuid4()));root.mkdir()
(root/'orchestrator.py').write_bytes(Path(__file__).read_bytes())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
record=dict(scope='predeclared_fixed_source_serial_mujoco_G1_G2_acceptance_not_section_completion',
    pid=os.getpid(),uid=os.getuid(),boot_id=boot,required_pairs=args.pairs,
    seed_g1_result=str(Path(args.seed_g1_result).resolve()),commands=[],attempts=[],passed=False,
    first_failure_stops=True,changes_system_settings=False,concurrent_engines=False)
def save():(root/'session.json').write_text(json.dumps(record,indent=2))
def invoke(command):
    record['commands'].append(command);save()
    return subprocess.run(command).returncode
def fail(reason):
    record['failure']=reason;save();raise SystemExit(reason)
save();print(json.dumps(dict(session=str(root),required_pairs=args.pairs,boot_id=boot)),flush=True)
preflight=root/'preflight'
if invoke([sys.executable,'Ch13/scripts/check_system_clock_13_5.py','--output-dir',str(preflight)]):
    fail('clock preflight failed: no engine attempt; no retry')
admission=json.loads((preflight/'result.json').read_text())
if not admission['passed'] or not admission['same_boot']:fail('clock admission unconfirmed')

# Diagnose the previous WAIT_CARRY test failure under recorded original clocks.
# This observer exists only during CPU/RPC verification and joins before engines.
stop=threading.Event();clock_changes=[];counter=[0];observer_errors=[]
def observe_verification_clock():
    previous=None
    try:
        with (root/'verification_clock.jsonl').open('x') as out:
            while not stop.is_set():
                a=time.monotonic_ns();system=time.time_ns();b=time.monotonic_ns()
                row=dict(wall_before_ns=a,system_ns=system,wall_after_ns=b,
                    offset_ns=system-(a+b)//2)
                if previous is not None and abs(row['offset_ns']-previous['offset_ns'])>1_000_000:
                    clock_changes.append(dict(wall_ns=a,offset_delta_ns=row['offset_ns']-previous['offset_ns']))
                out.write(json.dumps(row)+'\n');counter[0]+=1;previous=row
                stop.wait(.02)
    except BaseException as error:observer_errors.append(repr(error))
thread=threading.Thread(target=observe_verification_clock,name='preflight_verification_clock')
thread.start()
tests='Ch13/ros2_ws/src/integrated_robot_navigation/test/'
label='task8-stable-clock-startup-'+root.name.removeprefix('preflight-mujoco-pairs-')
command=['bash',str(task/'check-native.sh'),label,
    tests+'test_shutdown_lifecycle_state_ros.py',tests+'test_runtime_shutdown_order.py',
    tests+'test_carry_startup.py','-W','error']
try:
    environment=dict(os.environ,CH13_TEST_DOMAIN_ID='221')
    record['commands'].append(command);save()
    verified=subprocess.run(command,env=environment).returncode
finally:
    stop.set();thread.join(timeout=2.)
record['verification']=dict(returncode=verified,clock_samples=counter[0],
    clock_changes=clock_changes,observer_joined=not thread.is_alive(),observer_errors=observer_errors,
    label=label,scope='CPU_RPC_verification_only_not_engine_acceptance')
save()
if verified or thread.is_alive() or observer_errors or clock_changes:
    fail('verification or original clock stability failed: no engine attempt; no retry')

fixed=None
def trial(kind,proof):
    global fixed
    prefix='native-'+kind+'-mujoco-'
    before={p.name for p in base.glob(prefix+'*') if p.is_dir() and not p.name.endswith('-prepared')}
    if kind=='g1':
        command=[sys.executable,str(task/'native-output-g1-mujoco.py'),'--control-clock-mode','relay100',
            '--seed-g1-result',str(proof)]
    else:command=[sys.executable,str(task/'native-output-g2.py'),'--g1-result',str(proof)]
    code=invoke(command)
    after=[p for p in base.glob(prefix+'*') if p.is_dir() and not p.name.endswith('-prepared') and p.name not in before]
    if len(after)!=1:fail('completed trial missing/ambiguous; ownership unconfirmed; no next engine')
    output=after[0];result=json.loads((output/'result.json').read_text())
    closed=json.loads((output/'teardown.json').read_text())
    manifest=json.loads((output/'source_manifest.json').read_text())
    if not closed['parent_reaped'] or closed['residual_live_pids']:
        fail('owned cleanup unconfirmed; no next engine')
    archive='task8-preflight-pair-'+output.name.removeprefix('native-')
    if invoke([sys.executable,str(task/'freeze-current-trial.py'),output.name,archive]):
        fail('source/archive checkpoint failed; no next engine')
    if fixed is None:fixed=manifest
    same_source=manifest['head']==fixed['head'] and manifest['files']==fixed['files']
    passed=(code==0 and result['status']=='PASS' and same_source
        and all(result['checks'].get(name) is True for name in result['required_checks'])
        and closed['runtime_exit'] and closed['engine_exit'] and not closed['forced_cleanup']
        and closed.get('journal_writer_joined') is True)
    record['attempts'].append(dict(trial=output.name,status=result['status'],admitted=passed,
        required_checks=result['required_checks'],source_manifest_sha256=hashlib.sha256((output/'source_manifest.json').read_bytes()).hexdigest(),
        result_sha256=hashlib.sha256((output/'result.json').read_bytes()).hexdigest(),
        runtime_exit=closed['runtime_exit'],engine_exit=closed['engine_exit'],
        forced_cleanup=closed['forced_cleanup'],residual=closed['residual_live_pids'],archive=archive+'.json'))
    save()
    if not passed:fail('first failed acceptance retained: series stopped, no retry/next engine')
    return output/'result.json'

for number in range(1,args.pairs+1):
    if boot!=Path('/proc/sys/kernel/random/boot_id').read_text().strip():fail('WSL boot identity changed')
    record['pair_in_progress']=number;save()
    g1=trial('g1',args.seed_g1_result)
    trial('g2',g1)
record['passed']=True;record['pair_in_progress']=None;save()
print(json.dumps(dict(session=str(root),passed=True,pairs=args.pairs)),flush=True)
