"""Locate mission generation, native receipt and engine processing gaps offline."""
import json
import sys
from pathlib import Path


def read(path):return [json.loads(line) for line in path.read_text().splitlines()]


def analyze(path):
    run=Path(path)/'run';beats=read(run/'mission_heartbeats.jsonl');states=read(run/'manipulation_status.jsonl')
    gaps=sorted((dict(gap_s=b['send_wall']-a['send_wall'],previous=a,next=b) for a,b in zip(beats,beats[1:])),key=lambda r:r['gap_s'],reverse=True)
    faults=[r for r in states if r['phase']=='FAULT'];fault=faults[0] if faults else None
    surrounding=[]
    if fault:
        surrounding=[r for r in states if fault['decision_wall']-.5<=r['decision_wall']<=fault['decision_wall']+.1]
    engine=json.loads((run/'engine.json').read_text())
    return dict(first_fault=fault,largest_mission_send_gaps=gaps[:5],status_near_fault=surrounding,
                step_outliers=sorted(engine.get('step_outliers',[]),key=lambda r:r['wall_s'],reverse=True)[:10])


if __name__=='__main__':print(json.dumps(analyze(sys.argv[1]),indent=2))
