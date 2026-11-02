from pathlib import Path
import importlib.util,sys,time,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
ROS=importlib.util.find_spec('rclpy') is not None
if ROS:
 import rclpy,numpy as np,mujoco
 from rclpy.node import Node
 from types import SimpleNamespace
 from scipy.spatial.transform import Rotation
 from tf2_msgs.msg import TFMessage
 from nav_msgs.msg import Odometry
 from ch13_navigation_reuse.platform_adapter import Platform
 from ch13_navigation_reuse.state_adapter import adapt
 from ch13_navigation_reuse.command_gateway import JOINT_NAMES,N
@unittest.skipUnless(ROS,'requires Jazzy')
class ActualTFWireTests(unittest.TestCase):
 def test_actual_tf_output_preserves_full_root_and_arm_chain(self):
  root=Path(__file__).resolve().parents[5];model=mujoco.MjModel.from_xml_path(str(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'));data=mujoco.MjData(model)
  data.qpos[:]=model.key_qpos[model.key('home').id];data.qpos[:3]=[2,3,.3];q=Rotation.from_euler('xyz',[.1,.2,.4]).as_quat();data.qpos[3:7]=np.roll(q,1);mujoco.mj_forward(model,data)
  rclpy.init();p=Platform();probe=Node('reuse_tf_probe');seen=[];raw=[]
  probe.create_subscription(TFMessage,'/tf',lambda m:seen.append(m),1);probe.create_subscription(Odometry,N+'/engine_state',lambda m:raw.append(m),1)
  state=adapt(data.qpos,data.qvel,JOINT_NAMES,2_000_000_000);backend=SimpleNamespace(mjModel=model,mjData=data,_ch13_mujoco=mujoco)
  try:
   end=time.monotonic()+2
   while (not seen or not raw) and time.monotonic()<end:p.publish_state(backend,state);rclpy.spin_once(probe,timeout_sec=.02)
   self.assertTrue(seen and raw);edges={t.child_frame_id:t for t in seen[-1].transforms};self.assertEqual(len(edges),len(seen[-1].transforms))
   a,b=edges['reuse/nav_base'],edges['reuse/base']
   quat=lambda t:Rotation.from_quat([t.transform.rotation.x,t.transform.rotation.y,t.transform.rotation.z,t.transform.rotation.w])
   pos=lambda t:np.array([t.transform.translation.x,t.transform.translation.y,t.transform.translation.z])
   np.testing.assert_allclose(pos(a)+quat(a).apply(pos(b)),[2,3,.3],atol=1e-12)
   np.testing.assert_allclose((quat(a)*quat(b)).as_matrix(),Rotation.from_quat(q).as_matrix(),atol=1e-12)
   self.assertEqual(edges['reuse/link1'].header.frame_id,'reuse/base');self.assertIn('reuse/link6',edges)
   self.assertTrue(all(t.header.stamp.sec==2 and t.header.stamp.nanosec==0 for t in edges.values()))
   self.assertAlmostEqual(raw[-1].pose.pose.position.z,.3);self.assertEqual(raw[-1].child_frame_id,'reuse/base')
  finally:p.destroy_node();probe.destroy_node();rclpy.shutdown()
if __name__=='__main__':unittest.main()
