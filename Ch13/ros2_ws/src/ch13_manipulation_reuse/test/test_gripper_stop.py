from ch13_manipulation_reuse.action_bridge import gripper_stalled


def test_contact_blockage_can_be_below_force_cap():
    assert gripper_stalled(.019,0.,.0002,.19)
    assert not gripper_stalled(.001,0.,0.,.01)
    assert not gripper_stalled(.019,0.,.02,.19)
    assert not gripper_stalled(.019,0.,0.,0.)
