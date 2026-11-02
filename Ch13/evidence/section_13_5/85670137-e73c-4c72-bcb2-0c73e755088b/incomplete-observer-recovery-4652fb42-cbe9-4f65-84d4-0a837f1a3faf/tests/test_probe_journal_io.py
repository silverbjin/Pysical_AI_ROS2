"""A slow evidence sink must not own the native observation ingress lock."""
import json
import threading
import time
import pytest
import rclpy
from rclpy.context import Context
from probe_navigation_13_5 import NavigationProbe


def test_slow_journal_write_does_not_block_probe_callback_and_is_joined(tmp_path,monkeypatch):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    entered,release,finished=threading.Event(),threading.Event(),threading.Event()
    original=probe.raw.write;errors=[]
    def blocked(value):
        entered.set()
        assert release.wait(3.)
        return original(value)
    monkeypatch.setattr(probe.raw,'write',blocked)
    def callback():
        try:probe._dispatch(probe._write,'controlled',dict(capture_ns=123))
        except BaseException as error:errors.append(error)
        finally:finished.set()
    producer=threading.Thread(target=callback)
    try:
        producer.start()
        assert entered.wait(1.)
        assert finished.wait(.15),'file IO still blocks the ingress callback'
        assert not errors
        assert probe._lock.acquire(timeout=.05),'file IO still owns the native inbox lock'
        probe._lock.release()
        release.set();producer.join(1.)
        probe.restore_history(receiver_joined=True)
        assert probe.journal.report()['joined'] is True
        assert probe.journal.report()['submitted']==probe.journal.report()['written']==1
        assert json.loads((tmp_path/'observations.jsonl').read_text())['value']['capture_ns']==123
    finally:
        release.set();producer.join(3.)
        probe.close_log();probe.destroy_node();context.try_shutdown()


@pytest.mark.parametrize('bound',['records','bytes'])
def test_journal_overflow_is_sticky_without_overwrite_and_drain_is_joined(tmp_path,bound):
    from probe_navigation_13_5 import EvidenceJournal
    entered,release=threading.Event(),threading.Event()
    sink=(tmp_path/'journal').open('w');original=sink.write
    def blocked(value):
        entered.set();assert release.wait(2.)
        return original(value)
    sink.write=blocked
    writer=EvidenceJournal(sink,max_records=1 if bound=='records' else 3,
                           max_bytes=4 if bound=='bytes' else 1024)
    try:
        writer.submit('1234');assert entered.wait(1.)
        with pytest.raises(RuntimeError,match='capacity'):writer.submit('5')
        with pytest.raises(RuntimeError,match='capacity'):writer.submit('6')
        release.set()
        with pytest.raises(RuntimeError,match='capacity'):writer.close(timeout_sec=1.)
        assert writer.report()['joined']
        assert writer.report()['submitted']==writer.report()['written']==1
        assert (tmp_path/'journal').read_text()=='1234'
    finally:
        release.set()
        try:writer.close(timeout_sec=2.)
        except RuntimeError:pass


def test_journal_error_and_join_timeout_never_become_success(tmp_path):
    from probe_navigation_13_5 import EvidenceJournal
    entered,release=threading.Event(),threading.Event()
    sink=(tmp_path/'journal').open('w')
    def broken(value):
        entered.set();assert release.wait(2.)
        raise OSError('injected disk error')
    sink.write=broken;writer=EvidenceJournal(sink)
    try:
        writer.submit('original');assert entered.wait(1.)
        with pytest.raises(RuntimeError,match='not joined'):writer.close(timeout_sec=.01)
        assert not writer.report()['joined']
        with pytest.raises(RuntimeError,match='closed'):writer.submit('late')
        release.set()
        with pytest.raises(RuntimeError,match='injected disk error'):writer.close(timeout_sec=1.)
        assert writer.report()['joined'] and writer.report()['written']==0
        assert sink.closed
    finally:
        release.set()
        try:writer.close(timeout_sec=2.)
        except RuntimeError:pass


def test_probe_journal_preserves_immutable_submission_and_order(tmp_path):
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    try:
        value=dict(nested=dict(capture_ns=17))
        probe._write('first',value);value['nested']['capture_ns']=99
        probe._write('second',dict(capture_ns=18))
        probe.restore_history(receiver_joined=True)
        rows=[json.loads(x) for x in (tmp_path/'observations.jsonl').read_text().splitlines()]
        assert rows==[dict(kind='first',value=dict(nested=dict(capture_ns=17))),
                      dict(kind='second',value=dict(capture_ns=18))]
        assert probe.journal.report()['written']==2
    finally:probe.close_log();probe.destroy_node();context.try_shutdown()


def test_failed_journal_stays_failed_but_cleanup_rpc_receiver_remains_alive(tmp_path,monkeypatch):
    from rclpy.node import Node
    from rclpy.executors import SingleThreadedExecutor
    from rclpy.clock import Clock
    from rclpy.clock_type import ClockType
    from std_srvs.srv import Trigger
    from probe_navigation_13_5 import ProbeReceiver
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    peer=Node('probe_cleanup_rpc_peer',context=context)
    peer_executor=SingleThreadedExecutor(context=context);peer_executor.add_node(peer)
    release=threading.Event();original=probe.raw.write;receiver=None
    def blocked(value):
        assert release.wait(3.)
        return original(value)
    monkeypatch.setattr(probe.raw,'write',blocked)
    def reply(request,response):
        response.success=True;response.message='explicit cleanup acknowledgement'
        return response
    peer.create_service(Trigger,'/probe_cleanup_rpc_fixture',reply)
    client=probe.create_client(Trigger,'/probe_cleanup_rpc_fixture')
    def overflow():
        timer.cancel()
        for index in range(257):probe._write('overflow_fixture',dict(index=index))
    timer=probe.create_timer(.01,lambda:probe._dispatch(overflow),clock=Clock(clock_type=ClockType.STEADY_TIME))
    try:
        receiver=ProbeReceiver(probe)
        deadline=time.monotonic()+1.
        while not probe.journal.report()['error'] and time.monotonic()<deadline:time.sleep(.005)
        assert 'capacity' in probe.fault()
        time.sleep(.02)
        receiver.check() # sticky recording failure must not kill the RPC executor
        assert receiver.thread.is_alive()
        assert probe.journal_failure['callback']=='overflow'
        deadline=time.monotonic()+1.
        while not client.service_is_ready() and time.monotonic()<deadline:
            peer_executor.spin_once(timeout_sec=.005)
        assert client.service_is_ready()
        future=client.call_async(Trigger.Request())
        while not future.done() and time.monotonic()<deadline:
            peer_executor.spin_once(timeout_sec=.005);receiver.check()
        assert future.done() and future.result().success
        assert 'capacity' in probe.fault(),'cleanup acknowledgement erased the failed acceptance'
        assert probe.journal.report()['error'],'journal failure must remain sticky'
    finally:
        release.set()
        if receiver:assert receiver.shutdown(timeout_sec=2.)
        try:probe.close_log()
        except RuntimeError:pass # asserted failure remains failed; release only owned resources
        probe.destroy_node();peer_executor.shutdown(timeout_sec=2.);peer.destroy_node();context.try_shutdown()


def test_actual_dds_native_ingress_continues_while_sink_waits(tmp_path,nav_robot_model,monkeypatch):
    from carry_feedback_peer import CarryFeedbackPeer
    from guard_fixture import bundle
    from probe_navigation_13_5 import ProbeReceiver
    peer=CarryFeedbackPeer(nav_robot_model.model_sha256,bundle(nav_robot_model).joints.data['position'])
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    entered,release=threading.Event(),threading.Event();original=probe.raw.write
    def blocked(value):
        entered.set();assert release.wait(3.)
        return original(value)
    monkeypatch.setattr(probe.raw,'write',blocked)
    receiver=ProbeReceiver(probe)
    try:
        assert entered.wait(2.)
        deadline=time.monotonic()+1.;first=None
        while first is None and time.monotonic()<deadline:
            with probe._lock:first=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
            time.sleep(.005)
        assert first is not None
        time.sleep(.25)
        receiver.check()
        with probe._lock:latest=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
        assert latest.stamp_ns>first.stamp_ns
        assert time.monotonic_ns()-latest.received_ns<100_000_000
        assert probe.journal.report()['written']==0
        release.set()
        assert receiver.shutdown(timeout_sec=2.)
        probe.restore_history(receiver_joined=True)
        assert probe.journal.report()['submitted']==probe.journal.report()['written']
    finally:
        release.set()
        assert receiver.shutdown(timeout_sec=2.)
        probe.close_log();probe.destroy_node();context.try_shutdown();peer.close()


@pytest.mark.parametrize('legacy_boundary',[None,'inbox','record'])
def test_heavy_frame_serialization_cannot_own_native_ingress_group(tmp_path,nav_robot_model,monkeypatch,legacy_boundary):
    from carry_feedback_peer import CarryFeedbackPeer
    from guard_fixture import bundle
    from probe_navigation_13_5 import ProbeReceiver
    peer=CarryFeedbackPeer(nav_robot_model.model_sha256,bundle(nav_robot_model).joints.data['position'])
    context=Context();rclpy.init(context=context)
    probe=NavigationProbe(tmp_path,engine='gazebo',bounded_history=True,context=context)
    entered,release=threading.Event(),threading.Event()
    import probe_navigation_13_5 as api
    original=api.json.dumps
    def slow_encoding(value,*args,**kwargs):
        if isinstance(value,dict) and value.get('kind')=='frame':
            entered.set();assert release.wait(3.)
        return original(value,*args,**kwargs)
    monkeypatch.setattr(api.json,'dumps',slow_encoding)
    if legacy_boundary=='inbox':
        from functools import wraps
        frame=probe._frame
        @wraps(frame)
        def legacy_frame():
            with probe._lock:return frame()
        monkeypatch.setattr(probe,'_frame',legacy_frame)
    elif legacy_boundary=='record':
        write=probe._write
        def legacy_write(kind,value):
            with probe._record_lock:return write(kind,value)
        monkeypatch.setattr(probe,'_write',legacy_write)
    receiver=ProbeReceiver(probe)
    try:
        deadline=time.monotonic()+2.
        first=None
        while first is None and time.monotonic()<deadline:
            with probe._lock:first=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
            time.sleep(.01)
        assert first is not None
        # Force a complete frame from the independent peer's canonical samples.
        complete=bundle(nav_robot_model)
        with probe._lock:
            for key in ('joints','imu','contacts','body','scan','carry'):
                probe.inbox.samples[key]=getattr(complete,key)
            probe.native_com=complete.body
        # Exercise actual JSON serialization, including its record lock boundary.
        assert entered.wait(1.)
        # Counterfactuals must still fail native ingress freshness. The new
        # callback lock scope prevents the record-lock case from also owning
        # the inbox, but its blocked serial sensor callback remains unhealthy.
        if legacy_boundary=='inbox':
            time.sleep(.05)
            acquired=probe._lock.acquire(timeout=.05)
            if acquired:probe._lock.release()
            assert not acquired,'counterfactual did not reproduce the old lock coupling'
            return
        if legacy_boundary=='record':
            time.sleep(.05)
            assert probe._lock.acquire(timeout=.05),'recording acquired the inbox indirectly'
            try:first=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
            finally:probe._lock.release()
            time.sleep(.25)
            with probe._lock:latest=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
            assert latest.stamp_ns==first.stamp_ns,'counterfactual no longer blocks serial ingress'
            assert time.monotonic_ns()-latest.received_ns>200_000_000,'stale counterfactual was treated as fresh'
            return
        assert probe._lock.acquire(timeout=.05),'encoding still owns inbox indirectly'
        try:first=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
        finally:probe._lock.release()
        time.sleep(.25)
        with probe._lock:latest=probe.inbox.bundle(probe.get_clock().now().nanoseconds).joints
        assert latest.stamp_ns>first.stamp_ns,'heavy frame callback still blocks native ingress'
        assert time.monotonic_ns()-latest.received_ns<100_000_000
    finally:
        release.set()
        assert receiver.shutdown(timeout_sec=3.)
        probe.close_log();probe.destroy_node();context.try_shutdown();peer.close()
