#!/usr/bin/env python3
"""Reassess recorded measurements, never command odometry or declared PASS bits.

Acceptance arithmetic is separate from the runner's native process/library and
artifact provenance audit. Unit fixtures cannot establish those native facts.
"""
import math
import itertools
import re
import xml.etree.ElementTree as ET

import numpy as np

from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.samples import Sample, sample_valid
from integrated_robot_navigation.projection import body_rotation, project_body
from integrated_robot_navigation.leg_kinematics import fk_leg
from integrated_robot_navigation.support import center_of_mass, support_margin

FRAME_REQUIRED = frozenset({'native_observations', 'sensor_freshness', 'stability',
    'contact_support', 'native_com_consistent', 'stance_slip', 'joint_envelope'})
G2_REQUIRED = FRAME_REQUIRED | {'stand10', 'forward', 'left', 'right', 'stopped'}
G1_SENSOR_REQUIRED = frozenset({'contact_frames_force', 'imu_frame', 'scan_world_not_self',
                                'contact_lift', 'carry_collision_free'})


def operational_frames(frames):
    """Explicit stages only; never drop an operational fault or outlier."""
    if any(row.get('stage') not in ('bootstrap', 'stand', 'calibrate', 'shutdown') for row in frames):
        raise ValueError('unknown measurement stage cannot be filtered')
    return [row for row in frames if row.get('stage') in ('stand', 'calibrate')]


def assess_carry_hold(observations, arm_q):
    report = dict(passed=False)
    try:
        if observations.get('root_source') != 'native_ground_truth' or len(arm_q) != 6:
            return report
        targets = dict(zip(('arm_joint_'+str(i) for i in range(1, 7)), arm_q))
        if not all(math.isfinite(value) for value in arm_q):
            return report
        frames = operational_frames(observations['frames'])
        captures = {r['samples']['joints']['stamp_ns'] for r in frames}
        if len(captures) < 30:
            return report
        errors, speeds, grip_errors, grip_speeds = [], [], [], []
        fresh = True
        for row in frames:
            sample = Sample(**row['samples']['joints'])
            valid, _ = sample_valid(sample, row['ros_ns'], row['wall_ns'], 0, max_age_ns=200_000_000)
            fresh &= valid
            q, qd = sample.data['position'], sample.data['velocity']
            errors.extend(abs(q[name]-target) for name, target in targets.items())
            speeds.extend(abs(qd[name]) for name in targets)
            grip_errors.extend(abs(q[name]-.015) for name in ('gripper_left_joint', 'gripper_right_joint'))
            grip_speeds.extend(abs(qd[name]) for name in ('gripper_left_joint', 'gripper_right_joint'))
        report.update(max_arm_error_rad=max(errors), max_arm_speed_rps=max(speeds),
            max_gripper_error_m=max(grip_errors), max_gripper_speed_mps=max(grip_speeds),
            unique_joint_captures=len(captures), passed=bool(fresh and max(errors) <= .03
                and max(speeds) <= .02 and max(grip_errors) <= .002 and max(grip_speeds) <= .005))
        return report
    except (ValueError, TypeError, KeyError, IndexError):
        return report


def _room_boxes(xml, engine):
    tree, boxes = ET.fromstring(xml), []
    for name in ('north', 'south', 'east', 'west'):
        if engine == 'mujoco':
            tag = tree.find(f"worldbody/geom[@name='{name}']")
            if tag is None or tag.get('type') != 'box':
                raise ValueError('bound G1 room wall missing')
            center = np.array(list(map(float, tag.get('pos').split())))
            half = np.array(list(map(float, tag.get('size').split())))
            if not np.allclose(list(map(float, tag.get('quat', '1 0 0 0').split())), [1, 0, 0, 0]):
                raise ValueError('G1 wall must be axis aligned')
        elif engine == 'gazebo':
            tag = tree.find(f"world/model[@name='{name}']/link/collision")
            pose = np.array(list(map(float, tag.findtext('pose').split())))
            if len(pose) != 6 or not np.allclose(pose[3:], 0.):
                raise ValueError('G1 wall must be axis aligned')
            center, half = pose[:3], np.array(list(map(float, tag.findtext('geometry/box/size').split())))/2
        else:
            raise ValueError('unknown native engine')
        if center.shape != (3,) or half.shape != (3,) or not np.isfinite([center, half]).all() or np.any(half <= 0):
            raise ValueError('invalid G1 wall dimensions')
        boxes.append((center-half, center+half))
    return boxes


def _box_scan(origin, rays, boxes):
    nearest = np.full(rays.shape[1], np.inf)
    for low, high in boxes:
        moving = np.abs(rays) > 1e-12
        with np.errstate(divide='ignore', invalid='ignore'):
            first, second = (low[:, None]-origin[:, None])/rays, (high[:, None]-origin[:, None])/rays
        near, far = np.minimum(first, second), np.maximum(first, second)
        inside = (origin >= low) & (origin <= high)
        near = np.where(moving, near, np.where(inside[:, None], -np.inf, np.inf))
        far = np.where(moving, far, np.where(inside[:, None], np.inf, -np.inf))
        enter, leave = near.max(axis=0), far.min(axis=0)
        distance = np.where(enter > 0, enter, leave)
        nearest = np.minimum(nearest, np.where((leave >= enter) & (distance > 0), distance, np.inf))
    return nearest


def _measured_self_collision_free(model, frames):
    """Offline URDF geometry at measured joints, NOT a stepped native engine.

    The reconstructed model has a fixed root. No free/root pose, velocity,
    external force or live engine data is written. World collisions must also
    be absent in the actual native unexpected-contact stream.
    """
    import mujoco
    tree = ET.fromstring(model.urdf)
    extension = ET.SubElement(tree, 'mujoco')
    ET.SubElement(extension, 'compiler', fusestatic='false', discardvisual='true')
    native = mujoco.MjModel.from_xml_string(ET.tostring(tree, encoding='unicode'))
    if native.nq != len(model.limits) or any(t == mujoco.mjtJoint.mjJNT_FREE for t in native.jnt_type):
        raise ValueError('offline geometry requires fixed root and scalar joints')
    data, pairs = mujoco.MjData(native), []
    for i, j in itertools.combinations(range(native.ngeom), 2):
        a, b = (int(native.body_weldid[native.geom_bodyid[g]]) for g in (i, j))
        pa, pb = (int(native.body_weldid[native.body_parentid[w]]) for w in (a, b))
        if a != b and a != pb and b != pa:
            pairs.append((i, j))
    if not pairs:
        return False
    previous = None
    for row in frames:
        q = row['samples']['joints']['data']['position']
        current = tuple(q[name] for name in model.limits)
        if current == previous:
            continue
        previous = current
        for name, value in zip(model.limits, current):
            if not math.isfinite(value) or not model.limits[name][0] <= value <= model.limits[name][1]:
                return False
            data.qpos[native.joint(name).qposadr[0]] = value
        mujoco.mj_forward(native, data)
        for i, j in pairs:
            if np.linalg.norm(data.geom_xpos[i]-data.geom_xpos[j]) > native.geom_rbound[i]+native.geom_rbound[j]+.01:
                continue
            distance = mujoco.mj_geomDistance(native, data, i, j, .01, None)
            if not math.isfinite(distance) or distance < .0001:
                return False
    return True


def assess_g1_sensors(observations, world_xml, engine):
    """Independent raw G1 semantics. Native provenance is checked separately."""
    checks = dict.fromkeys(G1_SENSOR_REQUIRED, False)
    report = dict(checks=checks, geometry_scope='offline_fixed_root_URDF_at_measured_joints')
    try:
        if observations.get('root_source') != 'native_ground_truth':
            return report
        timing = observations['phases']['stand']
        if any(type(timing[key]) not in (int, float) or not math.isfinite(timing[key])
               or timing[key] < 10. for key in ('ros_duration_s', 'wall_duration_s')):
            return report
        frames = operational_frames(observations['frames'])
        static = [row for row in frames if row['stage'] == 'stand']
        if (len(static) < 30 or len({r['samples']['body']['stamp_ns'] for r in static}) < 30
                or len({r['samples']['scan']['stamp_ns'] for r in static}) < 30
                or static[-1]['ros_ns']-static[0]['ros_ns'] < 9_600_000_000
                or static[-1]['wall_ns']-static[0]['wall_ns'] < 9_600_000_000):
            return report
        model, boxes = compile_model(observations['urdf']), _room_boxes(world_xml, engine)
        weight = sum(mass for mass, _ in model.masses.values())*9.81
        force_ok, imu_ok, scan_ok, clear = True, True, True, True
        weight_errors, accel_errors, gyro_errors, scan_errors = [], [], [], []
        body_references = {}
        for reference in observations.get('native_body_references', []):
            capture = reference['capture_ns']
            if type(capture) is not int or capture in body_references:
                raise ValueError('duplicate/invalid native body reference capture')
            body_references[capture] = reference
        gyro_captures, missing_gyro_references = set(), set()
        baseline, lifted = {}, set()
        for row in frames:
            samples = row['samples']
            body, contacts = samples['body']['data'], samples['contacts']['data']
            q = samples['joints']['data']['position']
            rotation, _ = body_rotation(body)
            pose = np.eye(4)
            pose[:3, :3], pose[:3, 3] = rotation, body['position']
            points, forces = np.asarray(contacts['points']), np.asarray(contacts['forces'])
            if points.shape != (4, 3) or forces.shape != (4,) or not np.isfinite(points).all() or not np.isfinite(forces).all():
                return report
            force_ok &= (tuple(contacts['names']) == model.feet and samples['contacts']['frame_id'] == 'odom'
                and np.all(forces >= 0) and list(forces >= 2.) == list(contacts['touching']))
            clear &= contacts['unexpected_contacts'] == 0
            centers = []
            for i, foot in enumerate(model.feet):
                angles = tuple(q[foot[:2]+'_'+part+'_joint'] for part in ('hip', 'thigh', 'calf'))
                center = (pose @ np.r_[fk_leg(model, foot, angles), 1.])[:3]
                centers.append(center)
                if forces[i] >= 2.:
                    force_ok &= np.linalg.norm(points[i, :2]-center[:2]) <= .01 and abs(points[i, 2]) <= .005
                if row['stage'] == 'stand':
                    baseline.setdefault(foot, center[2])
            imu = samples['imu']['data']
            imu_sample = samples['imu']
            capture = imu_sample['stamp_ns']
            gyro_captures.add(capture)
            reference = body_references.get(capture)
            if engine == 'mujoco' and (body_references or capture != samples['body']['stamp_ns']):
                if reference is None:
                    missing_gyro_references.add(capture)
                    imu_ok = False
                    expected_gyro = np.full(3, np.nan)
                else:
                    expected_gyro = np.asarray(reference['angular_velocity'], dtype=float)
                    imu_ok &= (reference['source'] == 'mujoco_free_joint_qvel'
                        and reference['frame_id'] == 'base_link' and reference['epoch'] == 0
                        and type(reference['sequence']) is int and reference['sequence'] >= 0)
            else:
                # Synthetic synchronous fixtures and the Gazebo adapter contract.
                expected_gyro = np.asarray(body['angular_velocity'], dtype=float)
            actual_gyro = np.asarray(imu['angular_velocity'], dtype=float)
            if expected_gyro.shape != (3,) or actual_gyro.shape != (3,):
                raise ValueError('three gyro axes required')
            error = float(np.linalg.norm(actual_gyro-expected_gyro))
            gyro_errors.append(error if math.isfinite(error) else math.inf)
            imu_ok &= samples['imu']['frame_id'] == 'base_link' and gyro_errors[-1] <= .02
            if row['stage'] == 'stand':
                total = float(forces.sum())
                weight_errors.append(abs(total-weight)/weight)
                force_ok &= weight_errors[-1] <= .05 and total > 0
                cop = forces @ points[:, :2]/total
                force_ok &= np.linalg.norm(cop-np.asarray(samples['native_com']['data'])[:2]) <= .01
                accel_errors.append(float(np.linalg.norm(np.asarray(imu['acceleration'])-rotation.T @ [0., 0., 9.81])))
                imu_ok &= accel_errors[-1] <= .2
                scan = samples['scan']['data']
                angles = scan['angle_min']+np.arange(360)*scan['angle_increment']
                lidar = pose @ model.chains['lidar_link'].forward(q)
                rays = lidar[:3, :3] @ np.array([np.cos(angles), np.sin(angles), np.zeros(360)])
                expected = _box_scan(lidar[:3, 3], rays, boxes)
                ranges = np.asarray(scan['ranges'])
                if ranges.shape != (360,) or len(scan['hits']) != 360:
                    return report
                scan_errors.append(float(np.max(np.abs(ranges-expected))))
                scan_ok &= (samples['scan']['frame_id'] == 'lidar_link' and all(scan['hits'])
                    and np.isfinite(expected).all() and np.isfinite(ranges).all()
                    and scan_errors[-1] <= .03 and np.all(ranges >= scan['range_min'])
                    and np.all(ranges <= scan['range_max']))
            elif (row['crawl']['state'] == 'CALIBRATING' and row['crawl']['swing_foot'] == 'fl_foot'
                    and forces[1] < 2 and all(forces[i] >= 2 for i in (0, 2, 3))
                    and centers[1][2]-baseline['fl_foot'] >= .005):
                lifted.add(samples['contacts']['stamp_ns'])
        checks.update(contact_frames_force=bool(force_ok), imu_frame=bool(imu_ok),
            scan_world_not_self=bool(scan_ok), contact_lift=len(lifted) >= 3,
            carry_collision_free=bool(clear and _measured_self_collision_free(model, frames)))
        report.update(expected_weight_n=weight, max_weight_relative_error=max(weight_errors),
            max_gravity_vector_error_mps2=max(accel_errors),
            max_gyro_body_error_rps=max(gyro_errors) if all(map(math.isfinite, gyro_errors)) else None,
            gyro_reference_unique_captures=len(gyro_captures)-len(missing_gyro_references),
            missing_gyro_reference_captures=sorted(missing_gyro_references),
            max_world_scan_error_m=max(scan_errors), lifted_unique_captures=len(lifted))
        return report
    except (ValueError, RuntimeError, TypeError, KeyError, IndexError, AttributeError, ET.ParseError, np.linalg.LinAlgError):
        return dict(checks=dict.fromkeys(G1_SENSOR_REQUIRED, False), invalid_measurements=True)


def motion_phase(start, end, phase):
    start, end = np.asarray(start, dtype=float), np.asarray(end, dtype=float)
    if start.shape != (3,) or end.shape != (3,) or not np.isfinite([start, end]).all():
        return dict(passed=False, reason='invalid native pose')
    dx, dy = end[:2]-start[:2]
    yaw = math.atan2(math.sin(end[2]-start[2]), math.cos(end[2]-start[2]))
    if phase in ('forward', 'reverse'):
        target = .40 if phase == 'forward' else -.10
        longitudinal = math.cos(start[2])*dx+math.sin(start[2])*dy
        lateral = -math.sin(start[2])*dx+math.cos(start[2])*dy
        passed = abs(longitudinal-target) <= .05 and abs(lateral) <= .05 and abs(yaw) <= .10
        return dict(passed=bool(passed), longitudinal_m=float(longitudinal),
                    lateral_m=float(lateral), yaw_delta_rad=yaw, target_m=target)
    if phase not in ('left', 'right'):
        return dict(passed=False, reason='unknown measured phase')
    target = .30 if phase == 'left' else -.30
    drift = math.hypot(dx, dy)
    return dict(passed=abs(yaw-target) <= .10 and drift <= .05,
                yaw_delta_rad=yaw, drift_m=drift, target_rad=target)


def normal_teardown(record):
    native_codes = record.get('engine_returncodes', [])
    return (all(record.get(key) is True for key in ('runtime_exit', 'engine_exit', 'parent_reaped'))
            and record.get('launch_returncode') == 0
            and bool(native_codes) and all(type(code) is int and code == 0 for code in native_codes)
            and record.get('forced_cleanup') is False and record.get('residual_live_pids') == [])


def engine_returncodes(content, native_pids):
    codes = dict.fromkeys(native_pids)
    for pid in re.findall(r'process has finished cleanly \[pid (\d+)\]', content):
        if int(pid) in codes:
            codes[int(pid)] = 0
    for pid, code in re.findall(r'process has died \[pid (\d+), exit code (-?\d+)', content):
        if int(pid) in codes:
            codes[int(pid)] = int(code)
    return [codes[pid] for pid in native_pids]


def carry_terminal(record):
    return (record.get('terminal') is True and record.get('result_future_done') is True
            and record.get('result_status') == 4 and record.get('result_error_code') == 0
            and record.get('pending_uuid', 'missing') is None)


def assess_native_controls(records, model, mjcf):
    """Check raw scalar actuator observations against the exact engine model.

    This does not establish origin: the runner must independently attest the
    loaded native producer/library. Command-topic values alone cannot do that.
    """
    try:
        elements = list(ET.fromstring(mjcf).find('actuator'))
        expected = {element.get('joint'): (index, element) for index, element in enumerate(elements)}
        joints = {joint.get('name'): joint for joint in ET.fromstring(model.urdf).findall('joint')}
        if len(records) < 30 or set(expected) != set(model.limits) or len(expected) != len(elements):
            return False
        last_capture, last_sequence = -1, -1
        for row in records:
            if (row['schema'] != 1 or row['epoch'] != 0
                    or type(row['capture_ns']) is not int or row['capture_ns'] <= last_capture
                    or type(row['sequence']) is not int or row['sequence'] <= last_sequence):
                return False
            last_capture, last_sequence = row['capture_ns'], row['sequence']
            values = row['actuators']
            if len(values) != len(expected) or {value['joint_name'] for value in values} != set(expected):
                return False
            for value in values:
                name = value['joint_name']
                index, element = expected[name]
                lo, hi, speed, effort = model.limits[name]
                kind = 'slide' if joints[name].get('type') == 'prismatic' else 'hinge'
                if (element.tag != 'position' or value['control_kind'] != 'position'
                        or value['joint_type'] != kind or value['gear'] != 1.
                        or any(type(value[key]) is not int or value[key] != index
                               for key in ('actuator_id', 'ctrl_index', 'output_index'))
                        or value['force_limited'] is not True or value['ctrl_limited'] is not True):
                    return False
                scalars = [value[key] for key in ('position', 'velocity', 'ctrl', 'actuator_force',
                           'joint_force', 'kp', 'kv', 'gear')]
                force_range, ctrl_range = value['force_range'], value['ctrl_range']
                if (len(force_range) != 2 or len(ctrl_range) != 2
                        or not all(type(v) in (int, float) and math.isfinite(v)
                                   for v in scalars+force_range+ctrl_range)):
                    return False
                if (not np.allclose(force_range, list(map(float, element.get('forcerange').split())),
                                    atol=1e-10, rtol=0.)
                        or not np.allclose(ctrl_range, list(map(float, element.get('ctrlrange').split())),
                                           atol=1e-10, rtol=0.)
                        or not math.isclose(value['kp'], float(element.get('kp')), abs_tol=1e-10)
                        or not math.isclose(value['kv'], float(element.get('kv')), abs_tol=1e-10)
                        or max(abs(v) for v in force_range) > effort+1e-10
                        or not force_range[0]-1e-8 <= value['actuator_force'] <= force_range[1]+1e-8
                        or abs(value['joint_force']) > effort+1e-8
                        or not lo-1e-8 <= value['position'] <= hi+1e-8
                        or abs(value['velocity']) > speed+1e-8
                        or not lo <= value['ctrl'] <= hi
                        or not ctrl_range[0] <= value['ctrl'] <= ctrl_range[1]):
                    return False
        return True
    except (KeyError, TypeError, ValueError, AttributeError, ET.ParseError):
        return False


def assess_tf_ownership(records, model):
    """Require every model child and both odom siblings from one actual authority.

    Records must come from the audited native C++ process; graph endpoint counts
    are separate evidence and cannot attribute a TF message to a publisher.
    """
    try:
        expected = {joint.find('child').get('link'): (
            joint.find('parent').get('link'),
            '/tf_static' if joint.get('type') == 'fixed' else '/tf')
            for joint in ET.fromstring(model.urdf).findall('joint')}
        expected.update({child: ('odom', '/tf') for child in ('base_footprint', 'nav_base')})
        observed = {}
        for row in records:
            gid = row['gid']
            if (not isinstance(gid, str) or len(gid) not in (32, 48)
                    or not re.fullmatch('[0-9a-f]+', gid) or int(gid, 16) == 0
                    or type(row['source_timestamp']) is not int or row['source_timestamp'] <= 0
                    or type(row['stamp_ns']) is not int or row['stamp_ns'] < 0):
                return False
            child = row['child']
            if expected.get(child) != (row['parent'], row['topic']):
                return False
            observed.setdefault(child, set()).add(gid)
        return set(observed) == set(expected) and all(len(owners) == 1 for owners in observed.values())
    except (KeyError, TypeError, ValueError, AttributeError, ET.ParseError):
        return False


def assess_frames(observations, limits):
    checks = dict.fromkeys(FRAME_REQUIRED, False)
    frames = observations.get('frames', [])
    if observations.get('root_source') != 'native_ground_truth' or len(frames) < 30:
        return checks
    try:
        model = compile_model(observations['urdf'])
        anchors = {}
        healthy = dict.fromkeys(FRAME_REQUIRED, True)
        captures = set()
        for row in frames:
            samples = {key: Sample(**value) for key, value in row['samples'].items()}
            for key in ('joints', 'imu', 'contacts', 'body', 'scan', 'native_com'):
                ok, _ = sample_valid(samples[key], row['ros_ns'], row['wall_ns'], 0,
                                    max_age_ns=300_000_000 if key == 'scan' else 200_000_000)
                healthy['sensor_freshness'] &= ok
            body, contact = samples['body'].data, samples['contacts'].data
            q, qd = samples['joints'].data['position'], samples['joints'].data['velocity']
            captures.add(samples['body'].stamp_ns)
            rotation, (roll, pitch, _) = body_rotation(body)
            transform = np.eye(4)
            transform[:3, :3], transform[:3, 3] = rotation, body['position']
            healthy['stability'] &= (max(abs(roll), abs(pitch)) <= limits['max_roll_pitch']
                and limits['min_body_height_m'] <= body['position'][2] <= limits['max_body_height_m'])
            healthy['joint_envelope'] &= set(q) == set(model.limits) and set(qd) == set(q)
            for name, (lo, hi, speed, _) in model.limits.items():
                healthy['joint_envelope'] &= lo <= q[name] <= hi and abs(qd[name]) <= speed
            if row.get('crawl', {}).get('state') in ('CRAWL', 'CALIBRATING'):
                for name in model.joint_names:
                    lo, hi = limits['gait_joint_bounds'][name.split('_')[1]]
                    healthy['joint_envelope'] &= lo <= q[name] <= hi
            expected_com = np.asarray(center_of_mass(model, q, transform))
            native_com = np.asarray(samples['native_com'].data, dtype=float)
            healthy['native_com_consistent'] &= (native_com.shape == (3,)
                and np.linalg.norm(expected_com-native_com) <= .01
                and samples['native_com'].frame_id == 'odom')
            if (tuple(contact['names']) != model.feet or samples['contacts'].frame_id != 'odom'
                    or contact['unexpected_contacts'] != 0):
                healthy['contact_support'] = False
            loaded = [f >= limits['min_contact_force_n'] for f in contact['forces']]
            healthy['contact_support'] &= loaded == list(contact['touching'])
            swing = row.get('crawl', {}).get('swing_foot') or None
            support = [point for name, point, load in zip(model.feet, contact['points'], loaded)
                       if load and name != swing]
            healthy['contact_support'] &= len(support) >= 3 and support_margin(native_com, support) >= limits['min_support_margin_m']
            for foot, load in zip(model.feet, loaded):
                if foot == swing:
                    anchors.pop(foot, None)
                    continue
                angles = tuple(q[foot[:2]+'_'+part+'_joint'] for part in ('hip', 'thigh', 'calf'))
                point = (transform @ np.array((*fk_leg(model, foot, angles), 1.)))[:3]
                if load:
                    anchors.setdefault(foot, point.copy())
                    healthy['stance_slip'] &= np.linalg.norm(point-anchors[foot]) <= limits['max_stance_slip_m']
        healthy['native_observations'] &= len(captures) >= 30
        return {key: bool(value) for key, value in healthy.items()}
    except (ValueError, TypeError, KeyError, IndexError, np.linalg.LinAlgError):
        return checks  # malformed/missing raw measurements never become an empty PASS


def assess_crawl(observations, limits):
    checks = dict.fromkeys(G2_REQUIRED, False)
    checks.update(assess_frames(observations, limits))
    phases = observations.get('phases', {})
    for phase in ('forward', 'left', 'right'):
        try:
            checks[phase] = motion_phase(phases[phase]['start'], phases[phase]['end'], phase)['passed']
        except (KeyError, TypeError, ValueError):
            pass
    stand = phases.get('stand', {})
    checks['stand10'] = stand.get('ros_duration_s', 0.) >= 10. and stand.get('wall_duration_s', 0.) >= 10.
    tail = observations.get('stopped_frames', [])
    try:
        checks['stopped'] = (len(tail) >= 2 and tail[-1]['wall_ns']-tail[0]['wall_ns'] >= 1_000_000_000
                             and tail[-1]['ros_ns']-tail[0]['ros_ns'] >= 1_000_000_000)
        for row in tail:
            planar = project_body(Sample(**row['samples']['body'])).data
            checks['stopped'] &= (row['crawl']['stopped'] is True
                and math.hypot(*planar['linear_velocity'][:2]) <= limits['stopped_v_mps']
                and abs(planar['angular_velocity'][2]) <= limits['stopped_wz_rps']
                and all(row['samples']['contacts']['data']['touching']))
    except (ValueError, TypeError, KeyError, IndexError):
        checks['stopped'] = False
    return {key: bool(value) for key, value in checks.items()}
