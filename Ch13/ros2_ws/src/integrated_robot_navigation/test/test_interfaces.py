"""The new wire contract must preserve provenance and named physical contacts."""
import integrated_robot_interfaces.msg as messages
import integrated_robot_interfaces.action as actions
from rclpy.serialization import serialize_message, deserialize_message


def test_contact_wire_roundtrip():
    assert hasattr(messages, 'FootContacts'), 'FootContacts IDL is missing'
    contacts = messages.FootContacts()
    contacts.header.frame_id = 'odom'
    contacts.header.stamp.sec = 12
    contacts.epoch, contacts.sequence = 5, 43
    contacts.names = ['fr_foot', 'fl_foot', 'rr_foot', 'rl_foot']
    contacts.normal_forces = [20., 21., 19., 18.]
    contacts.touching = [True, True, True, True]
    contacts.points[0].x = 0.25
    actual = deserialize_message(serialize_message(contacts), messages.FootContacts)
    assert actual.names == ['fr_foot', 'fl_foot', 'rr_foot', 'rl_foot']
    assert list(actual.normal_forces) == [20., 21., 19., 18.]
    assert actual.points[0].x == .25
    assert (actual.header.stamp.sec, actual.epoch, actual.sequence) == (12, 5, 43)


def test_approach_wire_keeps_source_capture_separate_from_target():
    assert hasattr(actions, 'ApproachObject'), 'ApproachObject IDL is missing'
    goal = actions.ApproachObject.Goal()
    goal.object_name, goal.track_id = 'cup', 'cup-7'
    goal.source_header.frame_id, goal.source_header.stamp.sec = 'camera_optical_frame', 12
    goal.target_pose.header.frame_id, goal.target_pose.header.stamp.sec = 'odom', 12
    goal.target_pose.pose.position.x, goal.target_pose.pose.orientation.w = 1., 1.
    actual = deserialize_message(serialize_message(goal), actions.ApproachObject.Goal)
    assert actual.track_id == 'cup-7'
    assert actual.source_header.frame_id == 'camera_optical_frame'
    assert actual.source_header.stamp.sec == actual.target_pose.header.stamp.sec == 12
    assert actual.target_pose.pose.position.x == 1.


def test_motion_state_roundtrip():
    assert hasattr(messages, 'MotionState'), 'MotionState IDL is missing'
    state = messages.MotionState()
    state.generation, state.model_sha256 = 3, 'ab' * 32
    state.state, state.phase, state.swing_foot = 'CRAWLING', 'SHIFT', 'fl_foot'
    state.ready, state.stopped, state.fault_reason = True, False, ''
    actual = deserialize_message(serialize_message(state), messages.MotionState)
    assert (actual.generation, actual.state, actual.phase) == (3, 'CRAWLING', 'SHIFT')
    assert actual.ready and not actual.stopped
