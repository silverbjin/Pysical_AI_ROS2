"""Replay only the failed plan's math, without an engine or ROS motion."""
import json
import sys
import time
from pathlib import Path
root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Ch13/ros2_ws/src/ch13_manipulation_reuse'))
from ch13_manipulation_reuse.retime import normalize_points
from ch13_manipulation_reuse.trajectory import Trajectory
data=json.loads((Path(sys.argv[1]) if len(sys.argv)>1 else root/'Ch13/evidence/section_13_6_reuse/63bcc5a6-e00f-4d3b-96f2-cf0a9c553d9b/run/moveit_probe.json').read_text());data['records']=data.get('records',data.get('planning',[]))
msg=[r for r in data['records'] if r['kind']=='plan'][-1]['trajectory']['joint_trajectory']
points=[dict(time=p['time_from_start']['sec']+p['time_from_start']['nanosec']/1e9,
             positions=p['positions'],velocities=p['velocities'],accelerations=p['accelerations']) for p in msg['points']]
limits=[[-2.618,2.618],[0,3.14],[-2.697,0],[-1.832,1.832],[-1.22,1.22],[-3.14,3.14]]
start=time.monotonic();prepared,scale=normalize_points(msg['joint_names'],points,points[0]['positions'],limits)
normalized=time.monotonic();path=Trajectory.from_points(tuple(msg['joint_names']),prepared,points[0]['positions'],limits)
finished=time.monotonic()
print(json.dumps(dict(points=len(points),retime_wall_s=normalized-start,admission_wall_s=finished-normalized,
                      scale=scale,duration_sim_s=path.duration),indent=2))
