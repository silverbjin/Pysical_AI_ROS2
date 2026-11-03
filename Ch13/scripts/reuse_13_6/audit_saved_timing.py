"""Replay saved successful MoveIt outputs without ROS nodes or an engine.

This proves timing feasibility only; it grants no live execution permission.
"""
import argparse,hashlib,json,sys
from pathlib import Path
import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Ch13/ros2_ws/src/ch13_manipulation_reuse'))
from ch13_manipulation_reuse.retime import normalize_points

LIMITS=[[-2.618,2.618],[0.,3.14],[-2.697,0.],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]]


def audit(path):
    data=json.loads(path.read_text());records=data.get('planning',data.get('records',[]))
    digest=hashlib.sha256(path.read_bytes()).hexdigest();results=[]
    for index,record in enumerate(records):
        if record.get('kind') not in ('plan','cartesian') or record.get('error_code')!=1:continue
        trajectory=record.get('trajectory',{}).get('joint_trajectory')
        if not trajectory or len(trajectory['points'])<2:continue
        points=[dict(time=p['time_from_start']['sec']+p['time_from_start']['nanosec']/1e9,
                     positions=p['positions'],velocities=p['velocities'],accelerations=p['accelerations']) for p in trajectory['points']]
        row=dict(file=str(path.relative_to(ROOT)),sha256=digest,record=index,kind=record['kind'],
                 raw_duration_sim_s=points[-1]['time'],minimum_interval_sim_s=float(np.diff([p['time'] for p in points]).min()))
        try:
            result,scale=normalize_points(trajectory['joint_names'],points,points[0]['positions'],LIMITS)
            row.update(result='FEASIBLE',scale=scale,duration_sim_s=result[-1]['time'])
        except ValueError as error:row.update(result='REJECTED',reason=str(error))
        results.append(row)
    return results


def main():
    parser=argparse.ArgumentParser();parser.add_argument('output',type=Path);args=parser.parse_args()
    if args.output.exists():raise ValueError('use a new audit output')
    evidence=ROOT/'Ch13/evidence/section_13_6_reuse'
    paths=sorted([*evidence.glob('*/run/moveit_probe.json'),*evidence.glob('*/run/pick_mission.json')])
    rows=[row for path in paths for row in audit(path)]
    data=dict(meaning='offline timing only; recorded start, not live admission or collision/physical acceptance',
              files_scanned=len(paths),trajectories=len(rows),feasible=sum(r['result']=='FEASIBLE' for r in rows),
              rejected=sum(r['result']=='REJECTED' for r in rows),rows=rows)
    args.output.write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps({k:v for k,v in data.items() if k!='rows'},indent=2))


if __name__=='__main__':main()
