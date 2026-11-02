"""Read-only attribution window; never controls a service, clock or distro."""
import hashlib,json,subprocess,uuid
from pathlib import Path

repo=Path.cwd();task=Path(__file__).resolve().parent
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
root=base/('clock-lifetime-'+str(uuid.uuid4()));root.mkdir()
(root/'method.py').write_bytes(Path(__file__).read_bytes())
wsl='/mnt/c/Windows/System32/wsl.exe'
window=['--since','2026-10-28 01:40:00 UTC','--until','2026-10-28 01:50:00 UTC','--no-pager','-o','json']
commands=[];journal=[]
for key,args in (
    ('timesync',['journalctl','-u','systemd-timesyncd.service',*window]),
    ('init',['journalctl','_PID=1','--grep','systemd.*running in system mode|Startup finished',*window])):
    command=[wsl,'-d','Ubuntu-22.04','-u','root','--',*args]
    result=subprocess.run(command,capture_output=True,text=True,timeout=30)
    (root/(key+'.jsonl')).write_text(result.stdout)
    (root/(key+'.stderr')).write_text(result.stderr)
    commands.append(dict(command=command,returncode=result.returncode,
        stdout_sha256=hashlib.sha256(result.stdout.encode()).hexdigest()))
    if result.returncode:raise RuntimeError('read-only journal failed')
    for line in result.stdout.splitlines():
        row=json.loads(line)
        journal.append({field:row.get(field) for field in
            ('__MONOTONIC_TIMESTAMP','__REALTIME_TIMESTAMP','_BOOT_ID','_PID','MESSAGE','UNIT','_SYSTEMD_UNIT')})
source=base/'preflight-mujoco-pairs-da30689e-47cd-491a-96a2-ae66c4f8c5b5/verification_clock.jsonl'
rows=[json.loads(line) for line in source.read_text().splitlines()];steps=[]
for i in range(1,len(rows)):
    previous,current=rows[i-1],rows[i]
    delta=current['offset_ns']-previous['offset_ns']
    if abs(delta)>1_000_000:
        steps.append(dict(delta_ns=delta,before=previous,after=current,
            before_call_span_ns=previous['wall_after_ns']-previous['wall_before_ns'],
            after_call_span_ns=current['wall_after_ns']-current['wall_before_ns']))
value=dict(scope='read_only_service_and_init_journal_correlation_not_syscall_attribution',
    commands=commands,verification_clock_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    steps=steps,journal=journal,mutations=[],boot_expected='e5355f4f0360401c94cc546098ee8e9f')
(root/'result.json').write_text(json.dumps(value,indent=2))
print(json.dumps(dict(path=str(root),steps=steps,journal=journal),indent=2))
