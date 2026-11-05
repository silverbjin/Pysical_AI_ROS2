"""Post-exit only: correlate actual owner publication gaps with its GC events."""
import json
import sys
from pathlib import Path
case=Path(sys.argv[1])
assert (case/'trial.json').exists(), 'completed trial required'
output=case/'owner_deadline_analysis_v22.json'
assert not output.exists(), 'preserve prior analysis'
beats=[json.loads(line) for line in (case/'mission_heartbeats.jsonl').read_text().splitlines() if line]
gc=json.loads((case/'owner_gc_timing.json').read_text())
gaps=[]
for a,b in zip(beats,beats[1:]):
    start,end=a['send_wall'],b['send_wall']
    overlaps=[dict(**event,overlap_s=max(0.,min(end,event['end_wall'])-max(start,event['start_wall'])))
              for event in gc['events'] if event['start_wall']<end and event['end_wall']>start]
    gaps.append(dict(from_sequence=a['sequence'],to_sequence=b['sequence'],start_wall=start,end_wall=end,
        wall_s=end-start,stamp_advance_ns=b['stamp_ns']-a['stamp_ns'],gc_overlaps=overlaps))
report=dict(scope='post-exit owner producer timing; correlation is not proof of causation',
    beat_count=len(beats),gaps_over_250ms=sum(g['wall_s']>.25 for g in gaps),
    gaps_over_300ms=sum(g['wall_s']>.3 for g in gaps),largest_gaps=sorted(gaps,key=lambda g:g['wall_s'],reverse=True)[:8],
    gc_policy_changed=gc['policy_changed'],gc_counts=gc['counts'],
    largest_gc=sorted(gc['events'],key=lambda e:e['wall_s'],reverse=True)[:8])
output.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))