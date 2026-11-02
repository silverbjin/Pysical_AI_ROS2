"""Two real foreground user sessions, read-only services, original clock untouched."""
import hashlib,json,os,time,uuid
from pathlib import Path
from distro_session import DistroSession

repo=Path.cwd();task=Path(__file__).resolve().parent
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
root=base/('distro-sessions-'+str(uuid.uuid4()));root.mkdir();sessions={}
record=dict(scope='unprivileged_foreground_lifetime_only_no_service_or_clock_changes',commands=[],samples=[],errors=[],passed=False)
for name in ('smoke-distro-sessions.py','distro_session.py'):(root/name).write_bytes((task/name).read_bytes())
def save():(root/'result.json').write_text(json.dumps(record,indent=2))
try:
    for distro in ('Ubuntu-22.04','Ubuntu-24.04'):
        prefix=['/mnt/c/Windows/System32/wsl.exe','-d',distro,'-u','jinho','--','python3']
        sessions[distro]=DistroSession(prefix,label=distro.replace('.','-'),directory=root)
        record['commands'].append(sessions[distro].command);save()
    started=time.monotonic()
    for index in range(8):
        while time.monotonic()-started<index*10:time.sleep(.05)
        sample=dict(elapsed_wall_s=time.monotonic()-started,
            sessions={d:s.inspect() for d,s in sessions.items()})
        record['samples'].append(sample);save()
    initial=record['samples'][0]['sessions'];last=record['samples'][-1]['sessions']
    if any((last[d]['active'],last[d]['enabled'])!=(initial[d]['active'],initial[d]['enabled']) for d in initial):
        raise RuntimeError('externally changed service state')
except BaseException as error:record['errors'].append(repr(error))
finally:
    for distro,session in reversed(tuple(sessions.items())):
        try:session.close()
        except BaseException as error:record['errors'].append(repr(error))
    record['sessions']={d:s.report() for d,s in sessions.items()}
    record['passed']=len(record['samples'])==8 and not record['errors'] and all(
        s['joined'] and s['returncode']==0 and s['close_acknowledged'] for s in record['sessions'].values())
    save()
print(json.dumps(dict(path=str(root),passed=record['passed'],errors=record['errors']),indent=2))
raise SystemExit(0 if record['passed'] else 1)
