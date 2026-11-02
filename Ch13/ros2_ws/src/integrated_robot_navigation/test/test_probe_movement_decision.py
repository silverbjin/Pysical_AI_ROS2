"""A delayed journal frame must not replace fresher native ingress at decision.

The 04d65307 trace showed a 190ms-old frame and newer original body capture
already received. This is an offline interleaving regression, not gait proof.
"""
from dataclasses import asdict,replace
from threading import RLock
from types import SimpleNamespace

import pytest

from guard_fixture import bundle
from integrated_robot_navigation.carry_profile import default_limits
from integrated_robot_navigation.g2_sequence import movement_snapshot
from integrated_robot_navigation.observations import SensorInbox
from probe_navigation_13_5 import NavigationProbe


def fixture(model,monkeypatch,*,fresh=True):
    import probe_navigation_13_5 as api
    now=1_210_000_001;wall=10_210_000_001
    original=bundle(model);old=dict(ros_ns=1_190_000_000,wall_ns=10_190_000_000,
        stage='forward',samples=asdict(original),crawl=dict(stopped=False))
    inbox=SensorInbox(0)
    for key in ('body','contacts'):
        sample=getattr(original,key)
        if fresh:sample=replace(sample,stamp_ns=1_150_000_000,received_ns=10_195_000_000)
        inbox.receive(key,sample)
    records=[]
    probe=SimpleNamespace(_lock=RLock(),_record_lock=RLock(),inbox=inbox,frames=[old],stage='forward',
        motion=dict(crawl=dict(stopped=False)),
        callback_costs={},journal_costs={},slow_callbacks=[],slow_callback_count=0,
        get_clock=lambda:SimpleNamespace(now=lambda:SimpleNamespace(nanoseconds=now)),
        _write=lambda kind,value:records.append((kind,value)))
    probe.timing_snapshot=lambda:NavigationProbe.timing_snapshot(probe)
    monkeypatch.setattr(api.time,'monotonic_ns',lambda:wall)
    return probe,records,now,wall


def test_decision_uses_original_fresh_ingress_not_delayed_journal_frame(nav_robot_model,monkeypatch):
    probe,records,now,wall=fixture(nav_robot_model,monkeypatch)
    # Reproduce the old runner path: cached frame + later ROS now fails even
    # though its replacement has already arrived. Never retag the old sample.
    with pytest.raises(ValueError,match='body:ros_age'):
        movement_snapshot(NavigationProbe.latest_frame(probe),now,wall,default_limits())
    value=NavigationProbe.movement_decision(probe,default_limits())
    assert value['capture_ns']==1_150_000_000 and value['wall_ns']==wall
    assert probe.frames[0]['samples']['body']['stamp_ns']==1_000_000_000
    kind,row=records[-1]
    assert kind=='movement_decision' and row['ros_ns']==now and row['wall_ns']==wall
    assert row['samples']['body']['received_ns']==10_195_000_000
    assert row['accepted'] is True


def test_decision_without_fresh_native_ingress_still_fails_and_records_rejection(nav_robot_model,monkeypatch):
    probe,records,now,wall=fixture(nav_robot_model,monkeypatch,fresh=False)
    with pytest.raises(ValueError,match='body:ros_age'):
        NavigationProbe.movement_decision(probe,default_limits())
    kind,row=records[-1]
    assert kind=='movement_decision' and row['accepted'] is False
    assert row['samples']['body']['stamp_ns']==1_000_000_000
    assert 'body:ros_age' in row['error']
