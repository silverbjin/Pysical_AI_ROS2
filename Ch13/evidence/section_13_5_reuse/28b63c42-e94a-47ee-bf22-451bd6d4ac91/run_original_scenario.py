"""R1 experiment: invoke original class/loop with input replay and read-only telemetry."""
import builtins,hashlib,json,math,os,sys,time,traceback,threading
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[3]
UP=ROOT.parent/'upstream-iit-locomanipulation-d010212'
sys.dont_write_bytecode=True
sys.path.insert(0,str(UP/'deploy'))
SPEC=json.loads((HERE/'probe_spec.json').read_text(encoding='utf-8-sig'))
LOCK=json.loads((ROOT/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text(encoding='utf-8'))
for f in LOCK['files']:
    if hashlib.sha256((UP/f['path']).read_bytes()).hexdigest()!=f['sha256']:
        raise RuntimeError('upstream hash mismatch: '+f['path'])
import numpy as np
import play_mujoco as upstream
builtins.input=lambda *args:'closeConsole'
p=None
rows=[]
started=time.monotonic()
summary={'revision':SPEC['revision'],'pid':os.getpid(),'ppid':os.getppid(),'result':'ERROR','upstream_hashes_before':'PASS'}
try:
    p=upstream.PlayMujoco()
    sys.path.insert(0,str(ROOT/"Ch13/scripts/reuse_13_5"))
    from reproduce_upstream import freeze_arm_reference
    freeze_arm_reference(p)
    original_viewer=p.viewer
    original_step=upstream.mujoco.mj_step
    started=time.monotonic()
    wall_limit=SPEC['probe_limits_not_final_acceptance']['wall_timeout_s']
    phases=SPEC['schedule_sim_s']
    limits=SPEC['probe_limits_not_final_acceptance']
    class BoundedViewer:
        def __getattr__(self,name):return getattr(original_viewer,name)
        def is_running(self):
            if time.monotonic()-started>wall_limit:raise TimeoutError('R1 wall deadline')
            return p.mjData.time<phases[-1]['until'] and original_viewer.is_running()
    p.viewer=BoundedViewer()
    step_count=0
    def observe_step(model,data,*args,**kwargs):
        global step_count
        command=[float(p.ref_base_lin_vel_H[0]),float(p.ref_base_lin_vel_H[1]),float(p.ref_base_ang_yaw_dot)]
        original_step(model,data,*args,**kwargs)
        step_count+=1
        if not np.isfinite(data.qpos).all() or not np.isfinite(data.qvel).all():raise RuntimeError('nonfinite engine state')
        tilt=math.acos(float(np.clip(1-2*(data.qpos[4]**2+data.qpos[5]**2),-1,1)))
        if data.qpos[2]<limits['minimum_base_z_m'] or tilt>limits['maximum_tilt_rad']:raise RuntimeError('fallen/tilt probe limit')
        if step_count%10==0:
            q=data.qpos.copy();v=data.qvel.copy()
            phase=next((x for x in phases if data.time<x['until']),phases[-1])
            rows.append({'sim_s':float(data.time),'wall_s':time.monotonic()-started,'phase':phase['phase'],'command_consumed':command,'qpos':q.tolist(),'qvel':v.tolist(),'ctrl':data.ctrl.copy().tolist(),'actuator_force':data.actuator_force.copy().tolist(),'arm_target':p.desired_joint_pos_arm.copy().tolist(),'ncon':data.ncon,'tilt_rad':tilt})
        phase=next((x for x in phases if data.time<x['until']),phases[-1])
        p.ref_base_lin_vel_H[:]=[phase['vx'],0.,0.]
        p.ref_base_ang_yaw_dot=phase['wz']
    upstream.mujoco.mj_step=observe_step
    p.run()
    summary.update(result='LOOP_COMPLETED',sim_s=float(p.mjData.time),wall_s=time.monotonic()-started,samples=len(rows),actual_model_dt_s=p.mjModel.opt.timestep,actor_io={'inputs':[(x.name,x.shape) for x in p.locomotion_policy.policy.get_inputs()],'outputs':[(x.name,x.shape) for x in p.locomotion_policy.policy.get_outputs()]},actuator_caps=p.mjModel.actuator_ctrlrange.tolist())
except BaseException:
    summary['error']=traceback.format_exc()
finally:
    if p is not None:
        if 'original_step' in globals():upstream.mujoco.mj_step=original_step
        p.viewer.close()
    summary['elapsed_wall_s_including_init']=time.monotonic()-started
    summary['threads_after_close']=[{'name':t.name,'daemon':t.daemon} for t in threading.enumerate()]
    summary['upstream_hashes_after']='PASS' if all(hashlib.sha256((UP/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in LOCK['files']) else 'FAIL'
    (HERE/'observations.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows),encoding='utf-8')
    (HERE/'summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(summary,indent=2),flush=True)
if summary['result']!='LOOP_COMPLETED':sys.exit(1)
