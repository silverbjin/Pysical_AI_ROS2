"""Freeze runtime/script bytes and criteria before final physical scenarios."""
from pathlib import Path
import hashlib,json,subprocess,sys
root=Path(__file__).resolve().parents[3];out=Path(sys.argv[1])
assert not out.exists(),'a frozen revision is immutable; use a new filename'
paths=[]
for base in [root/'Ch13/ros2_ws/src/ch13_navigation_reuse',root/'Ch13/ros2_ws/src/ch13_reuse_wire',root/'Ch13/scripts/reuse_13_5']:
 paths += [p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
paths+=[root/'Ch13/dependencies/section_13_5_edu_stop_v2.json']
paths += [root/'Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision'/n for n in ['__init__.py','contracts.py','geometry.py']]
row=lambda p:{'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
f={'revision':out.stem,'scope':'MuJoCo corrected A, educational single execution per required scenario','source_head_before_freeze':subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),'files':[row(p) for p in sorted(set(paths))],'scenarios':['free','obstacle','blocked','cancel','vision','raw_loss'],'vision_inference_wall_hz':15,'camera_capture_cap_wall_hz':15,'scan_cap_wall_hz':10,'native_joint_soft_tolerance_rad':.02,'arrival_position_m':.1,'arrival_yaw_rad':.1,'physical_stop_gate':'section_13_5_edu_stop_v2','stop_deadline_wall_s':8,'stop_deadline_sim_s':5,'raw_expiry_zero_wall_s':.35,'nav_budget_sim_s':90,'nav_budget_wall_s':240,'blocked_goal':[2.25,0,0],'blocked_goal_cell':'free; full corridor barrier separates start and destination','iterations_per_scenario':1,'three_repetitions':'extension, not claimed','upstream_lock_files':json.loads((root/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())['files']}
out.write_text(json.dumps(f,indent=2)+'\n');print('FROZEN',len(f['files']),'source/script files')
