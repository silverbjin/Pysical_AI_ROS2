"""Decode unchanged ROS CDR with C++-captured DDS identity and first receipt."""
import time,math
from rclpy.serialization import deserialize_message
from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import JointState,LaserScan,Image,CameraInfo
from tf2_msgs.msg import TFMessage
from std_msgs.msg import String
from rosgraph_msgs.msg import Clock
from action_msgs.msg import GoalStatusArray
TYPES={'raw':TwistStamped,'safe':TwistStamped,'base':Odometry,'joints':JointState,'clock':Clock,'nav':TwistStamped,'smooth':TwistStamped,'scan':LaserScan,'tf':TFMessage,'tf_static':TFMessage,'rgb':Image,'depth':Image,'camera_info':CameraInfo,'camera_meta':String,'vision_health':String}
TYPES.update(mission_lease=String,manipulation_observation=String,manipulation_navigation=String,manipulation_goals=GoalStatusArray)
def decode(data):
    if len(data)>1050000:raise ValueError('oversized ingress')
    version,key,source_gid,relay_gid,receipt_ns,source_ns,payload=data.split('|',6)
    if version!='r2v1' or key not in TYPES or len(source_gid)!=32 or len(relay_gid)!=32:raise ValueError('invalid ingress identity/schema')
    receipt=int(receipt_ns)/1e9
    if not math.isfinite(receipt) or receipt>time.monotonic()+.01:raise ValueError('invalid monotonic receipt')
    msg=deserialize_message(bytes.fromhex(payload),TYPES[key])
    return key,msg,{'publisher_gid':bytes.fromhex(source_gid),'relay_gid':relay_gid,'receipt_wall':receipt,'source_timestamp':int(source_ns)}
