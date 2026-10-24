"""G1 contact is not an endpoint; the owner must still confirm measured settle."""
import numpy as np
import pytest

from gait_fixture import IdealFeedback
from test_gait import machine
from test_inplace_calibration import trajectory, tick


def test_loaded_return_reaches_original_preload_with_continuous_bounded_velocity():
    value = trajectory()
    previous, velocity = value.z, value.velocity
    for index in range(1,4):
        tick(value,index,center=.027)
    previous, velocity = value.z,value.velocity
    complete = False
    for index in range(4,120):
        result = tick(value,index,forces=(30.,5.,30.,30.))
        assert abs(result.z-previous)/.02 <= .020000001
        assert abs(value.velocity-velocity)/.02 <= .20000001
        if result.z > .017+1e-12:
            assert not result.complete, '4N contact must not strand the original preload reference'
        previous,velocity = result.z,value.velocity
        if result.complete:
            complete = True
            break
    assert complete
    assert result.z == pytest.approx(.017,abs=1e-12)
    assert value.velocity == pytest.approx(0.,abs=1e-12)
    assert len(value.snapshot()['landing_captures']) == 3


def test_original_endpoint_without_unique_loaded_measurements_never_completes():
    value = trajectory()
    for index in range(1,4):tick(value,index,center=.027)
    for index in range(4,120):
        result=tick(value,index,forces=(30.,0.,30.,30.))
        assert not result.complete
    assert result.z == pytest.approx(.017,abs=1e-12)
    capture=1_000_000_000+120*20_000_000
    for index in range(120,125):
        assert not tick(value,index,forces=(30.,5.,30.,30.),capture=capture).complete
    assert not tick(value,125,forces=(30.,5.,30.,30.)).complete
    assert tick(value,126,forces=(30.,5.,30.,30.)).complete


def stand_candidate(model):
    plant=IdealFeedback(model)
    value=machine(model,plant)
    value.request_contact_calibration()
    for _ in range(400):
        result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state!='FAULT',result.reason
        plant.tick(value,result)
        if value._calibration_vertical is not None and result.state=='STAND':
            return plant,value,result
    pytest.fail('reference return candidate not reached')


def test_stand_candidate_retains_calibration_owner_and_never_starts_a_second_lift(nav_robot_model):
    plant,value,result=stand_candidate(nav_robot_model)
    assert value.calibrating, 'reference completion released ownership before measured wall settle'
    targets={name:point.copy() for name,point in value._targets.items()}
    for _ in range(10):
        result=value.advance(plant.state,(0.,0.,0.),plant.ros,plant.wall)
        assert result.state=='STAND' and result.phase=='STAND'
        assert value.calibrating
        for name,point in targets.items():assert np.allclose(value._targets[name],point,atol=1e-12)
        plant.tick(value,result)


def test_stand_candidate_still_obeys_original_wall_deadline(nav_robot_model):
    plant,value,result=stand_candidate(nav_robot_model)
    assert value.calibrating
    deadline=value.calibration_snapshot()['request']['deadline_wall_ns']
    with pytest.raises(ValueError,match='deadline'):
        value.confirm_contact_calibration(wall_ns=deadline)
    assert value.calibrating, 'deadline cannot release ownership as successful completion'


def test_owner_releases_calibration_only_after_full_measured_wall_settle(nav_robot_model):
    import rclpy
    from rclpy.context import Context
    from integrated_robot_navigation.crawl_controller import CrawlController
    plant,value,result=stand_candidate(nav_robot_model)
    # Let the ideal follower's final nonzero joint velocity become quiet.
    plant.tick(value,result)
    context=Context()
    rclpy.init(context=context)
    node=CrawlController(context=context)
    try:
        node.machine=value
        start=plant.wall
        for elapsed in (0,200_000_000,999_999_999):
            assert not node._stand_ready(plant.state,result,start+elapsed)
            assert value.calibrating
        assert node._stand_ready(plant.state,result,start+1_000_000_000)
        assert not value.calibrating, 'the actual owner never confirmed the successful measured lease'
    finally:
        node.destroy_node();context.try_shutdown()
