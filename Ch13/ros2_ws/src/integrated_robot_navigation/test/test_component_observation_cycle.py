"""A 50Hz observer wake must drain received FIFO events, not drop pulses."""
import pytest
from integrated_robot_navigation import contact_component as module
from integrated_robot_navigation.samples import Sample
from test_contact_component import frame,tracker


def api():
    assert hasattr(module,'observe_contact_cycle'), 'component consumes only one already-received capture per throttled wake'
    return module.observe_contact_cycle


def prepared(model):
    join=module.ComponentCaptureJoiner();first=frame(model)
    for k in join.keys:join.receive(k,Sample(**first['samples'][k]))
    assert join.begin(first['ros_ns'],first['wall_ns'])
    return join,tracker(model)


def test_one_cycle_drains_coherent_existing_burst_and_preserves_high_force_reset(nav_robot_model):
    consume=api();join,value=prepared(nav_robot_model);foot=nav_robot_model.feet[0]
    for offset,force in ((20,0.),(40,30.),(60,0.)):
        sample=frame(nav_robot_model,1_000_000_000+offset*1_000_000,10_000_000_000+offset*1_000_000,foot,.006,force)
        for k in join.keys:join.receive(k,Sample(**sample['samples'][k]))
    assert not consume(value,lambda:join.take(1_060_000_000,10_060_000_000))
    assert value.samples==3 and not value.lifted
    assert value.low_since[foot]==(1_060_000_000,10_060_000_000)
    assert join.report()['emitted']==4 and not join.history['contacts']
    assert join.report()['capture_slop_ns']==40_000_000 and join.report()['dual_max_age_ns']==200_000_000


def test_batch_cannot_skip_expired_old_capture_for_new_fresh_one(nav_robot_model):
    consume=api();join,value=prepared(nav_robot_model)
    old=frame(nav_robot_model,1_080_000_000,10_080_000_000)
    join.receive('contacts',Sample(**old['samples']['contacts']))
    new=frame(nav_robot_model,1_280_000_001,10_280_000_001)
    for k in join.keys:join.receive(k,Sample(**new['samples'][k]))
    with pytest.raises(ValueError,match='pending contact expired'):
        consume(value,lambda:join.take(1_280_000_001,10_280_000_001))
    assert value.samples==0 and join.report()['error']
