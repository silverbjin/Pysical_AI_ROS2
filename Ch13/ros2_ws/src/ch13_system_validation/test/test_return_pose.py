import math
from ch13_system_validation.continuation import make_navigation_goal


def test_return_goal_sets_full_normalized_quaternion_despite_ros_defaults():
    goal=make_navigation_goal([0.,0.,math.pi],1_234_000_000)
    q=goal.pose.pose.orientation
    assert abs(q.x*q.x+q.y*q.y+q.z*q.z+q.w*q.w-1.)<1e-12
    yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
    assert abs(yaw-math.pi)<1e-12
    assert goal.pose.header.stamp.sec==1 and goal.pose.header.stamp.nanosec==234_000_000
