from sensor_msgs.msg import JointState
from ch13_navigation_reuse.command_gateway import JOINT_NAMES,valid_joints


def test_navigation_preserves_small_hold_and_manipulation_checks_real_limits():
    message=JointState(name=list(JOINT_NAMES),position=[0.]*20,velocity=[0.]*20)
    message.position[13]=2.;message.position[14]=-1.
    assert not valid_joints(message)
    assert valid_joints(message,manipulation=True)
    message.position[13]=3.3
    assert not valid_joints(message,manipulation=True)
    message.position[13]=1.;message.velocity[13]=float('nan')
    assert not valid_joints(message,manipulation=True)
