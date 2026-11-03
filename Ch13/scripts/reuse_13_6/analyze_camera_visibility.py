"""Offline sensor-placement geometry. Old evidence is NEVER motion authority."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import mujoco
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation
from ch13_navigation_reuse.scene import make_model,OPTICAL_R
from ch13_manipulation_reuse.model import TCP_LINK6


def analyze(folder):
    root=Path(__file__).resolve().parents[3];run=Path(folder)/'run'
    mission=json.loads((run/'pick_mission.json').read_text())
    phase=next(r['clock_ns']/1e9 for r in mission['stages'] if r.get('phase')=='PRE_GRASP')
    rows=[json.loads(line) for line in (run/'engine_observations.jsonl').read_text().splitlines()]
    initial=min(rows,key=lambda r:abs(r['sim_s']-phase))['qpos'][:27]
    observations=[json.loads(line) for line in (run/'vision_observations.jsonl').read_text().splitlines()]
    observed=min(observations,key=lambda r:abs(r['capture_ns']/1e9-phase));center=np.array(observed['point'])
    model=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision');data=mujoco.MjData(model)
    q=np.array(initial);link=model.body('link6').id;base=model.body('base').id
    plans=[r['trajectory']['joint_trajectory'] for r in mission['planning'] if r['kind']=='plan' and r['error_code']==1]
    plan=min(plans,key=lambda r:r['points'][-1]['time_from_start']['sec']+r['points'][-1]['time_from_start']['nanosec']/1e9)
    names=plan['joint_names'];states=[]
    for point in plan['points'][::10]+[plan['points'][-1]]:
        state=q.copy();state[19:25]=[point['positions'][names.index('joint'+str(i))] for i in range(1,7)];states.append(state)
    data.qpos[:]=states[-1];mujoco.mj_kinematics(model,data);desired_R=data.xmat[link].reshape(3,3).copy()
    limits=model.jnt_range[[model.joint('joint'+str(i)).id for i in range(1,7)]];proposals=[]
    for dz in (0.,.12):
        target=center+[0.,0.,dz]
        def residual(angles):
            data.qpos[19:25]=angles;mujoco.mj_kinematics(model,data);R=data.xmat[link].reshape(3,3)
            tcp=data.xpos[link]+R@TCP_LINK6
            return np.r_[tcp-target,.2*Rotation.from_matrix(desired_R.T@R).as_rotvec()]
        solved=least_squares(residual,states[-1][19:25],bounds=(limits[:,0]+1e-6,limits[:,1]-1e-6),max_nfev=100)
        error=float(np.linalg.norm(residual(solved.x)))
        proposals.append(dict(tcp_lift_m=dz,residual=error,offline_only=True))
        if error<.002:
            state=q.copy();state[19:25]=solved.x;states.append(state)
    group=np.ones(6,dtype=np.uint8);group[2]=group[5]=0;cal=observed['calibration'];results=[]
    for lateral,yaw_deg in ((0.,0.),(.15,0.),(.25,-20.),(.30,-25.)):
        worst_span=1.;worst_fraction=1.;inside=True;worst_index=None
        for index,state in enumerate(states):
            data.qpos[:]=state;mujoco.mj_kinematics(model,data);Rbody=data.xmat[base].reshape(3,3)
            camera=data.xpos[base]+Rbody@np.array([.4,lateral,.25])
            Ropt=Rbody@Rotation.from_euler('z',yaw_deg,degrees=True).as_matrix()@OPTICAL_R
            target=center.copy()
            if index==len(states)-1 and proposals[-1]['residual']<.002:target[2]+=.12
            heading=np.arctan2(camera[1]-target[1],camera[0]-target[0]);visible=[];total=0
            for z in np.linspace(-.036,.036,5):
                for angle in heading+np.array([-.5,0.,.5]):
                    point=target+np.array([.02*np.cos(angle),.02*np.sin(angle),z])
                    optical=Ropt.T@(point-camera)
                    u=cal[0]*optical[0]/optical[2]+cal[2];v=cal[1]*optical[1]/optical[2]+cal[3]
                    inside=inside and optical[2]>0 and 1<=u<=318 and 1<=v<=238
                    direction=point-camera;distance=np.linalg.norm(direction);geomid=np.array([-1],dtype=np.int32)
                    hit=mujoco.mj_ray(model,data,camera,direction/distance,group,1,-1,geomid)
                    total+=1
                    if hit<0 or hit>=distance-.002:visible.append(z)
            span=(max(visible)-min(visible))/.08 if visible else 0.
            if span<worst_span:worst_span=span;worst_index=index
            worst_fraction=min(worst_fraction,len(visible)/total)
        results.append(dict(camera_base_m=[.4,lateral,.25],yaw_deg=yaw_deg,minimum_visible_height_span=worst_span,
                            minimum_visible_surface_fraction=worst_fraction,all_sampled_surfaces_in_image=bool(inside),worst_state=worst_index,
                            qualifies=bool(inside and worst_span>=.75)))
    return dict(scope='offline prior robot trace and vision point; NOT live permission or collision plan',
                source=str(run),source_plan_sha256=hashlib.sha256((run/'pick_mission.json').read_bytes()).hexdigest(),
                target_source_capture_ns=observed['capture_ns'],states=len(states),offline_ik_checks=proposals,candidates=results)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('evidence');parser.add_argument('--output',type=Path,required=True);args=parser.parse_args()
    result=analyze(args.evidence);args.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
