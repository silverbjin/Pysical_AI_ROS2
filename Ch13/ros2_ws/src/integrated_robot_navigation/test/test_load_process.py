"""Numerical-only process: bounded requests, original context and normal reap."""
import importlib.util
import json
import os
import signal
import time
import pytest
from test_spatial_load_transition import inputs


def api():
    assert importlib.util.find_spec('integrated_robot_navigation.load_process'), \
        'numerical execution still shares the ROS callback interpreter'
    from integrated_robot_navigation.load_process import SpatialLoadProcess
    return SpatialLoadProcess


def take(worker):
    deadline=time.monotonic()+1.
    while time.monotonic()<deadline:
        try:result=worker.poll()
        except Exception:
            print('NUMERICAL_FAILURE_DIAGNOSTIC',json.dumps(dict(
                snapshot=worker.snapshot(),attempt=worker.last_attempt),allow_nan=False))
            raise
        if result is not None:return result
        time.sleep(.001)
    raise AssertionError('bounded numerical response missing')


def test_prepare_is_numeric_only_idempotent_and_normally_reaped(nav_robot_model):
    model,_=inputs(nav_robot_model);worker=api()(model)
    try:
        ready=worker.prepare()
        assert ready['scope']=='numerical_child_no_ros_or_commands'
        assert ready['pid']!=os.getpid() and ready['model_sha256']==model.model_sha256
        assert ready['preparation']['solver_verified'] is True
        assert worker.prepare()==ready
        assert worker.snapshot()['submitted']==0
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped'] and closed['returncode']==0
    assert closed['forced_cleanup'] is False


def test_one_outstanding_job_preserves_context_and_yields_no_command(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    context=dict(generation=7,foot=args['foot'],capture_ros_ns=123,capture_wall_ns=456)
    try:
        worker.submit(args,context)
        with pytest.raises(ValueError,match='outstanding'):worker.submit(args,dict(context,generation=8))
        result=take(worker)
        assert result['context']==context
        assert result['job_id']==worker.last_input_id==1
        assert worker.snapshot()['last_input_id']==1
        assert set(result['delta'])==set(model.feet)
        assert all(abs(v)<=.002*.02+1e-12 for v in result['delta'].values())
        assert worker.poll() is None
        assert worker.snapshot()['submitted']==1 and worker.snapshot()['completed']==1
    finally:worker.close()


def test_dispatch_deadline_is_separate_and_never_retags_a_late_job(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    try:
        worker.submit(args,dict(capture_ros_ns=123))
        with pytest.raises(ValueError,match='dispatch deadline'):
            worker.poll(now_wall_ns=time.monotonic_ns()+41_000_000)
        assert worker.snapshot()['fault']
    finally:worker.close()


def test_discarded_work_is_drained_without_applying_or_restarting(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);ready=worker.prepare()
    try:
        worker.submit(args,dict(generation=1));worker.discard()
        until=time.monotonic()+.3
        while worker.snapshot()['pending'] and time.monotonic()<until:
            assert worker.poll() is None;time.sleep(.001)
        assert not worker.snapshot()['pending'] and worker.snapshot()['discarded']==1
        assert worker.prepare()['pid']==ready['pid']
    finally:worker.close()


def test_failed_numeric_job_is_latched_without_automatic_retry(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    args['forces_world']={f:[0.,0.,100000.] for f in model.feet}
    try:
        worker.submit(args,dict(generation=1))
        with pytest.raises(ValueError,match='transition optimization'):take(worker)
        with pytest.raises(ValueError,match='latched'):worker.submit(args,dict(generation=2))
        assert worker.snapshot()['submitted']==1 and worker.snapshot()['failed']==1
    finally:worker.close()


def test_close_cancels_outstanding_math_and_reaps_before_releasing_owner(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    worker.submit(args,dict(generation=1))
    closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped']
    assert closed['discarded']==1 and closed['returncode']==0
    with pytest.raises(ValueError,match='closed'):worker.submit(args,{})


def test_nonfinite_job_cannot_enter_the_transport(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    args['dt']=float('nan')
    try:
        with pytest.raises(ValueError):worker.submit(args,{})
        assert worker.snapshot()['submitted']==0
    finally:worker.close()


def test_group_interrupt_leaves_normal_close_to_the_ros_owner(nav_robot_model):
    model,_=inputs(nav_robot_model);worker=api()(model);ready=worker.prepare()
    os.kill(ready['pid'],signal.SIGINT)
    closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped'] and closed['returncode']==0


def test_lost_parent_transport_exits_child_but_does_not_fabricate_close_ack(nav_robot_model):
    model,_=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    worker._channel.close()
    assert worker._process.wait(timeout=2.)==0
    with pytest.raises(RuntimeError,match='normal close unconfirmed'):worker.close()
    assert worker._close_report['parent_reaped'] and not worker._close_report['acknowledged']
    with pytest.raises(RuntimeError,match='normal close unconfirmed'):worker.close()


@pytest.mark.parametrize('change',[{},dict(acknowledged=False),dict(parent_reaped=False),
    dict(pending=True),dict(forced_cleanup=True),dict(returncode=-2),dict(returncode=False),
    dict(error='unconfirmed'),dict(model_sha256='wrong'),dict(owner_pid=2)])
def test_close_acceptance_requires_independent_terminal_and_owner_fields(change):
    from integrated_robot_navigation import load_process as module
    assert hasattr(module,'assess_numeric_close'),'normal numerical close is not an explicit acceptance check'
    record=dict(scope='one_numerical_job_no_command_authority',model_sha256='a'*64,
        pid=2,owner_pid=1,closed=True,acknowledged=True,parent_reaped=True,pending=False,
        forced_cleanup=False,returncode=0,error='')
    record.update(change)
    assert module.assess_numeric_close(record,'a'*64) is (not change)


def test_spawn_failure_closes_both_socket_ends_and_never_retries(nav_robot_model,monkeypatch):
    from integrated_robot_navigation import load_process as module
    model,_=inputs(nav_robot_model);worker=api()(model);calls=[]
    def denied(*a,**k):calls.append(1);raise OSError('controlled spawn rejection')
    monkeypatch.setattr(module.subprocess,'Popen',denied)
    before=len(os.listdir('/proc/self/fd'))
    with pytest.raises(ValueError,match='preparation'):worker.prepare()
    assert len(os.listdir('/proc/self/fd'))==before
    with pytest.raises(ValueError,match='latched'):worker.prepare()
    assert len(calls)==1
    closed=worker.close()
    assert closed['no_process_started'] and not closed['acknowledged']


@pytest.mark.parametrize('drain',['poll','close'])
def test_cancelled_failed_math_remains_a_job_failure_even_with_normal_close(nav_robot_model,drain):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    args['forces_world']={f:[0.,0.,100000.] for f in model.feet}
    worker.submit(args,dict(generation=1));worker.discard()
    try:
        if drain=='poll':
            with pytest.raises(ValueError,match='transition optimization'):take(worker)
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped']
    assert closed['failed']==1 and closed['fault'], 'cancel hid an actual numeric failure'
    from integrated_robot_navigation.load_process import assess_numeric_jobs
    assert not assess_numeric_jobs(closed)


def test_exact_sent_input_is_owned_json_and_survives_a_rejected_result(nav_robot_model):
    model,args=inputs(nav_robot_model);worker=api()(model);worker.prepare()
    args['forces_world']={f:[0.,0.,100000.] for f in model.feet}
    try:
        worker.submit(args,dict(generation=11));args['dt']=.1
        with pytest.raises(ValueError):take(worker)
        assert worker.last_input['dt']==.02
        assert worker.last_context==dict(generation=11)
        assert isinstance(worker.last_input['body_pose'],list)
        import json
        json.dumps(worker.last_input,allow_nan=False)
    finally:worker.close()


@pytest.mark.parametrize('change',[{},dict(failed=1),dict(fault='cancelled solve failed'),
    dict(pending=True),dict(submitted=3),dict(completed=0,discarded=2),dict(submitted=True)])
def test_job_acceptance_is_distinct_from_process_exit(change):
    from integrated_robot_navigation import load_process as module
    assert hasattr(module,'assess_numeric_jobs'), 'normal exit is not mathematical success'
    record=dict(submitted=2,completed=1,discarded=1,failed=0,fault='',pending=False)
    record.update(change)
    assert module.assess_numeric_jobs(record) is (not change)


def test_explicit_xyz_process_verifies_its_mode_and_returns_bounded_vectors(nav_robot_model):
    from test_spatial_xyz_transition import xyz_inputs
    from integrated_robot_navigation.carry_profile import default_limits
    model,args=xyz_inputs(nav_robot_model)
    worker=api()(model,command_space='stance_xyz',limits=default_limits())
    try:
        ready=worker.prepare();assert ready['command_space']=='stance_xyz'
        worker.submit(args,dict(generation=7));result=take(worker)
        import numpy as np
        assert all(np.linalg.norm(d)<=.002*.02+1e-10 for d in result['delta'].values())
        assert result['numeric_input']['reference_xyz']==worker.last_input['reference_xyz']
        assert worker.last_model['future_geometry_validated'] is True
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped']
