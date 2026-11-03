from pathlib import Path
import json,numpy as np,mujoco,sys,time
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];UP=ROOT.parent/'upstream-iit-locomanipulation-d010212'
sys.path.insert(0,str(ROOT/'Ch13/scripts/reuse_13_5'))
from reproduce_upstream import configure_native_arm_pd
rows=[json.loads(x) for x in (ROOT/'Ch13/evidence/section_13_5_reuse/d03dbba9-e07e-46ef-a32d-303e43b8b078/stop_windows_500hz.jsonl').read_text().splitlines()]
b=[r for r in rows if r['phase']=='stop_turn'];v=np.array([r['qvel'] for r in b]);dt=np.median(np.diff([r['sim_s'] for r in b]));freq=np.fft.rfftfreq(len(b),dt)
spec=np.abs(np.fft.rfft(v-v.mean(0),axis=0));peak=np.argmax(spec[1:],axis=0)+1
m=mujoco.MjModel.from_xml_path(str(UP/'robot_model/scene_rough.xml'))
names=['base_vx','base_vy','base_vz','base_wx','base_wy','base_wz']+[m.joint(i).name for i in range(1,m.njnt)]
R={'last_stop_signal_summary':[{'dof':i,'name':names[i],'rms':float(np.sqrt(np.mean(v[:,i]**2))),'dominant_hz':float(freq[peak[i]]),'adjacent_correlation':float(np.corrcoef(v[:-1,i],v[1:,i])[0,1])} for i in range(m.nv)],'contact_pair_names':[],'local_cases':[]}
for a,c in [(184,186),(6,124)]:
 R['contact_pair_names'].append([{'geom_id':i,'geom_name':m.geom(i).name,'body':m.body(m.geom_bodyid[i]).name} for i in [a,c]])
q0=m.key_qpos[m.key('home').id].copy();q0[2]=1
for case,legkp,legkd in [('stand_branch',50.,5.),('walking_branch',20.,1.5)]:
 m=mujoco.MjModel.from_xml_path(str(UP/'robot_model/scene_rough.xml'));configure_native_arm_pd(m,50.,4.)
 kp=np.array([legkp]*12+[50]*6+[10]);kd=np.array([legkd]*12+[4]*6+[.8])
 def advance(v0):
  d=mujoco.MjData(m);d.qpos[:]=q0;d.qvel[:]=v0
  d.ctrl[:]=kp*(q0[7:26]-d.qpos[7:26])-kd*d.qvel[6:25];d.ctrl[12:18]=q0[19:25]
  mujoco.mj_step(m,d);return d.qvel.copy()
 v0=np.zeros(m.nv);v0[6:]=.1;eps=1e-5
 J=np.column_stack([(advance(v0+np.eye(m.nv)[j]*eps)-advance(v0-np.eye(m.nv)[j]*eps))/(2*eps) for j in range(m.nv)])
 eig,vec=np.linalg.eig(J);order=np.argsort(abs(eig))[::-1];top=[]
 for index in order[:4]:
  mode=abs(vec[:,index]);parts=np.argsort(mode)[-5:][::-1]
  top.append({'eigenvalue':[float(eig[index].real),float(eig[index].imag)],'dominant_dofs':[{'name':names[i],'relative_weight':float(mode[i]/max(mode))} for i in parts]})
 R['local_cases'].append({'case':case,'spectral_radius':float(max(abs(eig))),'top_modes':top})
(HERE/'residual_modes.json').write_text(json.dumps(R,indent=2)+'\n');print(json.dumps(R,indent=2))
