"""Explicit benchmark contract; never infer a G2 physics mode from a ready flag."""
import re
import json


def normalize_execution_profile(value,engine):
    fields={'control_clock','position_reference_mode','dart_contact','native_physics_sha256'}
    if engine not in ('mujoco','gazebo') or not isinstance(value,dict) or set(value)!=fields:
        raise ValueError('complete engine execution profile required')
    if not isinstance(value['native_physics_sha256'],str) or not re.fullmatch('[0-9a-f]{64}',value['native_physics_sha256']):
        raise ValueError('bound native physics SHA256 required')
    modes=(value['control_clock'],value['position_reference_mode'],value['dart_contact'])
    if modes!=('native','native','native') and not (
            engine=='gazebo' and modes==('relay100','g1_ramp20ms','allowance50um') or
            engine=='mujoco' and modes==('relay100','native','native')):
        raise ValueError('unapproved or incomplete G2 execution profile')
    return dict(value)


def g2_execution_profile(scene,control_clock):
    return normalize_execution_profile(dict(control_clock=control_clock,
        position_reference_mode=scene.get('position_reference_mode','native'),
        dart_contact=scene.get('dart_contact_mode','native'),
        native_physics_sha256=scene.get('native_physics_sha256')),scene['engine'])


def read_g2_execution_scope(validation_mode,g2_mode,serialized,engine):
    if type(validation_mode) is not bool or type(g2_mode) is not bool or not isinstance(serialized,str):
        raise ValueError('typed G2 validation scope required')
    if not g2_mode:
        if serialized:raise ValueError('execution profile requires explicit G2 scope')
        return None
    if not validation_mode or not serialized:raise ValueError('G2 requires validation_mode and execution profile')
    return normalize_execution_profile(json.loads(serialized),engine)
