"""Original40ms complete receipt is separate from the50Hz model decision."""
import importlib
import select
import socket
import time
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from test_native_xyz_process import fixture
from integrated_robot_navigation.load_process import SpatialLoadProcess,assess_numeric_close,assess_numeric_jobs
from integrated_robot_navigation import load_process as module


def wait_until(issued,delay_ns):
    remaining=(issued+delay_ns-time.monotonic_ns())/1e9
    if remaining>0:time.sleep(remaining)


def test_legacy_model_tick_rejects_already_readable_reply_after_40ms():
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',limits=case['limits'])
    try:
        worker.prepare();worker.submit(case['args'],dict(generation=1))
        issued=worker._pending['submitted_wall_ns']
        assert select.select([worker._channel],[],[],.035)[0]
        assert time.monotonic_ns()-issued<40_000_000
        wait_until(issued,45_000_000)
        with pytest.raises(ValueError,match='dispatch deadline'):worker.poll()
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['parent_reaped']
    assert not assess_numeric_jobs(closed),'negative control must keep the original deadline failure'


def test_event_receipt_within_40ms_can_wait_for_next_model_tick_without_renewing_time():
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',
        limits=case['limits'],receipt_mode='event_receiver')
    try:
        worker.prepare();worker.submit(case['args'],dict(generation=2))
        issued=worker._pending['submitted_wall_ns']
        assert worker._receipts.wait_message(.035),'no complete response before original40ms'
        collected=worker._receipts.snapshot()['received_wall_ns']
        assert 0<=collected-issued<=40_000_000
        wait_until(issued,45_000_000)
        reply=worker.poll()
        assert reply is not None and reply['context']==dict(generation=2)
        assert reply['received_wall_ns']==collected,'later decision renewed receipt time'
        assert worker.snapshot()['last_reply']['poll_started_wall_ns']>=collected
        assert worker.poll() is None,'same numerical reply was consumed twice'
        assert worker.snapshot()['completed']==1
    finally:closed=worker.close()
    assert closed['receiver_joined'] is True and closed['receiver_slot_empty'] is True
    assert assess_numeric_jobs(closed)
    closed.update(model_sha256=model.model_sha256,owner_pid=closed['pid']+1)
    assert assess_numeric_close(closed,model.model_sha256)
    assert not assess_numeric_close({**closed,'receiver_joined':False},model.model_sha256)


def test_event_receipt_still_rejects_consumption_after_original_200ms_wall_age():
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',
        limits=case['limits'],receipt_mode='event_receiver')
    try:
        worker.prepare();worker.submit(case['args'],dict(generation=3))
        issued=worker._pending['submitted_wall_ns']
        assert worker._receipts.wait_message(.035)
        wait_until(issued,200_000_001)
        with pytest.raises(ValueError,match='consum.*age'):worker.poll()
        assert worker.last_model is None and worker.snapshot()['discarded']==1
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['receiver_joined']
    assert not assess_numeric_jobs(closed)


def test_late_complete_receipt_is_rejected_even_when_child_compute_was_timely(monkeypatch):
    inbox_module=importlib.import_module('integrated_robot_navigation.numeric_receipts')
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',
        limits=case['limits'],receipt_mode='event_receiver')
    try:
        worker.prepare()
        # Only the test receiver clock is shifted. The child's compute stamp
        # and parent's real request time cannot substitute for complete receipt.
        with monkeypatch.context() as patch:
            patch.setattr(inbox_module,'time',SimpleNamespace(monotonic_ns=lambda:time.monotonic_ns()+50_000_000))
            worker.submit(case['args'],dict(generation=4))
            issued=worker._pending['submitted_wall_ns']
            assert worker._receipts.wait_message(.1)
            with pytest.raises(ValueError,match='dispatch deadline'):worker.poll()
        reply=worker.snapshot()['last_reply']
        assert reply['computed_wall_ns']-issued<40_000_000
        assert reply['received_wall_ns']-issued>40_000_000
        assert worker.last_model is None and worker.snapshot()['pending'] is False
    finally:closed=worker.close()
    assert closed['acknowledged'] and closed['receiver_joined']
    assert not assess_numeric_jobs(closed)


def test_stop_with_outstanding_job_joins_reader_before_draining_result_and_stop_ack():
    model,case=fixture();worker=SpatialLoadProcess(model,command_space='stance_xyz',
        limits=case['limits'],receipt_mode='event_receiver')
    worker.prepare();worker.submit(case['args'],dict(generation=5))
    with pytest.raises(ValueError,match='one outstanding'):worker.submit(case['args'],{})
    closed=worker.close()
    assert closed['receiver_joined'] and closed['receiver_slot_empty']
    assert closed['pending'] is False and closed['discarded']==1
    assert closed['acknowledged'] and closed['parent_reaped'] and closed['returncode']==0
    assert closed['complete_kernel_closed'] and closed['optimizer_closed'] and closed['reference_geometry_closed']
    with pytest.raises(ValueError,match='closed'):worker.submit(case['args'],{})
    assert worker.close()==closed


@contextmanager
def raw_inbox():
    api=importlib.import_module('integrated_robot_navigation.numeric_receipts')
    left,right=socket.socketpair();left.setblocking(False)
    owner=object.__new__(SpatialLoadProcess);owner._channel=left;owner._buffer=b''
    inbox=api.NumericReceiptInbox(left,owner._receive_once);inbox.start()
    try:yield owner,inbox,right
    finally:
        assert inbox.stop(.5),'read-only receiver leaked'
        left.close();right.close()


def test_partial_frame_has_no_receipt_and_first_complete_parse_is_never_retimed():
    with raw_inbox() as (_,inbox,peer):
        frame=module._packet(dict(kind='result',id=1,ok=True))
        peer.sendall(frame[:-1]);assert not inbox.wait_message(.02)
        assert inbox.snapshot()['received_wall_ns'] is None
        completed_after=time.monotonic_ns();peer.sendall(frame[-1:])
        assert inbox.wait_message(.2)
        captured=inbox.snapshot()['received_wall_ns'];assert captured>=completed_after
        time.sleep(.01);message,received=inbox.take()
        assert received==captured and message['id']==1
        assert inbox.take() is None


def test_one_slot_never_overwrites_the_first_frame():
    with raw_inbox() as (_,inbox,peer):
        peer.sendall(module._packet(dict(kind='result',id=1))+module._packet(dict(kind='result',id=2)))
        assert inbox.wait_message(.2)
        first_stamp=inbox.snapshot()['received_wall_ns'];time.sleep(.01)
        first,stamp=inbox.take();assert first['id']==1 and stamp==first_stamp
        assert inbox.wait_message(.2)
        second,_=inbox.take();assert second['id']==2


def test_stop_during_partial_frame_returns_stream_ownership_without_losing_bytes():
    with raw_inbox() as (owner,inbox,peer):
        frame=module._packet(dict(kind='result',id=1))
        peer.sendall(frame[:6]);assert not inbox.wait_message(.02)
        assert inbox.stop(.2) and inbox.snapshot()['alive'] is False
        peer.sendall(frame[6:])
        assert owner._receive_once()['id']==1,'joined receiver lost partially read bytes'
        assert inbox.stop(.2)


def test_eof_is_reported_and_reader_can_be_joined():
    with raw_inbox() as (_,inbox,peer):
        peer.close();assert not inbox.wait_message(.2)
        with pytest.raises(ValueError,match='disconnected'):inbox.take()


@pytest.mark.parametrize('async_mode,policy',[(False,'coupled_contact'),(True,'geometric')])
def test_event_receipt_requires_explicit_async_coupled_scope(nav_robot_model,async_mode,policy):
    from integrated_robot_navigation.gait import CrawlMachine
    from integrated_robot_navigation.carry_profile import default_limits
    with pytest.raises(ValueError,match='event receipt requires'):
        CrawlMachine(nav_robot_model,default_limits(),async_load_transfer=async_mode,
            load_transfer_policy=policy,load_receipt_mode='event_receiver')
