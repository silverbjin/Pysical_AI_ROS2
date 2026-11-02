"""Counterfactual read-only gate replay; never rewrites an original failure."""
import json,hashlib
from pathlib import Path
import clock_convergence as module
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
source=base/'clock-single-owner-280ff810-a986-441b-91d3-e41470052afa/convergence.jsonl'
rows=[json.loads(line) for line in source.read_text().splitlines()]
original=module.nominal_tick_encoding
def symmetric(tick,freq_scaled_ppm=None,*,allow_compensated=False):
    return original(tick,freq_scaled_ppm,allow_compensated=allow_compensated) or (
        allow_compensated is True and type(tick) is int and tick==10001
        and type(freq_scaled_ppm) is int and abs(freq_scaled_ppm+100*65536)<=2*65536)
results=[]
for name,policy in (('original',original),('proposed_symmetric_read_only',symmetric)):
    module.nominal_tick_encoding=policy
    gate=module.ClockConvergence(deadline_ns=300_000_000_000,allow_compensated_tick=True)
    for index,row in enumerate(rows):
        clock=row['clock'];raw=(row['raw_before_ns']+row['raw_after_ns'])//2
        state=gate.observe(raw,row['mono_ns'],row['real_ns'],clock['tick_us'],freq_scaled_ppm=clock['freq_scaled_ppm'])
        if state!='WAITING':break
    results.append(dict(policy=name,state=state,reason=gate.reason,row=index,
        elapsed_raw_s=(raw-gate.started)/1e9,stable_since=gate.stable_since))
out=dict(scope='counterfactual_replay_no_engine_no_new_live_admission',
    original_recorded_final_state=rows[-1]['state'],results=results,
    input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
    method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
output=base/'task8-clock-upper-encoding-replay-01.json';assert not output.exists();output.write_text(json.dumps(out,indent=2))
method=output.with_suffix('.method.py');assert not method.exists();method.write_bytes(Path(__file__).read_bytes())
print(json.dumps(out,indent=2))
