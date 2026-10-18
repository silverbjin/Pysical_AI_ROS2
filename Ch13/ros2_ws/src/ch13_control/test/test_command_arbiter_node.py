import pytest
from ch13_control.command_arbiter_node import to_command
from sensor_msgs.msg import JointState
from ch13_control.common import sole_publisher_id

def test_jazzy_transport_info_dictionary():
    from types import SimpleNamespace
    assert sole_publisher_id([SimpleNamespace(endpoint_gid=[1,2,3])])=='010203'
    with pytest.raises(ValueError):sole_publisher_id([])
    with pytest.raises(ValueError):sole_publisher_id([object(),object()])

def test_message_conversion_uses_transport_owner_and_stamp():
    m=JointState();m.name=['arm_joint_1'];m.position=[.2];m.header.stamp.sec=2;m.header.stamp.nanosec=100000000;m.header.frame_id='spoofed'
    c=to_command(m,'transport_gid')
    assert c.stamp==2.1 and c.publisher_id=='transport_gid'
    assert c.names==('arm_joint_1',)
