"""Bounded offline profile of the actual installed publisher, no ROS node/engine."""
import cProfile,io,pstats,json,sys,time
from pathlib import Path
from types import SimpleNamespace
import numpy as np,mujoco
from ch13_navigation_reuse.platform_adapter import Platform
from ch13_navigation_reuse.command_gateway import JOINT_NAMES
from ch13_navigation_reuse.state_adapter import adapt
from ch13_manipulation_reuse.pick_scene import make_pick_model
root=Path(sys.argv[1]);out=Path(sys.argv[2]);assert not out.exists()
import os;os.environ['CH13_VALIDATION_PROFILE']='carry_v1';os.environ['CH13_VALIDATION_SCENARIO']='level3_house'
model=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml');data=mujoco.MjData(model);data.qpos[:]=model.key_qpos[model.key('home').id];mujoco.mj_forward(model,data)
state=adapt(data.qpos[:27],data.qvel[:26],JOINT_NAMES,1234567)
sink=SimpleNamespace(publish=lambda message:None);owner=SimpleNamespace(clock_pub=sink,base_pub=sink,nav_pub=sink,joint_pub=sink,tf_pub=sink,manipulation=None)
p=SimpleNamespace(_ch13_mujoco=mujoco,mjModel=model,mjData=data)
prof=cProfile.Profile();start=time.monotonic();cpu=time.process_time();prof.enable()
for _ in range(100):Platform.publish_state(owner,p,state)
prof.disable();span=time.monotonic()-start;cpu=time.process_time()-cpu
stream=io.StringIO();pstats.Stats(prof,stream=stream).sort_stats('cumtime').print_stats(14)
result=dict(scope='installed actual publisher with no-op DDS sink; 100 immutable-state repetitions; not live latency bound',wall_s=span,cpu_s=cpu,profile=stream.getvalue())
out.write_text(json.dumps(result,indent=2)+'\n');print(span,cpu);print(stream.getvalue())
