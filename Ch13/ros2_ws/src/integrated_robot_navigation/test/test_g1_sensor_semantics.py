"""Synthetic unit fixtures only: arithmetic is not native G1 provenance.

Breaks caught: force/axis/name swaps, self-hitting scan, missing physical lift,
unobserved collision and counting intentional teardown as operational data.
"""
from copy import deepcopy
from dataclasses import asdict
import math
import numpy as np
import pytest

from guard_fixture import bundle
from integrated_robot_navigation.leg_kinematics import ik_leg
from integrated_robot_navigation.support import center_of_mass
from test_native_verdicts import api

WORLD = '''<mujoco><worldbody>
<geom name="north" type="box" pos="0 4.7 .6" size="4.7 .05 .6"/>
<geom name="south" type="box" pos="0 -4.7 .6" size="4.7 .05 .6"/>
<geom name="east" type="box" pos="4.7 0 .6" size=".05 4.7 .6"/>
<geom name="west" type="box" pos="-4.7 0 .6" size=".05 4.7 .6"/>
</worldbody></mujoco>'''


@pytest.fixture
def observed(nav_robot_model):
    model = nav_robot_model
    samples = asdict(bundle(model))
    samples['joints']['data']['position'].update(gripper_left_joint=.015, gripper_right_joint=.015)
    pose = np.eye(4)
    pose[2, 3] = .46
    com = center_of_mass(model, samples['joints']['data']['position'], pose)
    samples['native_com'] = {**samples['body'], 'data': tuple(com)}
    weight = sum(mass for mass, _ in model.masses.values())*9.81
    points = samples['contacts']['data']['points']
    # Independent static first-moment balance for the rectangular support.
    samples['contacts']['data']['forces'] = tuple(weight/4*(1+com[0]*x/.25**2+com[1]*y/.18**2)
                                                  for x, y, _ in points)
    # Independent 2D room-ray fixture: lidar mount x=-.18, no roll/yaw.
    ranges = []
    for i in range(360):
        direction = (math.cos(-math.pi+i*math.tau/360), math.sin(-math.pi+i*math.tau/360))
        distances = [(side-origin)/component for origin, component in zip((-.18, 0.), direction)
                     for side in (-4.65, 4.65) if abs(component) > 1e-12
                     and (side-origin)/component > 0]
        ranges.append(min(distances))
    samples['scan']['data'].update(ranges=tuple(ranges), hits=(True,)*360)
    frames = []

    def row(index, stage, state, phase='', lifted=False):
        value = deepcopy(samples)
        stamp, receipt = 1_000_000_000+index*100_000_000, 10_000_000_000+index*100_000_000
        for sample in value.values():
            sample.update(stamp_ns=stamp, received_ns=receipt, sequence=stamp)
        if stage == 'calibrate':
            body = value['body']['data']
            body['position'] = (-.05, -.03, .46)
            q = value['joints']['data']['position']
            for foot, (x, y, _) in zip(model.feet, points):
                z = .46-.5*math.cos(.5) + (.006 if foot == 'fl_foot' and lifted else 0.)
                names = tuple(foot[:2]+'_'+p+'_joint' for p in ('hip', 'thigh', 'calf'))
                angles = ik_leg(model, foot, (x+.05, y+.03, z-.46), tuple(q[n] for n in names))
                q.update(zip(names, angles))
            local_pose = pose.copy()
            local_pose[:2, 3] = (-.05, -.03)
            value['native_com']['data'] = center_of_mass(model, q, local_pose)
            if lifted:
                value['contacts']['data'].update(forces=(weight/3, 0., weight/3, weight/3),
                    touching=(True, False, True, True))
        return dict(stage=stage, ros_ns=stamp, wall_ns=receipt, samples=value,
                    crawl=dict(state=state, phase=phase, swing_foot='fl_foot' if lifted else '',
                               stopped=state == 'STAND'))

    frames += [row(i, 'stand', 'STAND') for i in range(101)]  # 10s, unique samples
    frames += [row(i, 'calibrate', 'CALIBRATING', 'SWING', True) for i in range(111, 114)]
    frames += [row(i, 'calibrate', 'STAND') for i in range(114, 118)]
    return dict(root_source='native_ground_truth', urdf=model.urdf, frames=frames,
        phases={'stand': dict(ros_duration_s=10., wall_duration_s=10.)})


def test_semantics_require_real_measurements_not_ready_or_commands(observed):
    result = api().assess_g1_sensors(observed, WORLD, 'mujoco')
    assert all(result['checks'].values()), result
    assert not any(api().assess_g1_sensors({'frames': []}, WORLD, 'mujoco')['checks'].values())


@pytest.mark.parametrize('failure,check', [
    ('force_scale', 'contact_frames_force'), ('contact_names', 'contact_frames_force'),
    ('imu_axes', 'imu_frame'), ('scan_self', 'scan_world_not_self'),
    ('no_lift', 'contact_lift'), ('swapped_lift', 'contact_lift'),
    ('unexpected', 'carry_collision_free'), ('geometry', 'carry_collision_free'),
    ('duplicates', 'contact_frames_force'), ('command_source', 'contact_frames_force')])
def test_sensor_semantics_reject_specific_fault(observed, failure, check):
    for frame in observed['frames']:
        samples = frame['samples']
        if failure == 'force_scale':
            samples['contacts']['data']['forces'] = [f*1.2 for f in samples['contacts']['data']['forces']]
        elif failure == 'contact_names':
            samples['contacts']['data']['names'] = ('fl_foot', 'fr_foot', 'rr_foot', 'rl_foot')
        elif failure == 'imu_axes':
            samples['imu']['data']['acceleration'] = (9.81, 0., 0.)
        elif failure == 'scan_self':
            samples['scan']['data']['ranges'] = (.2,)*360
        elif failure == 'no_lift':
            frame['stage'], frame['crawl']['state'] = 'stand', 'STAND'
        elif failure == 'swapped_lift' and frame['crawl']['phase'] == 'SWING':
            samples['contacts']['data'].update(forces=(0., 50., 50., 50.), touching=(False, True, True, True))
        elif failure == 'unexpected':
            samples['contacts']['data']['unexpected_contacts'] = 1
        elif failure == 'duplicates':
            for sample in samples.values():
                sample['stamp_ns'] = 1_000_000_000
        elif failure == 'command_source':
            observed['root_source'] = 'command_integrated'
    if failure == 'geometry':
        observed['urdf'] = observed['urdf'].replace('size="0.60 0.30 0.15"', 'size="0.60 0.30 3.0"')
    result = api().assess_g1_sensors(observed, WORLD, 'mujoco')
    assert result['checks'][check] is False, result


def test_operational_scope_keeps_faults_but_excludes_explicit_teardown():
    frames = [dict(stage='bootstrap'), dict(stage='stand', fault=True),
              dict(stage='calibrate'), dict(stage='shutdown', stale=True)]
    assert api().operational_frames(frames) == frames[1:3]


def test_unknown_measurement_stage_is_not_silently_filtered():
    with pytest.raises(ValueError):
        api().operational_frames([dict(stage='stand'), dict(stage='unknown')])


@pytest.mark.parametrize('field', ['ros_duration_s', 'wall_duration_s'])
def test_static_phase_must_really_run_ten_seconds(observed, field):
    observed['phases']['stand'][field] = 9.999
    assert not any(api().assess_g1_sensors(observed, WORLD, 'mujoco')['checks'].values())


@pytest.mark.parametrize('fault', ['', 'missing', 'stamp', 'axis', 'nan', 'frame', 'epoch'])
def test_imu_uses_same_capture_native_qvel_not_later_body_cache(observed, fault):
    """Catch asynchronous-cache comparison without weakening gyro error .02."""
    references = []
    for row in observed['frames']:
        imu = row['samples']['imu']
        # Literal synthetic dynamic case: later body has changed by .04rad/s.
        if row['stage'] == 'calibrate':
            imu['data']['angular_velocity'] = (.01, -.01, .002)
            row['samples']['body']['stamp_ns'] += 34_000_000
            row['samples']['body']['data']['angular_velocity'] = (.01, .03, .002)
        references.append(dict(capture_ns=imu['stamp_ns'], epoch=0,
            sequence=imu['sequence'], frame_id='base_link',
            source='mujoco_free_joint_qvel', angular_velocity=list(imu['data']['angular_velocity'])))
    target = references[-1]
    if fault == 'missing':
        references.pop()
    elif fault == 'stamp':
        target['capture_ns'] += 1  # exact capture required, no nearest substitution
    elif fault == 'axis':
        target['angular_velocity'] = (.01, .010001, .002)
    elif fault == 'nan':
        target['angular_velocity'] = (float('nan'), 0., 0.)
    elif fault == 'frame':
        target['frame_id'] = 'odom'
    elif fault == 'epoch':
        target['epoch'] = 1
    observed['native_body_references'] = references
    result = api().assess_g1_sensors(observed, WORLD, 'mujoco')
    assert result['checks']['imu_frame'] is (fault == ''), result
    if fault == '':
        assert result['max_gyro_body_error_rps'] == 0.
        assert result['gyro_reference_unique_captures'] == len(references)


@pytest.mark.parametrize('fault', ['', 'arm_error', 'arm_speed', 'gripper_error',
                                   'gripper_speed', 'age', 'ready_only', 'duplicates'])
def test_raw_carry_hold_is_independent_of_ready_flag(observed, fault):
    for row in observed['frames']:
        sample = row['samples']['joints']
        data = sample['data']
        if fault == 'arm_error':
            data['position']['arm_joint_1'] = .030001
        elif fault == 'arm_speed':
            data['velocity']['arm_joint_1'] = .020001
        elif fault == 'gripper_error':
            data['position']['gripper_left_joint'] = .017001
        elif fault == 'gripper_speed':
            data['velocity']['gripper_left_joint'] = .005001
        elif fault == 'age':
            sample['received_ns'] -= 200_000_001
        elif fault == 'ready_only':
            data['position']['arm_joint_2'] = .9  # READY remains true throughout
        elif fault == 'duplicates':
            sample['stamp_ns'] = 1_000_000_000
    result = api().assess_carry_hold(observed, (0., 1.2, -2., 0., .8, 0.))
    assert result['passed'] is (fault == ''), result
