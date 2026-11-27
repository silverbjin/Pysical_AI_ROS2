"""Actual MuJoCo 1DOF, no ROS motion output and no external assets."""
import argparse,csv,hashlib,json,time
from collections import deque
from pathlib import Path
import numpy as np
import mujoco
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from ch15_simulation.joint_tuner import RealTimeTuner,torque

DT=.005
STEPS=800
FIELDS=('step','sim_s','q_rad','qd_rad_s','ref_rad','requested_nm','clipped_nm','applied_nm','actuator_nm','control_ns')
CASES={'A_underdamped':(25.,.5),'B_tuned':(25.,9.5),'C_overdamped':(25.,18.)}

def summarize(rows):
    a=np.asarray(rows,dtype=float)
    if a.shape!=(STEPS,len(FIELDS)) or not np.isfinite(a).all():
        raise ValueError('missing/nonfinite sample')
    if not np.array_equal(a[:,0],np.arange(1,STEPS+1)) or not np.allclose(a[:,1],np.arange(1,STEPS+1)*DT,rtol=0,atol=1e-10):
        raise ValueError('time/step discontinuity')
    q,t=a[:,2],a[:,1]
    if np.max(np.abs(q))>2.+1e-9 or np.max(np.abs(a[:,6:9]))>60.+1e-9:
        raise ValueError('joint/actuator limit violation')
    if not np.all(a[:,4]==1.) or not np.allclose(a[:,7],a[:,8],atol=1e-9,rtol=0):
        raise ValueError('actuator witness mismatch')
    lo=np.flatnonzero(q>=.1);hi=np.flatnonzero(q>=.9)
    rise=float(t[hi[0]]-t[lo[0]]) if len(lo) and len(hi) and hi[0]>=lo[0] else None
    outside=np.flatnonzero(np.abs(q-1.)>.02)
    settle=float(t[0] if not len(outside) else t[outside[-1]+1]) if not len(outside) or outside[-1]+1<STEPS else None
    return dict(samples=STEPS,sim_s=float(t[-1]),rmse_rad=float(np.sqrt(np.mean((q-1.)**2))),overshoot_pct=float(max(0.,100*(np.max(q)-1.))),rise_s=rise,rise_reason=None if rise is not None else 'threshold_not_reached',settling_s=settle,settling_reason=None if settle is not None else 'not_settled_within_window',last_half_max_abs_error_rad=float(np.max(np.abs(q[-100:]-1.))),peak_abs_q_rad=float(np.max(np.abs(q))),saturation_count=int(np.count_nonzero(a[:,5]!=a[:,6])),control_p50_ns=float(np.percentile(a[:,9],50)),control_p95_ns=float(np.percentile(a[:,9],95)),control_max_ns=int(np.max(a[:,9])),finite=True,limit_violation=0)

def run_case(model_path,out,name,kp,kd,inertia=1.,damping=.5,delay_steps=0):
    original=Path(model_path).read_text()
    xml=original.replace('diaginertia="1 1 1"',f'diaginertia="{inertia} {inertia} {inertia}"').replace('damping=".5"',f'damping="{damping}"')
    model=mujoco.MjModel.from_xml_string(xml)
    data=mujoco.MjData(model)
    mujoco.mj_forward(model,data)
    full=np.zeros((model.nv,model.nv));mujoco.mj_fullM(model,full,data.qM)
    assert model.nq==model.nv==model.nu==1 and abs(full[0,0]-inertia)<=1e-9
    assert abs(model.opt.timestep-DT)<1e-12 and np.all(model.opt.gravity==0)
    assert abs(model.dof_damping[0]-damping)<1e-12 and abs(model.dof_frictionloss[0]-.1)<1e-12
    assert np.array_equal(model.jnt_range[0],[-2.,2.]) and np.array_equal(model.actuator_ctrlrange[0],[-60.,60.])
    assert data.qpos[0]==data.qvel[0]==data.time==0.
    tuner=RealTimeTuner({'kp':kp,'kd':kd})
    queue=deque([0.]*delay_steps)
    rows=[];wall=time.perf_counter_ns()
    with tuner.trial() as gains:
        for step in range(1,STEPS+1):
            start=time.perf_counter_ns()
            raw,clipped=torque(gains,float(data.qpos[0]),float(data.qvel[0]))
            if delay_steps:
                queue.append(clipped);applied=queue.popleft()
            else:applied=clipped
            control_ns=time.perf_counter_ns()-start
            data.ctrl[0]=applied
            mujoco.mj_step(model,data)
            rows.append((step,float(data.time),float(data.qpos[0]),float(data.qvel[0]),1.,raw,clipped,applied,float(data.actuator_force[0]),control_ns))
    metrics=summarize(rows)
    metrics.update(case=name,kp=kp,kd=kd,inertia_kg_m2=float(full[0,0]),damping_nm_s_rad=float(model.dof_damping[0]),frictionloss_nm=float(model.dof_frictionloss[0]),delay_steps=delay_steps,delay_s=delay_steps*DT,initial_q_rad=0.,initial_qd_rad_s=0.,wall_ns=time.perf_counter_ns()-wall,model_sha256=hashlib.sha256(xml.encode()).hexdigest(),original_model_sha256=hashlib.sha256(original.encode()).hexdigest(),engine=mujoco.__version__,source='ACTUAL_MUJOCO')
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    with (out/(name+'.csv')).open('x',newline='') as f:
        w=csv.writer(f);w.writerow(FIELDS);w.writerows(rows)
    (out/(name+'.json')).write_text(json.dumps(metrics,indent=2,allow_nan=False)+'\n')
    return metrics

def plot_cases(out,names,filename):
    out=Path(out);fig,ax=plt.subplots(figsize=(9,4.8))
    for name in names:
        data=np.genfromtxt(out/(name+'.csv'),delimiter=',',names=True)
        ax.plot(data['sim_s'],data['q_rad'],label=name)
    ax.axhline(1.,linestyle='--',label='reference 1 rad')
    ax.set(xlabel='simulation time (s)',ylabel='joint position (rad)');ax.legend();ax.grid(True,alpha=.25);fig.tight_layout()
    fig.savefig(out/filename,dpi=130);plt.close(fig)

def main():
    p=argparse.ArgumentParser();p.add_argument('--model',required=True);p.add_argument('--out',required=True);args=p.parse_args()
    out=Path(args.out);out.mkdir(parents=True,exist_ok=False)
    result={n:run_case(args.model,out,n,*g) for n,g in CASES.items()}
    a,b=result['A_underdamped'],result['B_tuned']
    checks=dict(rmse_improves=b['rmse_rad']<a['rmse_rad'],overshoot_improves=b['overshoot_pct']<a['overshoot_pct'],overshoot_limit=b['overshoot_pct']<=5.,final_error=b['last_half_max_abs_error_rad']<=.02,all_finite_limit=all(x['finite'] and x['limit_violation']==0 and x['samples']==800 for x in result.values()))
    plot_cases(out,list(CASES),'pid.png')
    payload=dict(result='PASS' if all(checks.values()) else 'FAIL',checks=checks,cases=result)
    (out/'pid_summary.json').write_text(json.dumps(payload,indent=2,allow_nan=False)+'\n')
    print(json.dumps(payload));return 0 if all(checks.values()) else 1
if __name__=='__main__':raise SystemExit(main())
