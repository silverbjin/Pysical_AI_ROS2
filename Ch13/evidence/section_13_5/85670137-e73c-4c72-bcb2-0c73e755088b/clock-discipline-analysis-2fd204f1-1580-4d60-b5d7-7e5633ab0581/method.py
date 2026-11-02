"""Compare original QPC-bracketed clocks; read-only evidence, no engine verdict."""
import datetime,hashlib,json,statistics,sys,uuid
from pathlib import Path

base=Path.cwd()/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
guest=base/'clock-discipline-18ba439f-97f6-47aa-bb12-3019199fe70d'
host=base/'host-clock-43de3fba-abf5-4964-8d0e-7e4ba9bd7f67'
cross=base/'clock-cross-boundary-12e96348-4d8d-4475-a9df-1c02f029b8e8'
preflight=base/'preflight-mujoco-pairs-a386ee08-36fa-4d7a-9370-f0b8b6015679/preflight'
out=base/('clock-discipline-analysis-'+str(uuid.uuid4()));out.mkdir()
(out/'method.py').write_bytes(Path(__file__).read_bytes())
def read(path):
    with path.open() as source:return [json.loads(line) for line in source]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
raw=read(guest/'samples.jsonl');assert raw[-1]['kind']=='finished'
g=[r for r in raw if 'raw_before_ns' in r]
assert all(r['modes']==0 and r['errno']==0 for r in g)
def rawmid(r):return (r['raw_before_ns']+r['raw_after_ns'])/2
dur=rawmid(g[-1])-rawmid(g[0])
ratios=[(b['monotonic_ns']-a['monotonic_ns'])/(rawmid(b)-rawmid(a)) for a,b in zip(g,g[1:])]
steps=[dict(raw_ns=b['raw_before_ns'],step_ns=(b['realtime_ns']-b['monotonic_ns'])-(a['realtime_ns']-a['monotonic_ns'])) for a,b in zip(g,g[1:])]
steps=[r for r in steps if abs(r['step_ns'])>1_000_000]
h=read(host/'samples.jsonl');assert json.loads((host/'result.json').read_text())['writes_system_settings'] is False
hc=json.loads((host/'start.json').read_text());freq=hc['stopwatch_frequency']
def utc(s):return datetime.datetime.fromisoformat(s).timestamp()
qpc=lambda r:(r['stopwatch_before']+r['stopwatch_after'])/2/freq
host_ratio=(utc(h[-1]['utc'])-utc(h[0]['utc']))/(qpc(h[-1])-qpc(h[0]))
c=read(cross/'samples.jsonl');assert json.loads((cross/'result.json').read_text())['completed']
assert len({r['guest']['boot_id'] for r in c})==1
cf=json.loads((cross/'start.json').read_text())['qpc_frequency']
lower=(c[-1]['qpc_before']-c[0]['qpc_after'])/cf
upper=(c[-1]['qpc_after']-c[0]['qpc_before'])/cf
cross_rates={}
for key in ('raw_before_ns','monotonic_ns','realtime_ns'):
    delta=(c[-1]['guest'][key]-c[0]['guest'][key])/1e9
    cross_rates[key]=dict(guest_elapsed_seconds=delta,ratio_interval=[delta/upper,delta/lower])
p=read(preflight/'samples.jsonl');ps=[dict(wall_ns=b['wall_before_ns'],offset_delta_ns=b['gate']['last_system_offset_ns']-a['gate']['last_system_offset_ns']) for a,b in zip(p,p[1:]) if abs(b['gate']['last_system_offset_ns']-a['gate']['last_system_offset_ns'])>1_000_000]
report=dict(scope='read_only_clock_diagnosis_not_engine_acceptance',guest_samples=len(g),
    raw_elapsed_seconds=dur/1e9,guest_mono_raw_ratio_median=statistics.median(ratios),
    guest_mono_raw_ratio_total=(g[-1]['monotonic_ns']-g[0]['monotonic_ns'])/dur,
    tick_us=sorted({r['tick_us'] for r in g}),freq_scaled_ppm=sorted({r['freq_scaled_ppm'] for r in g}),
    freq_ppm=sorted({r['freq_scaled_ppm']/65536 for r in g}),guest_realtime_steps=steps,
    host_utc_qpc_ratio=host_ratio,host_elapsed_qpc_seconds=qpc(h[-1])-qpc(h[0]),
    cross_boundary=dict(samples=len(c),host_elapsed_interval_seconds=[lower,upper],rates=cross_rates),
    failed_preflight_steps=ps,boot_id=c[0]['guest']['boot_id'],writes_system_settings=False,
    identities={str(path.relative_to(base)):sha(path) for path in
        [guest/'method.c',guest/'method.sh',guest/'samples.jsonl',host/'samples.jsonl',
         host/'result.json',cross/'method.ps1',cross/'samples.jsonl',cross/'result.json',preflight/'result.json']})
(out/'result.json').write_text(json.dumps(report,indent=2))
print(json.dumps(dict(output=str(out),**{k:v for k,v in report.items() if k!='identities'}),indent=2))
