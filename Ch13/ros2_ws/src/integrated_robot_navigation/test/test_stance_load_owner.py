"""Ownership/rate scope only; synthetic feedback cannot prove physical lift."""
import inspect,json
from dataclasses import replace
import numpy as np
import pytest
from integrated_robot_navigation.gait import CrawlMachine
from integrated_robot_navigation.carry_profile import default_limits
from gait_fixture import IdealFeedback
from test_stance_load_transfer import helper,inputs


def configured(model):
    assert 'load_transfer_policy' in inspect.signature(CrawlMachine).parameters, 'stance load feedback has no serial reference owner'
    model=helper(model).model;plant=IdealFeedback(model)
    machine=CrawlMachine(model,default_limits(),load_transfer_policy='stance_admittance')
    machine.reset(plant.state,plant.ros,plant.wall)
    args=inputs(model);contacts={**plant.state.contacts.data,'forces':tuple(args['forces'])}
    plant.state=replace(plant.state,contacts=replace(plant.state.contacts,data=contacts))
    machine.state='CRAWL';machine.phase='SHIFT';machine._unload_start=plant.ros
    return machine,plant,args


def test_held_capture_cannot_repeat_stance_integration(nav_robot_model):
    m,p,a=configured(nav_robot_model);before={f:v.copy() for f,v in m._targets.items()}
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    after={f:v.copy() for f,v in m._targets.items()}
    assert all(np.array_equal(before['rr_foot'],after['rr_foot']) for _ in [0])
    assert any(abs(after[f][2]-before[f][2])>0 for f in m.model.feet)
    assert max(abs(after[f][2]-before[f][2]) for f in m.model.feet)<=.00004000001
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    assert all(np.array_equal(after[f],m._targets[f]) for f in m.model.feet)


@pytest.mark.parametrize('state',[dict(calibrating=True),dict(stopping=True),dict(state='FAULT'),dict(phase='SWING')])
def test_no_admittance_after_its_unload_scope(nav_robot_model,state):
    m,p,a=configured(nav_robot_model);before={f:v.copy() for f,v in m._targets.items()}
    for k,v in state.items():setattr(m,k,v)
    m._transfer_stance_load(p.state,a['joints'],p.pose,a['points'],'rr_foot',.02)
    assert all(np.array_equal(before[f],m._targets[f]) for f in m.model.feet)


def test_stance_correction_cannot_wind_up_beyond_reset_reference(nav_robot_model):
    m,p,a=configured(nav_robot_model);origin=dict(m._stance_reference_z)
    for capture in range(1500):
        contact=replace(p.state.contacts,sequence=capture,stamp_ns=p.ros+capture*20_000_000)
        m._transfer_stance_load(replace(p.state,contacts=contact),a['joints'],p.pose,a['points'],'rr_foot',.02)
    assert max(abs(m._targets[f][2]-origin[f]) for f in m.model.feet)<=.01000000001
    assert m._stance_reference_z==origin  # transient offsets cannot redefine neutral preload


@pytest.mark.parametrize('engine,g2',[('gazebo',True),('gazebo',False),('mujoco',True),('mujoco',False)])
def test_real_config_selects_only_explicit_gazebo_g2(tmp_path,nav_robot_model,engine,g2):
    import rclpy
    from rclpy.context import Context
    from rclpy.parameter import Parameter
    from integrated_robot_navigation.crawl_controller import CrawlController
    from test_execution_admission_contract import fixture
    model=helper(nav_robot_model).model;profile,expected=fixture(tmp_path,model,engine)
    expected={**expected,'control_clock':'relay100'}
    ctx=Context();rclpy.init(context=ctx)
    node=CrawlController(model,profile,engine,context=ctx,
        cli_args=['--ros-args','-r','/clock:=/navigation/control_clock'],parameter_overrides=[
            Parameter('validation_mode',value=True),Parameter('g2_validation_mode',value=g2),
            Parameter('control_clock_mode',value='relay100'),
            Parameter('native_execution_profile',value=json.dumps(expected) if g2 else '')])
    numeric=None
    try:
        node.trigger_configure();assert node.machine is not None
        assert getattr(node.machine,'load_transfer_policy',None)==('coupled_contact' if engine=='gazebo' and g2 else 'geometric')
        if engine=='gazebo' and g2:
            from integrated_robot_navigation.native_reference import NativeReferenceEnvelope
            from std_srvs.srv import Trigger
            from integrated_robot_navigation.load_process import assess_numeric_close
            assert node.machine._load_transfer.preparation['solver_verified'] is True
            assert node.mass_evaluator is not None
            numeric=node.machine._load_transfer
            geometry=node.machine._reference_geometry
            assert isinstance(geometry,NativeReferenceEnvelope)
            assert numeric.asynchronous is True
            assert numeric.command_space=='stance_xyz'
            assert numeric.prepare()['library_sha256']==node.mass_evaluator.provenance['library_sha256']
            assert numeric.prepare()['reference_library_sha256']==geometry.provenance['library_sha256']
            from integrated_robot_navigation.native_xyz import optimizer_library_path
            import hashlib
            assert numeric.prepare()['optimization_backend']=='qpmad_1_5_1_native'
            assert numeric.prepare()['optimization_library_sha256']==hashlib.sha256(optimizer_library_path().read_bytes()).hexdigest()
            node.active=True
            rejected=node._stop_numeric(Trigger.Request(),Trigger.Response())
            assert not rejected.success and numeric.snapshot()['alive']
            node.active=False
            stopped=node._stop_numeric(Trigger.Request(),Trigger.Response())
            assert stopped.success and assess_numeric_close(json.loads(stopped.message),model.model_sha256)
            assert json.loads(stopped.message)['reference_geometry_closed'] is True
            assert json.loads(stopped.message)['optimizer_closed'] is True
            assert not geometry._finalize.alive
        assert node.command_publication_count==0 and not node.active
    finally:
        node.destroy_node();ctx.try_shutdown()
    if numeric is not None:
        closed=numeric.close()
        assert closed['acknowledged'] and closed['parent_reaped'] and not closed['pending']
