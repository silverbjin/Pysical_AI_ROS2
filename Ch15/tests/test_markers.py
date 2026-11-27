import unittest
from copy import deepcopy
from ch15_interfaces.msg import MissionStatus,TargetObservation
from ch15_visualization.marker_contract import Session,valid_target
from ch15_visualization.detection_marker_node import create_detection_marker
from visualization_msgs.msg import Marker

def status():
    m=MissionStatus();m.mission_id='m';m.epoch=1;m.profile='mock';m.source='MOCK';m.header.stamp.sec=10
    return m
def target():
    m=TargetObservation();m.mission_id='m';m.epoch=1;m.valid=True;m.source='MOCK';m.pose_kind='GRASP_POSE';m.object_class='red_cube'
    m.header.frame_id='map';m.header.stamp.sec=10;m.target_pose.header=deepcopy(m.header)
    m.target_pose.pose.position.x=.5;m.target_pose.pose.orientation.w=1.
    return m

class Tests(unittest.TestCase):
    def test_valid(self):
        m=target()
        self.assertTrue(valid_target(m,'map',('m',1),'mock',10_000_000_001))
        a=create_detection_marker(m.target_pose)
        self.assertEqual((a.action,a.header,a.pose.position,a.pose.orientation.w,a.lifetime.sec),(Marker.ADD,m.target_pose.header,m.target_pose.pose.position,1.,1))
    def test_invalid(self):
        for name in ('nan','frame','stale','future','epoch','source','invalid','quat','header'):
            m=target();now=10_000_000_001
            if name=='nan':m.target_pose.pose.position.x=float('nan')
            if name=='frame':m.target_pose.header.frame_id='bad'
            if name=='stale':now+=300_000_000
            if name=='future':now-=2
            if name=='epoch':m.epoch=2
            if name=='source':m.source='RGBD_COLOR'
            if name=='invalid':m.valid=False
            if name=='quat':m.target_pose.pose.orientation.w=.1
            if name=='header':m.header.stamp.nanosec=1
            self.assertFalse(valid_target(m,'map',('m',1),'mock',now),name)
    def test_transition_rewind(self):
        s=Session('mock');m=status();now=10_000_000_001
        self.assertTrue(s.clock(now));self.assertEqual(s.status(m,now),(True,True))
        m.epoch=2;self.assertEqual(s.status(m,now),(True,True))
        m.epoch=1;self.assertEqual(s.status(m,now),(False,False))
        self.assertFalse(s.clock(now-1));self.assertIsNone(s.identity)
        self.assertFalse(s.clock(now+100));self.assertEqual(s.status(m,now),(False,False))
    def test_replay_and_physical(self):
        m=target();now=10_000_000_001
        self.assertFalse(valid_target(m,'map',('m',1),'replay',now))
        m.source='RGBD_COLOR';m.pose_kind='POSITION_ONLY'
        self.assertTrue(valid_target(m,'map',('m',1),'physical',now))
        self.assertFalse(valid_target(m,'map',('m',1),'mock',now))
    def test_ids(self):
        m=target()
        self.assertNotEqual(create_detection_marker(m.target_pose,0).id,create_detection_marker(m.target_pose,2).id)
if __name__=='__main__':unittest.main()
