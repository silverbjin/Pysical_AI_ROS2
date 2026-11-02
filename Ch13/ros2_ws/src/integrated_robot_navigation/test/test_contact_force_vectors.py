"""Signed, mapped world forces retain capture identity; never infer from |Fz|."""
import copy
import pytest
from ros_gz_interfaces.msg import Contacts
from test_gazebo_contacts import contact,MAP,GROUND,POINTS
from integrated_robot_navigation.gazebo_contacts import normalize_contacts
from integrated_robot_navigation.observations import sensor_sample


@pytest.mark.parametrize('swapped',[False,True])
def test_signed_force_belongs_to_named_foot_after_pair_order_change(swapped):
    item=contact(next(iter(MAP)),force=-30. if swapped else 30.,swap=swapped)
    sign=-1. if swapped else 1.
    item.wrenches[0].body_1_wrench.force.x=sign*5.
    item.wrenches[0].body_2_wrench.force.x=-sign*5.
    msg=Contacts(contacts=[item]);msg.header.frame_id='odom';msg.header.stamp.sec=4
    output=normalize_contacts(msg,POINTS,MAP,GROUND,epoch=0,sequence=8)
    assert getattr(output,'force_vectors_valid',False), 'attested signed force vectors missing'
    assert (output.forces_world[0].x,output.forces_world[0].y,output.forces_world[0].z)==(5.,0.,30.)
    sample=sensor_sample('contacts',output,9_000_000_000,0)
    assert sample.stamp_ns==4_000_000_000 and sample.received_ns==9_000_000_000
    assert sample.data['force_vectors_valid'] is True
    assert sample.data['forces_world'][0]==(5.,0.,30.)


def test_unsigned_normal_load_does_not_attest_a_downward_foot_vector():
    msg=Contacts(contacts=[contact(next(iter(MAP)),force=-30.)]);msg.header.frame_id='odom'
    output=normalize_contacts(msg,POINTS,MAP,GROUND,epoch=0,sequence=1)
    assert output.normal_forces[0]==30.  # old support observation remains explicit
    assert not getattr(output,'force_vectors_valid',False)


def test_force_packet_does_not_rewrite_the_received_message():
    msg=Contacts(contacts=[contact(next(iter(MAP)))]);msg.header.frame_id='odom'
    original=copy.deepcopy(msg)
    normalize_contacts(msg,POINTS,MAP,GROUND,epoch=0,sequence=1)
    assert msg==original
