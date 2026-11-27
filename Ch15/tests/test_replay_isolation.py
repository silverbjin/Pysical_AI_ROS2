import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from replay_contract import validate,SAFE,validate_graph_topic,GRAPH_TYPES,EndpointAudit
class TestReplay(unittest.TestCase):
    def test_allow(self):self.assertEqual(validate(81,80,SAFE),list(SAFE))
    def test_reject(self):
        for domain,source,topics in [(80,80,SAFE),(81,80,SAFE+('/cmd_vel',)),(81,80,SAFE+('/clock',)),(81,80,('/navigate_to_pose/_action/send_goal',)),(0,80,SAFE)]:
            with self.assertRaises(ValueError):validate(domain,source,topics)
    def test_internal_graph_type_and_owner(self):
        self.assertTrue(validate_graph_topic('/events/read_split',['rosbag2_interfaces/msg/ReadSplitEvent'],['rosbag2_player']))
        for name,types,owners in [
            ('/events/read_split',['geometry_msgs/msg/Twist'],['rosbag2_player']),
            ('/events/read_split',['rosbag2_interfaces/msg/ReadSplitEvent'],['unknown']),
            ('/cmd_vel',['geometry_msgs/msg/Twist'],['rosbag2_player']),
            ('/clock',['rosgraph_msgs/msg/Clock'],['other']),
        ]:
            with self.assertRaises(ValueError):validate_graph_topic(name,types,owners)
        with self.assertRaises(ValueError):validate(81,80,SAFE+('/events/read_split',))
    def test_known_endpoint_teardown(self):
        a=EndpointAudit();topic='/clock';typ='rosgraph_msgs/msg/Clock'
        good=dict(owner='rosbag2_player',gid='abc1',type=typ)
        unknown=dict(good,owner='_NODE_NAME_UNKNOWN_')
        self.assertEqual(a.observe(topic,[typ],[good]),['rosbag2_player'])
        with self.assertRaises(ValueError):a.observe(topic,[typ],[unknown],completed=False)
        self.assertEqual(a.observe(topic,[typ],[unknown],completed=True),['rosbag2_player'])
        self.assertEqual(len(a.metadata_loss),1)
        for bad in [dict(unknown,gid='abc2'),dict(good,owner='intruder'),dict(good,gid='abc2'),dict(good,type='geometry_msgs/msg/Twist')]:
            with self.assertRaises(ValueError):a.observe(topic,[typ],[bad],completed=True)
        with self.assertRaises(ValueError):a.observe(topic,[typ],[good,good],completed=True)
        with self.assertRaises(ValueError):EndpointAudit().observe(topic,[typ],[unknown],completed=True)
if __name__=='__main__':unittest.main()
