"""Approved temporary service-only comparison; all validation runs as jinho.

No disable/mask, clock write, configuration change, driver or Windows admin.
The restoration marker remains on any uncatchable parent termination.
"""
import hashlib,json,os,signal,subprocess,sys,time,uuid
from pathlib import Path

repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2')
task=repo/'.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO'
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
service='systemd-timesyncd.service'
assert os.geteuid()==0 and Path.cwd().resolve()==repo and base.is_dir()
root=base/('timesync-comparison-'+str(uuid.uuid4()))
subprocess.run(['runuser','-u','jinho','--','mkdir','--',str(root)],check=True)
assert root.stat().st_uid==1000

def inspect(arguments):
    p=subprocess.run(['systemctl',*arguments,service],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    return dict(command=['systemctl',*arguments,service],returncode=p.returncode,output=p.stdout.strip())

initial=inspect(['is-active']);enabled=inspect(['is-enabled'])
record=dict(scope='user_approved_temporary_timesyncd_comparison_not_engine_acceptance',
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),pid=os.getpid(),uid=os.getuid(),
    validation_uid=1000,initial_active=initial,initial_enabled=enabled,
    restoration_pending=False,restored=False,child_returncode=None,
    source_hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in
        (Path(__file__),task/'timesync-comparison-user.sh')})
for source in (Path(__file__),task/'timesync-comparison-user.sh'):
    (root/source.name).write_bytes(source.read_bytes())
def save():(root/'service-lifecycle.json').write_text(json.dumps(record,indent=2))
def interrupted(signum,frame):raise SystemExit('interrupted: '+str(signum))
signal.signal(signal.SIGTERM,interrupted)
signal.signal(signal.SIGINT,interrupted)
save();print(json.dumps(dict(service_comparison=str(root),initial=initial,enabled=enabled)),flush=True)
assert initial['output']=='active', 'unexpected initial state; no service change'
seed='/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/native-g1-mujoco-9d296bc8-1f99-494a-83f4-2bfc0bdc3751/result.json'
try:
    record['restoration_pending']=True;save()
    record['stop']=inspect(['stop']);record['during']=inspect(['is-active']);save()
    assert record['stop']['returncode']==0 and record['during']['output']=='inactive'
    command=['runuser','-u','jinho','--','bash',str(task/'timesync-comparison-user.sh'),str(root),seed]
    record['validation_command']=command;save()
    record['child_returncode']=subprocess.run(command).returncode;save()
finally:
    record['restore']=inspect(['start']);record['final_active']=inspect(['is-active'])
    record['final_enabled']=inspect(['is-enabled'])
    record['restored']=(record['restore']['returncode']==0
        and record['final_active']['output']==initial['output']
        and record['final_enabled']['output']==enabled['output'])
    record['restoration_pending']=not record['restored'];save()
    print(json.dumps(dict(service_comparison=str(root),restored=record['restored'],
        child_returncode=record['child_returncode'])),flush=True)
assert record['restored'], 'service restoration unconfirmed; user attention required'
raise SystemExit(record['child_returncode'] if record['child_returncode'] is not None else 1)
