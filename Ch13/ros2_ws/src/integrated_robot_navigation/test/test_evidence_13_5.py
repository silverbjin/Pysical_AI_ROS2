"""A process exit, cancel ACK, or handwritten PASS is not native acceptance."""
from test_native_verdicts import api


def test_empty_teardown_and_missing_fields_fail_closed():
    assert not api().normal_teardown({})


def test_force_or_residual_or_unreaped_child_cannot_be_normal_exit():
    good = dict(runtime_exit=True, engine_exit=True, parent_reaped=True,
                launch_returncode=0, engine_returncodes=[0], forced_cleanup=False, residual_live_pids=[])
    assert api().normal_teardown(good)
    for key, value in (('forced_cleanup', True), ('residual_live_pids', [12345]),
                       ('parent_reaped', False), ('runtime_exit', False), ('engine_exit', False)):
        assert not api().normal_teardown({**good, key: value})


def test_successful_launch_wrapper_cannot_hide_crashed_or_unknown_engine_child():
    base = dict(runtime_exit=True, engine_exit=True, parent_reaped=True,
                launch_returncode=0, forced_cleanup=False, residual_live_pids=[])
    assert not api().normal_teardown({**base, 'engine_returncodes': [-6]})
    assert not api().normal_teardown({**base, 'engine_returncodes': []})


def test_native_child_exit_is_taken_from_owning_parent_not_wrapper_returncode():
    content = ('[INFO] [ros2_control_node-1]: process has finished cleanly [pid 123]\n'
               '[ERROR] [ros2_control_node-2]: process has died [pid 124, exit code -6, cmd x].\n')
    assert api().engine_returncodes(content, [123, 124, 125]) == [0, -6, None]


def test_terminal_ack_or_status_alone_cannot_prove_carry():
    verify = api()
    assert not verify.carry_terminal(dict(cancel_ack=True, status=4))
    assert not verify.carry_terminal(dict(terminal=True, result_future_done=False, result_status=4,
                                         result_error_code=0, pending_uuid=None))
    assert verify.carry_terminal(dict(terminal=True, result_future_done=True, result_status=4,
                                     result_error_code=0, pending_uuid=None))
