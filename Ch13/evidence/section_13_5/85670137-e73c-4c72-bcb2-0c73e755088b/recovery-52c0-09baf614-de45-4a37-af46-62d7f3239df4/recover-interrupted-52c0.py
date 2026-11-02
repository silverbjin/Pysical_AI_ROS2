"""Read-only new-instance baseline; never retarget or close the old lease."""
import hashlib,json,os,shutil,time,uuid
from datetime import datetime,timezone
from pathlib import Path
from distro_session import DistroSession

repo=Path.cwd().resolve();task=Path(__file__).resolve().parent
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
old=base/'clock-single-owner-52c0f3cd-a4b2-4656-861c-9ac1263866fa'
lease=json.loads((old/'lease.json').read_text());state=json.loads((old/'session.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
old_boot=lease['initial_clock']['boot_id']
assert os.getuid()==1000 and boot!=old_boot,'old kernel still present; use its original ownership protocol'
def owned():
    values=[]
    for path in Path('/proc').glob('[0-9]*'):
        try:
            if path.stat().st_uid!=os.getuid():continue
            command=(path/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if any(key in command for key in ('/install/integrated_robot_','Ch13/scripts/run_navigation_13_5.py',
                '/temporary-clock-session.py','/run-preflight-mujoco-pairs.py','/native-output-g2.py')):
                values.append(dict(pid=int(path.name),command=command))
        except OSError:pass
    return values
assert not owned(),'a Ch13 runtime exists; do not start or mutate another instance'
out=base/('recovery-52c0-'+str(uuid.uuid4()));out.mkdir()
report=dict(scope=__doc__,observed_utc=datetime.now(timezone.utc).isoformat(),
    old_boot=old_boot,new_boot=boot,old_kernel_ended=True,old_normal_close_confirmed=False,
    old_restoration_acknowledged=state['restored'],old_metadata_unchanged=True,
    changes_services_clock_or_system_settings=False,owned_before=[],sessions={},errors=[])
def save():(out/'result.json').write_text(json.dumps(report,indent=2))
sessions={}
try:
    for distro in ('Ubuntu-22.04','Ubuntu-24.04'):
        sessions[distro]=DistroSession(['/mnt/c/Windows/System32/wsl.exe','-d',distro,'-u','jinho','--','python3'],
            label=distro.replace('.','-'),directory=out)
        snapshot=sessions[distro].inspect();expected=lease['initial_services'][distro]
        report['sessions'][distro]=dict(snapshot=snapshot,
            baseline_matches=all(snapshot[key]==expected[key] for key in ('active','enabled')))
        save()
except BaseException as error:report['errors'].append(repr(error))
finally:
    for distro,session in reversed(tuple(sessions.items())):
        try:session.close()
        except BaseException as error:report['errors'].append(repr(error))
        report['sessions'].setdefault(distro,{})['foreground']=session.report();save()
report['owned_after']=owned()
report['replacement_baseline_confirmed']=(len(sessions)==2 and not report['errors'] and not report['owned_after']
    and all(v.get('baseline_matches') and v['foreground']['close_acknowledged'] for v in report['sessions'].values()))
trial=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/native-g2-mujoco-b7cedb29-78b9-46a9-97c9-67872775443f')
v=json.loads((trial/'result.json').read_text());report['interrupted_trial']=dict(path=str(trial),
    original_status=v['status'],original_phase=v.get('phase'),normal_teardown_exists=(trial/'teardown.json').exists(),
    derived_status='INTERRUPTED_ENVIRONMENT',counts_as_success=False)
snapshot=out/'source_snapshot'
manifest=json.loads((trial/'source_manifest.json').read_text());report['source_manifest_sha256']=hashlib.sha256((trial/'source_manifest.json').read_bytes()).hexdigest()
for relative,expected in manifest['files'].items():
    path=repo/relative;assert hashlib.sha256(path.read_bytes()).hexdigest()==expected,relative
    target=snapshot/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,target)
report['source_files_preserved']=len(manifest['files'])
for name in ('result.json','source_manifest.json','install_manifest.json','validated_profile.json'):
    path=trial/name
    if path.exists():shutil.copyfile(path,out/('original-'+name))
report['partial_raw']=[]
for name in ('observations.cdr','native_command_trace.bin'):
    path=trial/name
    if not path.exists():continue
    digest=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(4*1024*1024),b''):digest.update(block)
    report['partial_raw'].append(dict(path=str(path),bytes=path.stat().st_size,sha256=digest.hexdigest(),
        not_a_normal_closed_recording=True))
for name in ('recover-interrupted-52c0.py','distro_session.py'):
    shutil.copyfile(task/name,out/name)
save();print(json.dumps(dict(output=str(out),**{k:v for k,v in report.items() if k!='sessions'}),indent=2))
if not report['replacement_baseline_confirmed']:raise SystemExit(1)
