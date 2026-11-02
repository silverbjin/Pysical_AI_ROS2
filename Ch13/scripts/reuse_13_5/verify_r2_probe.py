"""Independent post-run edu_stop_v2 verification from actual500Hz samples."""
from pathlib import Path
import json,math,sys
import numpy as np,mujoco
root=Path(__file__).resolve().parents[3];out=Path(sys.argv[1]);g=json.loads((root/'Ch13/dependencies/section_13_5_edu_stop_v2.json').read_text(encoding='utf-8-sig'))
a=[json.loads(x) for x in (out/'last_stop_500hz.jsonl').read_text().splitlines()]
last=a[-1]
# Both values are minimum durations. Slow simulation extends wall waiting;
# it must not fail an otherwise stationary educational example merely for RTF.
anchor=max(i for i,r in enumerate(a) if last['wall']-r['wall']>=g['window_wall_s'] and last['sim_s']-r['sim_s']>=g['minimum_window_sim_s'])
w=a[anchor:];q=np.array([r['qpos'] for r in w]);v=np.array([r['qvel'] for r in w]);dt=np.diff([r['sim_s'] for r in w]);assert np.all(dt>0)
rms=lambda z:np.sqrt(np.sum(z[1:]**2*dt[:,None],axis=0)/sum(dt))
yaw=np.unwrap(np.arctan2(2*(q[:,3]*q[:,6]+q[:,4]*q[:,5]),1-2*(q[:,5]**2+q[:,6]**2)))
model=mujoco.MjModel.from_xml_path(str(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'))
limited=model.jnt_limited.astype(bool)&(model.jnt_type==mujoco.mjtJoint.mjJNT_HINGE);values=q[:,model.jnt_qposadr[limited]];bounds=model.jnt_range[limited]
m={'planar_rms_speed_mps':float(np.linalg.norm(rms(v[:,:2]))),'yaw_rate_rms_radps':float(rms(v[:,5:6])[0]),'planar_excursion_m':float(np.max(np.linalg.norm(q[:,:2]-q[0,:2],axis=1))),'yaw_excursion_rad':float(max(abs(yaw-yaw[0]))),'arm_joint_rms_speed_radps':float(max(rms(v[:,18:24]))),'arm_joint_excursion_rad':float(max(np.ptp(q[:,19:25],axis=0))),'arm_joint_target_error_rad':float(np.max(abs(q[:,19:25]-np.array([r['arm_target'] for r in w])))),'max_stop_tilt_rad':float(max(np.arccos(np.clip(1-2*(q[:,4]**2+q[:,5]**2),-1,1)))),'joint_limit_soft_tolerance_rad':float(max(0,np.max(bounds[:,0]-values),np.max(values-bounds[:,1])))}
checks={k:m[k]<=g[k]+1e-10 for k in m};checks['zero_command']=all(r['vx']==0 and r['wz']==0 for r in w);checks['unique_samples']=len(w)>=g['minimum_unique_samples']
s=json.loads((out/'probe_summary.json').read_text());checks['physical_motion']=s['forward_distance_m']>.15;checks['latch']=s['gateway_final']['mode']=='FAULT';checks['rx_join']=s['engine']['rx_joined'];checks['owned_processes_reaped_normal']=all(p['reaped'] and p['exit_code']==0 for p in s['children'])
checks['probe_pass']=s['result']=='PASS'
checks['normal_engine_shutdown']=s['engine']['result']=='COMPLETED' and s['engine']['normal_shutdown_requested']
checks['upstream_threads_join']=s['engine']['upstream_threads_joined']
if 'turn_angle_rad' in s:checks['physical_turn']=s['turn_angle_rad']>.15
if 'launch_children_pids' in s:checks['launch_lifetime']=len(s['launch_children_pids'])==3 and s['launch_clean_exits']==3 and not s['launch_remaining_pids']
result={'gate_revision':g['revision'],'window_selection':'latest start satisfying BOTH minimum wall and simulation durations, not an RTF gate','wall_span_s':last['wall']-w[0]['wall'],'sim_span_s':last['sim_s']-w[0]['sim_s'],'unique_samples':len(w),'metrics':m,'checks':checks,'result':'PASS' if all(checks.values()) else 'FAIL'}
(out/'edu_stop_verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2));assert result['result']=='PASS'
