from integrated_robot_runtime.policy import joint_snapshot, safe_arm, valid_pair


def test_joint_mapping_is_by_name_and_rejects_missing_state():
    assert joint_snapshot(['right', 'left'], [0.2, 0.1], ['left', 'right']) == [0.1, 0.2]
    assert joint_snapshot(['right'], [0.2], ['left', 'right']) is None


def test_old_safe_pose_does_not_enable_startup():
    assert safe_arm([0.0] * 6, 0.1)
    assert not safe_arm([0.0] * 6, 1.0)


def test_close_timestamps_do_not_make_stale_pair_valid():
    assert valid_pair(100.0, 100.02, 100.1)
    assert not valid_pair(100.0, 100.02, 101.0)
