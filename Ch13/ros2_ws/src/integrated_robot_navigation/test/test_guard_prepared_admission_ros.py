"""Actual ROS mode service uses startup proof, never bulk artifact hashing."""
import importlib
from pathlib import Path
import rclpy
from rclpy.context import Context
from rclpy.parameter import Parameter
from test_prepared_admission import candidate
from test_motion_guard_ros import Rig


def test_real_mode_service_checks_prepared_file_identity_without_rehash(tmp_path,nav_robot_model,monkeypatch):
    module=importlib.import_module('integrated_robot_navigation.motion_guard')
    original=module.validate_profile;calls=[]
    def checked(*args,**kwargs):calls.append(None);return original(*args,**kwargs)
    monkeypatch.setattr(module,'validate_profile',checked)
    profile=candidate(tmp_path,nav_robot_model)
    context=Context();rclpy.init(context=context);guard=None;rig=None
    try:
        guard=module.MotionGuardNode(nav_robot_model,profile,'mujoco',context=context,
            parameter_overrides=[Parameter('use_sim_time',value=True)])
        assert len(calls)==1,'native proof was not prepared before starting control resources'
        rig=Rig(guard,nav_robot_model,context);rig.pump(.5)
        def forbidden(*args,**kwargs):raise AssertionError('control service rehashed native artifacts')
        monkeypatch.setattr(module,'validate_profile',forbidden)
        assert rig.mode('CRAWL').accepted
        (tmp_path/'frames.json').write_bytes(b'modified after startup')
        response=rig.mode('CRAWL')
        assert not response.accepted and response.message=='prepared_admission_changed'
        rig.pump(.1)
        assert rig.outputs[-1][1:]==(0.,0.)
    finally:
        if rig is not None:rig.close()
        elif guard is not None:guard.destroy_node()
        context.try_shutdown()
