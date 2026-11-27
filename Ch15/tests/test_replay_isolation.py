import unittest,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'python'))
from replay_contract import validate,SAFE,validate_graph_topic,GRAPH_TYPES
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
if __name__=='__main__':unittest.main()
