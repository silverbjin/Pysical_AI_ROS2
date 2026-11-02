"""Fresh edu_stop_v2 replay: upstream loop, snapshot + bounded native arm PD."""
import builtins,hashlib,json,math,os,sys,time,traceback,threading,inspect,textwrap,types,difflib
from pathlib import Path
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];UP=ROOT.parent/'upstream-iit-locomanipulation-d010212'
sys.dont_write_bytecode=True
sys.path[:0]=[str(UP/'deploy'),str(ROOT/'Ch13/scripts/reuse_13_5')]
import play_mujoco as upstream
from reproduce_upstream import freeze_arm_reference,configure_native_arm_pd,consistent_walking_run_source
GATE_PATH=ROOT/'Ch13/dependencies/section_13_5_edu_stop_v2.json'
G=json.loads(GATE_PATH.read_text(encoding='utf-8-sig'))
LOCK=json.loads((ROOT/'Ch13/dependencies/section_13_5_reuse.lock.json').read_text())
PHASES=[(5,'initial_zero',0,0),(10,'forward',.2,0),(15,'stop_forward',0,0),(19,'turn',0,.2),(25,'stop_turn',0,0)]
phase_at=lambda t:next((x for x in PHASES if t<x[0]),PHASES[-1])
for f in LOCK['files']:
    if hashlib.sha256((UP/f['path']).read_bytes()).hexdigest()!=f['sha256']:raise RuntimeError('asset mismatch '+f['path'])

def evaluate_window(rows, model):
    if not rows:return {'pass':False,'reason':'no observations'}
    cutoff=rows[-1]['wall_s']-G['window_wall_s']
    anchor=max((i for i,r in enumerate(rows) if r['wall_s']<=cutoff),default=-1)
    if anchor<0:return {'pass':False,'reason':'short wall window'}
    w=rows[anchor:];q=np.array([r['qpos'] for r in w]);v=np.array([r['qvel'] for r in w]);t=np.array([r['sim_s'] for r in w]);dt=np.diff(t)
    if len(w)<G['minimum_unique_samples'] or np.any(dt<=0) or t[-1]-t[0]<G['minimum_window_sim_s']:return {'pass':False,'reason':'insufficient unique advancing simulation observations'}
    rms=lambda a:np.sqrt(np.sum(a[1:]**2*dt[:,None],axis=0)/sum(dt))
    yaw=np.unwrap(np.arctan2(2*(q[:,3]*q[:,6]+q[:,4]*q[:,5]),1-2*(q[:,5]**2+q[:,6]**2)))
    limited=(model.jnt_limited.astype(bool)) & (model.jnt_type==upstream.mujoco.mjtJoint.mjJNT_HINGE)
    values=q[:,model.jnt_qposadr[limited]];bounds=model.jnt_range[limited]
    penetration=float(max(0,np.max(bounds[:,0]-values),np.max(values-bounds[:,1])))
    m={'wall_span_s':w[-1]['wall_s']-w[0]['wall_s'],'sim_span_s':t[-1]-t[0],'unique_samples':len(w),'planar_rms_speed_mps':float(np.linalg.norm(rms(v[:,:2]))),'yaw_rate_rms_radps':float(rms(v[:,5:6])[0]),'planar_excursion_m':float(np.max(np.linalg.norm(q[:,:2]-q[0,:2],axis=1))),'yaw_excursion_rad':float(np.max(abs(yaw-yaw[0]))),'arm_joint_rms_speed_radps':float(max(rms(v[:,18:24]))),'arm_joint_excursion_rad':float(max(np.max(q[:,19:25],axis=0)-np.min(q[:,19:25],axis=0))),'arm_joint_target_error_rad':float(np.max(abs(q[:,19:25]-np.array([r['arm_target'] for r in w])))),'max_stop_tilt_rad':max(r['tilt_rad'] for r in w),'joint_limit_soft_tolerance_rad':penetration,'diagnostic_max_raw_angular_speed':float(max(np.linalg.norm(v[:,3:6],axis=1))),'diagnostic_max_raw_arm_speed':float(np.max(abs(v[:,18:24])))}
    checks={key:m[key]<=G[key]+1e-10 for key in ['planar_rms_speed_mps','yaw_rate_rms_radps','planar_excursion_m','yaw_excursion_rad','arm_joint_rms_speed_radps','arm_joint_excursion_rad','arm_joint_target_error_rad','max_stop_tilt_rad','joint_limit_soft_tolerance_rad']}
    checks['zero_command']=all(r['command_consumed']==[0.,0.,0.] for r in w)
    return {'pass':all(checks.values()),'metrics':m,'checks':checks}

builtins.input=lambda *args:'closeConsole'
p=None;rows=[];allrows=[];step_count=0;last_phase=None;start=time.monotonic()
S={'revision':'section_13_5_reuse_v1_native_arm_pd_consistent_gains_edu_v2','gate_revision':G['revision'],'gate_sha256':hashlib.sha256(GATE_PATH.read_bytes()).hexdigest(),'shim_sha256':hashlib.sha256((ROOT/'Ch13/scripts/reuse_13_5/reproduce_upstream.py').read_bytes()).hexdigest(),'pid':os.getpid(),'ppid':os.getppid(),'result':'ERROR','correction':'snapshot arm target; arm affine PD with unchanged50/4 and original32/8Nm force caps; implicitfast. Original walking20/1.5 held throughout RL-active ticks (stand50/5 only when RL inactive); policy/physics2ms unchanged','max_force_cap_ratio':0.,'unexpected_contacts':{},'observed_leg_gain_counts':{}}
try:
    p=upstream.PlayMujoco();freeze_arm_reference(p)
    caps=p.mjModel.actuator_ctrlrange.copy()
    configure_native_arm_pd(p.mjModel,p.Kp_arm,p.Kd_arm)
    original_source=textwrap.dedent(inspect.getsource(upstream.PlayMujoco.run))
    corrected_source=consistent_walking_run_source(original_source)
    (HERE/'upstream_run_gain_selection.patch').write_text(''.join(difflib.unified_diff(original_source.splitlines(True),corrected_source.splitlines(True),fromfile='upstream/run',tofile='ch13/run_consistent_gains')))
    (HERE/'corrected_run_source.py').write_text(corrected_source)
    namespace=dict(upstream.PlayMujoco.run.__globals__)
    exec(compile(corrected_source,str(HERE/'corrected_run_source.py'),'exec'),namespace)
    p.run=types.MethodType(namespace['run'],p)

    original_viewer=p.viewer;original_step=upstream.mujoco.mj_step
    start=time.monotonic()
    class BoundedViewer:
        def __getattr__(self,name):return getattr(original_viewer,name)
        def is_running(self):
            if time.monotonic()-start>100:raise TimeoutError('100wall-second probe deadline')
            return p.mjData.time<25 and original_viewer.is_running()
    p.viewer=BoundedViewer()
    feet={p.mjModel.geom(n).id for n in ['FL','FR','RL','RR']}
    def observe_step(model,data,*args,**kwargs):
        global step_count,last_phase
        command=[float(p.ref_base_lin_vel_H[0]),float(p.ref_base_lin_vel_H[1]),float(p.ref_base_ang_yaw_dot)]
        gain_key=f"{p.Kp_legs}/{p.Kd_legs}";S['observed_leg_gain_counts'][gain_key]=S['observed_leg_gain_counts'].get(gain_key,0)+1
        data.ctrl[12:18]=p.desired_joint_pos_arm
        original_step(model,data,*args,**kwargs);step_count+=1
        if not all(np.isfinite(x).all() for x in [data.qpos,data.qvel,data.actuator_force]):raise RuntimeError('nonfinite state/force')
        ratio=float(np.max(np.abs(data.actuator_force)/caps[:,1]));S['max_force_cap_ratio']=max(S['max_force_cap_ratio'],ratio)
        if ratio>1+1e-8:raise RuntimeError('actual actuator force cap exceeded')
        tilt=math.acos(float(np.clip(1-2*(data.qpos[4]**2+data.qpos[5]**2),-1,1)))
        if data.qpos[2]<.12 or tilt>math.pi/4:raise RuntimeError('fall bound')
        for c in data.contact:
            a,b=int(c.geom1),int(c.geom2)
            allowed=(a in feet and model.geom_bodyid[b]==0) or (b in feet and model.geom_bodyid[a]==0)
            if not allowed:
                key=f'{a}:{b}';S['unexpected_contacts'][key]=S['unexpected_contacts'].get(key,0)+1
        phase=phase_at(data.time)
        r={'sim_s':float(data.time),'wall_s':time.monotonic()-start,'phase':phase[1],'command_consumed':command,'qpos':data.qpos.copy().tolist(),'qvel':data.qvel.copy().tolist(),'arm_target':p.desired_joint_pos_arm.copy().tolist(),'tilt_rad':tilt}
        allrows.append(r)
        if step_count%10==0:rows.append(r)
        if phase[1]!=last_phase:print('phase',phase[1],'sim_s',round(data.time,3),flush=True);last_phase=phase[1]
        p.ref_base_lin_vel_H[:]=[phase[2],0.,0.];p.ref_base_ang_yaw_dot=phase[3]
    upstream.mujoco.mj_step=observe_step
    p.run()
    gates={}
    for phase in ['initial_zero','stop_forward','stop_turn']:
        subset=[r for r in allrows if r['phase']==phase]
        gates[phase]=evaluate_window(subset,p.mjModel)
    S.update(result='LOOP_COMPLETED',sim_s=float(p.mjData.time),wall_s=time.monotonic()-start,physics_samples=len(allrows),trajectory_samples=len(rows),stop_gates=gates,edu_stop_gate_pass=all(x['pass'] for x in gates.values()),scope='R1 stop and hold feasibility only; not U3-U7 or complete stow/IK/lifecycle approval')
except BaseException:S['error']=traceback.format_exc()
finally:
    if p is not None:
        if 'original_step' in globals():upstream.mujoco.mj_step=original_step
        p.viewer.close()
    S['upstream_hashes_after']='PASS' if all(hashlib.sha256((UP/f['path']).read_bytes()).hexdigest()==f['sha256'] for f in LOCK['files']) else 'FAIL'
    S['threads_after_close']=[{'name':t.name,'daemon':t.daemon} for t in threading.enumerate()]
    (HERE/'trajectory.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in rows))
    # Retain actual500Hz end windows for independent validation; avoid full long raw dump.
    retained=[]
    for phase in ['initial_zero','stop_forward','stop_turn']:
        subset=[r for r in allrows if r['phase']==phase]
        if subset:retained += [r for r in subset if r['sim_s']>=subset[-1]['sim_s']-2.]
    (HERE/'stop_windows_500hz.jsonl').write_text(''.join(json.dumps(x)+'\n' for x in retained))
    (HERE/'summary.json').write_text(json.dumps(S,indent=2)+'\n');print(json.dumps(S,indent=2),flush=True)
if S['result']!='LOOP_COMPLETED':sys.exit(1)
