"""Read-only replacement baseline after interruption; old lease stays unchanged."""
import hashlib,json,os,shutil,subprocess,uuid
from pathlib import Path
from distro_session import DistroSession

repo=Path.cwd().resolve();task=Path(__file__).resolve().parent
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
old=base/'clock-single-owner-f2289ad9-c1dc-4e7c-a631-17c7be96aa69'
lease=json.loads((old/'lease.json').read_text());state=json.loads((old/'session.json').read_text())
boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
assert os.getuid()==1000 and boot!=lease['initial_clock']['boot_id']

def owned():
    result=[]
    for p in Path('/proc').glob('[0-9]*'):
        try:
            if p.stat().st_uid!=os.getuid():continue
            cmd=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
            if any(s in cmd for s in ('/install/integrated_robot_','Ch13/scripts/run_navigation_13_5.py',
                '/temporary-clock-session.py','/run-preflight-native-pairs.py','/native-output-g1.py',
                '/native-output-g2.py','gz sim ','gz-sim-server')):
                result.append(dict(pid=int(p.name),command=cmd))
        except OSError:pass
    return result

assert not owned(),'runtime still present; no replacement baseline allowed'
out=base/('recovery-f228-'+str(uuid.uuid4()));out.mkdir()
original_hashes={n:hashlib.sha256((old/n).read_bytes()).hexdigest() for n in ('lease.json','session.json')}
report=dict(scope=__doc__,old_boot=lease['initial_clock']['boot_id'],new_boot=boot,
    old_normal_close_confirmed=False,old_restoration_acknowledged=state['restored'],
    old_validation_exit=state['validation_exit'],old_metadata_sha256=original_hashes,
    settings_changed=False,owned_before=[],sessions={},errors=[])
def save():(out/'result.json').write_text(json.dumps(report,indent=2))
sessions={}
try:
    for distro in ('Ubuntu-22.04','Ubuntu-24.04'):
        session=DistroSession(['/mnt/c/Windows/System32/wsl.exe','-d',distro,'-u','jinho','--','python3'],
            label=distro.replace('.','-'),directory=out)
        sessions[distro]=session;snapshot=session.inspect();expected=lease['initial_services'][distro]
        report['sessions'][distro]=dict(snapshot=snapshot,
            baseline_matches=all(snapshot[k]==expected[k] for k in ('active','enabled')))
        save()
except BaseException as error:report['errors'].append(repr(error))
finally:
    for distro,session in reversed(tuple(sessions.items())):
        try:session.close()
        except BaseException as error:report['errors'].append(repr(error))
        report['sessions'].setdefault(distro,{})['foreground']=session.report();save()
report['owned_after']=owned()
report['old_metadata_unchanged']=all(hashlib.sha256((old/n).read_bytes()).hexdigest()==h
    for n,h in original_hashes.items())
report['replacement_baseline_confirmed']=(len(sessions)==2 and not report['errors']
    and not report['owned_after'] and report['old_metadata_unchanged']
    and all(v['baseline_matches'] and v['foreground']['close_acknowledged']
        and v['foreground']['joined'] and v['foreground']['returncode']==0 for v in report['sessions'].values()))
report['head']=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
report['candidate_sources']={}
for relative in ('Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/gait.py',
    'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/reference_envelope.py',
    'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/contact_transfer.py',
    'Ch13/ros2_ws/src/integrated_robot_navigation/integrated_robot_navigation/crawl_controller.py',
    'Ch13/scripts/run_navigation_13_5.py'):
    report['candidate_sources'][relative]=hashlib.sha256((repo/relative).read_bytes()).hexdigest()
for name in ('lease.json','session.json'):shutil.copyfile(old/name,out/('original-'+name))
for name in ('recover-interrupted-f228.py','distro_session.py'):shutil.copyfile(task/name,out/name)
save()
print(json.dumps(dict(output=str(out),replacement_baseline_confirmed=report['replacement_baseline_confirmed'],
    old_normal_close_confirmed=False,old_metadata_unchanged=report['old_metadata_unchanged'],
    settings_changed=False,errors=report['errors'],services={k:{s:v['snapshot'][s] for s in ('active','enabled')}
        for k,v in report['sessions'].items()})),flush=True)
if not report['replacement_baseline_confirmed']:raise SystemExit(1)
