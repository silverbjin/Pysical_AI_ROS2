"""Closed original trace: legacy encoding versus proposed measured-rate gate.

Offline decision support ONLY. No acceptance result or current gate changes.
"""
import hashlib,json,sys,uuid
from pathlib import Path
root=Path(sys.argv[1]);base=root.parent
path=root/'original-clocks.jsonl'
rows=[r for line in path.open() if 'monotonic_ns' in (r:=json.loads(line))]
bad=[];groups=[];deviations=[]
for i,r in enumerate(rows):
    decoded=(r['tick_us']-10000)*100+r['freq_scaled_ppm']/65536
    deviations.append(decoded)
    if r['tick_us']!=10000 and (r['tick_us'] not in (9999,10001) or abs(decoded)>2):
        bad.append(i)
        if not groups or groups[-1][-1]+1!=i:groups.append([])
        groups[-1].append(i)
rates=[];j=0
for i,r in enumerate(rows):
    while j+1<i and r['raw_before_ns']-rows[j+1]['raw_after_ns']>=1_000_000_000:j+=1
    a=rows[j]
    if r['raw_before_ns']-a['raw_after_ns']<1_000_000_000:continue
    delta=r['monotonic_ns']-a['monotonic_ns']
    low=delta/(r['raw_after_ns']-a['raw_before_ns'])
    high=delta/(r['raw_before_ns']-a['raw_after_ns'])
    rates.append((low,high))
legacy=json.loads((root/'continuous-clock-result.json').read_text())
cross=json.loads((root/'cross-clock-result.json').read_text())
out=dict(scope='offline_comparison_only_original_FAIL_preserved_no_gate_change',root=root.name,
 method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
 input_sha256={name:hashlib.sha256((root/name).read_bytes()).hexdigest() for name in
     ('original-clocks.jsonl','continuous-clock-result.json','cross-clock-result.json','session.json')},
 legacy_passed=legacy['passed'],samples=len(rows),legacy_invalid_encodings=len(bad),
 unsupported_tick_count=sum(r['tick_us'] not in (9999,10000,10001) for r in rows),
 correction_ppm_min=min(deviations),correction_ppm_max=max(deviations),
 bad_groups=[dict(samples=len(g),raw_start_ns=rows[g[0]]['raw_before_ns'],
     raw_end_ns=rows[g[-1]]['raw_after_ns'],observed_span_s=(rows[g[-1]]['raw_after_ns']-rows[g[0]]['raw_before_ns'])/1e9,
     correction_ppm_min=min(deviations[i] for i in g),correction_ppm_max=max(deviations[i] for i in g)) for g in groups],
 proposed_continuous_measured_rate=dict(window_min_ns=1_000_000_000,observations=len(rates),
     minimum_lower_ratio=min(v[0] for v in rates),maximum_upper_ratio=max(v[1] for v in rates),
     original_ratio_limit=[.999,1.001],failed_windows=sum(not .999<=lo<=hi<=1.001 for lo,hi in rates)),
 realtime_steps=legacy['steps'],host_cross_clock=cross,
 decision='Approval required to replace added2ppm metadata requirement with continuous actual0.1percent rate; no new engine or PASS is minted.')
target=base/('task8-clock-witness-comparison-'+str(uuid.uuid4())+'.json')
target.write_text(json.dumps(out,indent=2));target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),samples=out['samples'],bad_groups=out['bad_groups'],
 rate=out['proposed_continuous_measured_rate'],legacy_passed=out['legacy_passed']),indent=2))
