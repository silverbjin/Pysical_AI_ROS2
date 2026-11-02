"""Preserve failed manual comparison and read-only managed-clock evidence."""
import base64,hashlib,json,subprocess,uuid
from pathlib import Path
base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
trial=base/'clock-normalization-7f639ebf-9e7b-430b-8126-8b28355e76f3'
out=base/('clock-normalization-analysis-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
origin=None;previous=None;segments=[];ticks=set();steps=[];count=0
with (trial/'original-clocks.jsonl').open() as source:
    for line in source:
        row=json.loads(line)
        if 'tick_us' not in row:continue
        count+=1;ticks.add(row['tick_us'])
        if origin is None:origin=row['raw_before_ns']
        if previous is None or row['tick_us']!=previous['tick_us']:
            segments.append(dict(raw_elapsed_seconds=(row['raw_before_ns']-origin)/1e9,
                tick_us=row['tick_us'],freq_scaled_ppm=row['freq_scaled_ppm']))
        if previous is not None:
            step=(row['realtime_ns']-row['monotonic_ns'])-(previous['realtime_ns']-previous['monotonic_ns'])
            if abs(step)>1_000_000:steps.append(dict(raw_elapsed_seconds=(row['raw_before_ns']-origin)/1e9,step_ns=step))
        previous=row
record=json.loads((trial/'session.json').read_text());lease=json.loads((trial/'lease.json').read_text())
assert record['restored'] and not record['restoration_pending'] and record['validation_exit'] is None
commands=[];wsl='/mnt/c/Windows/System32/wsl.exe'
for args in ([wsl,'--version'],[wsl,'--system','--exec','id'],
             [wsl,'--system','--exec','chronyc','-n','tracking'],
             [wsl,'--system','--exec','chronyc','-n','sources','-v']):
    p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=15)
    encoding='utf-16-le' if p.stdout.count(b'\0')>len(p.stdout)//5 else 'utf-8'
    commands.append(dict(command=args,returncode=p.returncode,stdout=p.stdout.decode(encoding,errors='replace'),
        stdout_base64=base64.b64encode(p.stdout).decode(),stderr=p.stderr.decode(errors='replace')))
report=dict(scope='failed_manual_comparison_and_managed_clock_diagnosis_not_engine_acceptance',
    original_trial=trial.name,original_status='FAIL_host_guest_rate',engine_attempts=0,
    original_clock_samples=count,tick_segments=segments,realtime_steps=steps,
    lease_restored=lease['restored'],tick_restored_before_service_resume=lease['tick_restored'],
    final_tick_after_service_resume=record['final_clock']['tick_us'],
    related_runtime_residual=record['final_related_runtimes'],read_only_commands=commands,
    references=[dict(url='https://github.com/microsoft/WSL/blob/master/src/linux/init/main.cpp',
      blob_sha='4970608d7739a5b5a60ea1c5e11ec83e97099567',scope='concept_not_installed_binary_identity',function='StartTimeSyncAgent'),
      dict(url='https://chrony-project.org/doc/4.6/chrony.conf.html#maxslewrate',default_maxslew_ppm=83333.333)],
    identities={name:hashlib.sha256((trial/name).read_bytes()).hexdigest() for name in
       ('session.json','lease.json','original-clocks.jsonl','cross-clock-result.json')},
    exact_syscall_writer_traced=False,changes_managed_chrony_or_settings=False)
(out/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(output=str(out),samples=count,tick_segments=segments,restored=lease['restored'],
    final_tick_after_services=record['final_clock']['tick_us']),indent=2))
