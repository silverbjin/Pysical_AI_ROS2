"""Saved-state ray equivalence and same-process GIL contention; no physics step."""
import os,sys,json,math,time,threading,tarfile,fcntl
from pathlib import Path
import numpy as np,mujoco
root=Path.cwd();out=root/'Ch13/evidence/section_13_8_repair/v50_scalar_batch_ray';out.mkdir(exist_ok=False)
os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level2_obstacles'
for name in ('ch13_navigation_reuse','ch13_manipulation_reuse','ch13_system_validation'):
 sys.path.insert(0,str(root/'Ch13/ros2_ws/src'/name))
from ch13_navigation_reuse.scene import ray_scan,SCAN_POS
from ch13_manipulation_reuse.pick_scene import make_pick_model

def batch(model,data,count=181):
 mujoco.mj_kinematics(model,data)
 base=model.body('base').id;r=data.xmat[base].reshape(3,3);origin=data.xpos[base]+r@SCAN_POS
 groups=np.zeros(6,dtype=np.uint8);groups[5]=1
 directions=np.array([r@np.array([math.cos(a),math.sin(a),0.]) for a in np.linspace(-math.pi,math.pi,count)])
 ids=np.empty(count,dtype=np.int32);dist=np.empty(count)
 mujoco.mj_multiRay(model,data,origin,directions.reshape(-1),groups,True,-1,ids,dist,None,count,mujoco.mjMAXVAL)
 return np.where((dist>=.05)&(dist<=4.),dist,np.inf)

lock=(root.parent/'ch13_reuse_engine.lock').open('a+');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml');data=mujoco.MjData(model)
 group_bodies=np.unique(model.geom_bodyid[model.geom_group==5]).tolist()
 case=root/'Ch13/evidence/section_13_8_system/0e7456d4-adcd-4ffc-873b-4ab4a054afa4'
 with tarfile.open(case/'raw.tar.gz','r:gz') as tar:
  with tar.extractfile('engine_observations.jsonl') as f:saved=[json.loads(line) for line in f]
 samples=[saved[i] for i in np.linspace(0,len(saved)-1,30,dtype=int)]
 differences=[]
 for row in samples:
  data.qpos[:]=row['qpos'];mujoco.mj_forward(model,data)
  reference=np.asarray(ray_scan(model,data));candidate=batch(model,data)
  np.testing.assert_allclose(candidate,reference,rtol=1e-12,atol=1e-10)
  finite=np.isfinite(reference);differences.append(float(np.max(abs(reference[finite]-candidate[finite]),initial=0.)))
 row=min(saved,key=lambda r:abs(r['sim_s']-39.71));data.qpos[:]=row['qpos'];mujoco.mj_forward(model,data)
 timings=[];stop=threading.Event();counter=[0];payload=json.dumps(dict(mode='ARMED',clock_ns=39710000000,counts={'safe':1,'clock':1},values=[.15,.1]))
 def contend():
  while not stop.is_set():json.loads(payload);counter[0]+=1
 thread=threading.Thread(target=contend);thread.start()
 try:
  for label,call in [('scalar',ray_scan),('batch',batch),('scalar',ray_scan),('batch',batch)]:
   for repeat in range(3):
    start=time.monotonic();cpu=time.thread_time();value=call(model,data)
    timings.append(dict(mode=label,wall_s=time.monotonic()-start,cpu_s=time.thread_time()-cpu))
 finally:stop.set();thread.join(2.);assert not thread.is_alive()
 report=dict(scope='saved qpos reconstruction only, no mj_step/ROS/actions/lease; one synthetic JSON thread, no scheduler/GC/GIL policy change',mujoco=mujoco.__version__,group5_body_ids=group_bodies,states=len(samples),rays_per_state=181,max_distance_error_m=max(differences),equivalence='PASS',timings=timings,contention_operations=counter[0],boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip())
 with (out/'comparison.json').open('x') as f:json.dump(report,f,indent=2)
 print(json.dumps(report))
finally:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
