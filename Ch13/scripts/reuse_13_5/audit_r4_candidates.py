"""Debug-only nominal arm/footprint candidate audit; never a vision PASS."""
from pathlib import Path
import json,sys
import numpy as np,mujoco,rclpy
root=Path(__file__).resolve().parents[3]
from ch13_navigation_reuse.scene import make_model
from ch13_navigation_reuse.world_map import WorldMap
from ch13_navigation_reuse.approach_geometry import candidates,arm_reach
m=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision');q=m.key_qpos[m.key('home').id].copy();q[2]=.30
rclpy.init();node=WorldMap('vision');msg=node.map;grid={'width':msg.info.width,'height':msg.info.height,'resolution':msg.info.resolution,'origin':[msg.info.origin.position.x,msg.info.origin.position.y],'data':list(msg.data)};fp=json.loads((root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json').read_text())['footprint'];a=candidates(m,q,np.array([1.75,0.,.55]),grid,fp);node.destroy_node();rclpy.shutdown();report={'profile':'DEBUG_MODEL_POINT_NOT_VISION','arm_chain_length_m':arm_reach(m,q),'candidate_count':len(a),'candidates':a};Path(sys.argv[1]).write_text(json.dumps(report,indent=2)+'\n');print('DEBUG candidates',len(a),'arm chain',report['arm_chain_length_m']);assert a
