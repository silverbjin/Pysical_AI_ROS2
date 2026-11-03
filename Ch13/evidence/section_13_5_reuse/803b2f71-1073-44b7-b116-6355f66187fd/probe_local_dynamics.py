"""Bounded local numerical diagnosis; original files untouched; no policy/viewer."""
from pathlib import Path
import json,math,os,time
import numpy as np
import mujoco
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];UP=ROOT.parent/'upstream-iit-locomanipulation-d010212'
START=time.monotonic()
report={'mujoco':mujoco.__version__,'pid':os.getpid(),'ppid':os.getppid(),'hypothesis':'Opaque Python damping torque can destabilize low-inertia wrists at 2ms; integrator-only change cannot expose its derivative.','scope':'Local one-step derivative, suspended home z1, wrist qvel0.1rad/s; no locomotion/stability acceptance','cases':[]}
for case in ['motor_euler','motor_implicitfast','native_arm_pd_implicitfast']:
 m=mujoco.MjModel.from_xml_path(str(UP/'robot_model/scene_rough.xml'))
 q0=m.key_qpos[m.key('home').id].copy();q0[2]=1.
 kp=np.array([50.]*12+[50.]*6+[10.]);kd=np.array([5.]*12+[4.]*6+[.8])
 caps=m.actuator_ctrlrange.copy()
 if 'implicitfast' in case:m.opt.integrator=mujoco.mjtIntegrator.mjINT_IMPLICITFAST
 if case.startswith('native'):
  m.actuator_ctrllimited[12:18]=False
  m.actuator_forcelimited[12:18]=True
  m.actuator_forcerange[12:18]=caps[12:18]
  m.actuator_biastype[12:18]=mujoco.mjtBias.mjBIAS_AFFINE
  m.actuator_gainprm[12:18,0]=50.
  m.actuator_biasprm[12:18,1]=-50.
  m.actuator_biasprm[12:18,2]=-4.
 def step(wrist_v,advance=True):
  d=mujoco.MjData(m);d.qpos[:]=q0;d.qvel[21:24]=wrist_v
  ctrl=kp*(q0[7:26]-d.qpos[7:26])-kd*d.qvel[6:25]
  d.ctrl[:]=ctrl
  if case.startswith('native'):d.ctrl[12:18]=q0[19:25]
  mujoco.mj_forward(m,d)
  force=d.actuator_force.copy()
  if advance:mujoco.mj_step(m,d)
  return d,force
 v=np.array([.1,.1,.1]);jac=np.zeros((3,3));eps=1e-5
 for j in range(3):
  dv=np.zeros(3);dv[j]=eps
  dp,_=step(v+dv);dm,_=step(v-dv)
  jac[:,j]=(dp.qvel[21:24]-dm.qvel[21:24])/(2*eps)
 d,force=step(v);M=np.zeros((m.nv,m.nv))
 try:mujoco.mj_fullM(m,d,M)
 except TypeError:mujoco.mj_fullM(m,M,d.qM)
 inv=np.linalg.inv(M)
 report['cases'].append({'name':case,'dt_s':m.opt.timestep,'wrist_initial_qvel':v.tolist(),'wrist_next_qvel':d.qvel[21:24].tolist(),'wrist_dvnext_dv':jac.tolist(),'wrist_velocity_map_eigenvalues_real':np.linalg.eigvals(jac).real.tolist(),'spectral_radius':float(max(abs(np.linalg.eigvals(jac)))),'wrist_effective_inertia_kgm2':[float(1/inv[i,i]) for i in range(21,24)],'initial_arm_forces':force[12:18].tolist(),'arm_force_caps':(m.actuator_forcerange if case.startswith('native') else m.actuator_ctrlrange)[12:18].tolist(),'contacts':int(d.ncon)})
report['wall_s']=time.monotonic()-START
(HERE/'local_dynamics.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
