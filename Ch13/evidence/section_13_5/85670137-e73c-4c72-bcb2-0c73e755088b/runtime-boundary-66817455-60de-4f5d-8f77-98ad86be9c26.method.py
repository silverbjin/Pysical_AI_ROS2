"""Closed current G1/C1 clock and scheduler intervals, no acceptance override."""
import hashlib,json,uuid
from pathlib import Path
base=Path('Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b')
names=['native-g1-gazebo-835a4a4c-e7f7-4a1e-9935-7714af541143',
 'native-contact-component-gazebo-76838bec-808d-4199-afd1-8c01589486fb']
out=dict(scope='runtime_clock_and_owned_thread_diagnostic_not_physical_acceptance',trials=[])
for name in names:
 d=base/name;path=d/'process_metrics.jsonl';rows=[json.loads(s) for s in path.read_text().splitlines()]
 report=json.loads((d/'controller_report.json').read_bytes());fault=report['first_fault'];pivot=None if not fault else fault['wall_ns']
 intervals=[];samples=[];before={};probe=[]
 for r in rows:
  snapshot={}
  for p in r['members']:
   t=p.get('thread_work')
   if not t:continue
   probe.append({k:t[k] for k in ('collection_wall_ns','collection_raw_ns','collection_thread_ns','truncated','unavailable_threads')})
   for thread in t['threads']:
    key=(p['pid'],p['start_ticks'],thread['tid'],thread['start_ticks'])
    snapshot[key]=(thread,p['executable'])
  if before:
   prior=before['row'];rawlo=r['raw_before_ns']-prior['raw_after_ns'];rawhi=r['raw_after_ns']-prior['raw_before_ns'];dt=r['wall_ns']-prior['wall_ns']
   if rawlo<=0 or rawhi<=0:raise RuntimeError('invalid original raw bracket')
   actors=[]
   for key,(t,exe) in snapshot.items():
    if key not in before['threads']:continue
    old=before['threads'][key][0];cpu=t['runtime_ns']-old['runtime_ns'];wait=t['runqueue_wait_ns']-old['runqueue_wait_ns']
    actors.append(dict(pid=key[0],tid=t['tid'],name=t['name'],runtime_ms=cpu/1e6,
     runqueue_ms=wait/1e6,executable=exe))
   interval=dict(start_wall_ns=prior['wall_ns'],end_wall_ns=r['wall_ns'],raw_s=(rawlo+rawhi)/2e9,
    mono_s=dt/1e9,mono_raw_ratio_interval=[dt/rawhi,dt/rawlo],
    actors=sorted(actors,key=lambda v:-v['runtime_ms'])[:10],
    largest_runqueue=sorted(actors,key=lambda v:-v['runqueue_ms'])[:5])
   intervals.append(interval)
  before=dict(row=r,threads=snapshot)
 selected=intervals if pivot is None else [r for r in intervals if r['end_wall_ns']>=pivot-3_000_000_000 and r['start_wall_ns']<=pivot+500_000_000]
 entry=dict(trial=name,first_fault=None if not fault else dict(reason=fault['reason'],wall_ns=pivot,ros_ns=fault['ros_ns']),
  sample_count=len(rows),min_mono_raw_ratio=min(r['mono_raw_ratio_interval'][0] for r in intervals),
  max_mono_raw_ratio=max(r['mono_raw_ratio_interval'][1] for r in intervals),
  maximum_probe_wall_ms=max(r['collection_wall_ns'] for r in probe)/1e6,
  maximum_probe_cpu_ms=max(r['collection_thread_ns'] for r in probe)/1e6,
  truncated_count=sum(r['truncated'] for r in probe),unavailable_threads=sum(r['unavailable_threads'] for r in probe),
  selected_intervals=selected,source_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in (path,d/'controller_report.json')})
 out['trials'].append(entry)
target=base/('runtime-boundary-'+str(uuid.uuid4())+'.json')
with target.open('x') as stream:json.dump(out,stream,indent=2)
target.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes())
print(json.dumps(dict(path=str(target),trials=[{k:v for k,v in r.items() if k not in ('source_sha256','selected_intervals')} for r in out['trials']]),indent=2))
