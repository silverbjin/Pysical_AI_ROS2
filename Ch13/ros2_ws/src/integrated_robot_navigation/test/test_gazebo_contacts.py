"""Breaks: fixed-joint name guesses, doubled contacts, wrong force axes."""
import importlib
import math

import pytest
from geometry_msgs.msg import Vector3, PoseArray, Pose, Point
from ros_gz_interfaces.msg import Contact, Contacts, Entity, JointWrench
from std_msgs.msg import Header
from builtin_interfaces.msg import Time

FEET = ('fr_foot', 'fl_foot', 'rr_foot', 'rl_foot')
MAP = {f'integrated_robot::{n[:2]}_calf_link::actual_lumped_{n}': n for n in FEET}
GROUND = 'ground_plane::link::collision'
POINTS = ((.25, -.18, .02), (.25, .18, .02), (-.25, -.18, .02), (-.25, .18, .02))


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.gazebo_contacts'), 'normalizer missing'
    return importlib.import_module('integrated_robot_navigation.gazebo_contacts')


def contact(name, force=30., swap=False):
    value = Contact(collision1=Entity(id=10, name=name), collision2=Entity(id=20, name=GROUND))
    if swap:
        value.collision1, value.collision2 = value.collision2, value.collision1
    wrench = JointWrench()
    wrench.body_1_wrench.force.z = force
    wrench.body_2_wrench.force.z = -force
    value.positions = [Vector3(x=.25, y=-.18, z=0.)]
    value.normals = [Vector3(z=1.)]
    value.depths = [.0001]
    value.wrenches = [wrench]
    return value


@pytest.mark.parametrize('swap,force', [(False, 30.), (True, -30.)])
def test_explicit_collision_mapping_and_world_up_load(swap, force):
    name = next(iter(MAP))
    msg = Contacts(header=Header(stamp=Time(sec=4), frame_id='odom'),
                   contacts=[contact(name, force, swap)])
    result = api().normalize_contacts(msg, POINTS, MAP, GROUND, epoch=8, sequence=9)
    assert result.header == msg.header and result.epoch == 8 and result.sequence == 9
    assert result.names == list(FEET)
    assert list(result.normal_forces) == [30., 0., 0., 0.]
    assert list(result.touching) == [True, False, False, False]
    assert result.points[0].z == 0. and result.points[1].z == .02


def test_unexpected_body_contact_is_reported_not_hidden():
    msg = Contacts(header=Header(frame_id='odom'), contacts=[contact('integrated_robot::base::body')])
    result = api().normalize_contacts(msg, POINTS, MAP, GROUND, epoch=0, sequence=1)
    assert result.unexpected_contacts == 1
    assert not any(result.touching)


@pytest.mark.parametrize('case', ['duplicate', 'missing_wrench', 'nonfinite', 'frame'])
def test_bad_native_contact_sample_fails_closed(case):
    item = contact(next(iter(MAP)))
    msg = Contacts(header=Header(frame_id='odom'), contacts=[item])
    if case == 'duplicate':
        msg.contacts.append(item)
    elif case == 'missing_wrench':
        item.wrenches = []
    elif case == 'nonfinite':
        item.wrenches[0].body_1_wrench.force.z = math.nan
    elif case == 'frame':
        msg.header.frame_id = 'base_link'
    with pytest.raises(ValueError):
        api().normalize_contacts(msg, POINTS, MAP, GROUND, epoch=0, sequence=1)


def pair():
    header = Header(stamp=Time(sec=4), frame_id='odom')
    return (Contacts(header=header, contacts=[contact(next(iter(MAP)))]),
            PoseArray(header=header, poses=[Pose(position=Point(x=p[0], y=p[1], z=p[2]))
                                           for p in POINTS]))


def test_pair_join_keeps_capture_and_drops_duplicates():
    join = api().GazeboContactJoiner(MAP, GROUND)
    contacts, feet = pair()
    join.receive_contacts(contacts, 8_000_000_000)
    assert join.take(4_010_000_000, 8_010_000_000) is None
    join.receive_feet(feet, 8_020_000_000)
    result = join.take(4_030_000_000, 8_030_000_000)
    assert result.header.stamp == contacts.header.stamp and result.sequence == 1
    join.receive_contacts(contacts, 8_040_000_000)
    join.receive_feet(feet, 8_040_000_000)
    assert join.take(4_050_000_000, 8_050_000_000) is None


@pytest.mark.parametrize('ros,wall', [(4_200_000_001, 8_100_000_000),
                                     (4_100_000_000, 8_200_000_001)])
def test_pair_cannot_renew_either_original_age(ros, wall):
    join = api().GazeboContactJoiner(MAP, GROUND)
    contacts, feet = pair()
    join.receive_contacts(contacts, 8_000_000_000)
    join.receive_feet(feet, 8_000_000_000)
    join.receive_contacts(contacts, 8_190_000_000)
    join.receive_feet(feet, 8_190_000_000)
    assert join.take(ros, wall) is None


def test_clock_reset_never_reactivates_old_or_new_contact_packets():
    join = api().GazeboContactJoiner(MAP, GROUND)
    join.observe_clock(4_000_000_000)
    join.observe_clock(1_000_000_000)
    contacts, feet = pair()
    join.receive_contacts(contacts, 8_000_000_000)
    join.receive_feet(feet, 8_000_000_000)
    assert join.take(4_100_000_000, 8_100_000_000) is None
    assert join.stopped


def test_pair_diagnostic_distinguishes_one_missing_member_and_keeps_first_receipt():
    join=api().GazeboContactJoiner(MAP,GROUND);contacts,feet=pair()
    join.receive_contacts(contacts,8_000_000_000)
    join.receive_contacts(contacts,8_100_000_000)
    snapshot=join.snapshot()
    assert snapshot['pending']['contacts']==[dict(stamp_ns=4_000_000_000,received_ns=8_000_000_000)]
    assert snapshot['pending']['feet']==[]
    assert snapshot['counts']['contacts']==2 and snapshot['duplicates']['contacts']==1
    join.receive_feet(feet,8_110_000_000)
    assert join.take(4_010_000_000,8_120_000_000) is not None
    snapshot=join.snapshot()
    assert snapshot['outputs']==1 and snapshot['last_pair']['capture_ns']==4_000_000_000
    assert snapshot['last_pair']['contacts_received_ns']==8_000_000_000
    assert snapshot['last_pair']['feet_received_ns']==8_110_000_000
    join.stop();assert join.snapshot()['last_pair']==snapshot['last_pair']


def test_pair_diagnostic_preserves_expiry_cause_and_largest_delivery_gap():
    join=api().GazeboContactJoiner(MAP,GROUND);contacts,feet=pair()
    join.receive_contacts(contacts,8_000_000_000)
    contacts.header.stamp.nanosec=20_000_000
    join.receive_contacts(contacts,8_210_000_000)
    join.take(4_030_000_000,8_220_000_000)
    snapshot=join.snapshot()
    assert snapshot['expired']['contacts']==1
    gap=snapshot['maximum_receipt_gap']['contacts']
    assert gap==dict(previous_stamp_ns=4_000_000_000,stamp_ns=4_020_000_000,
                    previous_received_ns=8_000_000_000,received_ns=8_210_000_000,gap_ns=210_000_000)
    assert snapshot['pending']['contacts']==[dict(stamp_ns=4_020_000_000,received_ns=8_210_000_000)]
