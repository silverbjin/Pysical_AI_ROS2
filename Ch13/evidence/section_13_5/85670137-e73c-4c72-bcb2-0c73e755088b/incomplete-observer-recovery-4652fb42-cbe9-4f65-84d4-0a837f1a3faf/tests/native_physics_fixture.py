"""Real stepped Python MuJoCo fixture, NOT ROS-native G1/G2 acceptance.

Only normal keyframe initialization and actuator ctrl are written. Body pose,
velocities, contacts and encoders are read from physics, never ideal feedback.
Python3.3.7 and the ROS C++3.12.0 engine are intentionally distinguished.
"""
import time
import mujoco
import numpy as np
from integrated_robot_navigation.samples import Sample, SensorBundle


def measured_bundle(native, data, model):
    mujoco.mj_forward(native, data)
    stamp, receipt = int(round(data.time*1e9)), time.monotonic_ns()
    def sample(frame, value):
        return Sample(stamp, receipt, 0, stamp, frame, value)
    position, velocity = {}, {}
    for name in model.limits:
        joint = native.joint(name)
        position[name] = float(data.qpos[joint.qposadr[0]])
        velocity[name] = float(data.qvel[joint.dofadr[0]])
    base = native.body('base_link').id
    root = next(i for i in range(native.njnt) if native.jnt_type[i] == mujoco.mjtJoint.mjJNT_FREE)
    adr = native.jnt_dofadr[root]
    rotation = data.xmat[base].reshape(3, 3)
    w, x, y, z = data.xquat[base]
    body = dict(position=data.xpos[base].tolist(), orientation=(x, y, z, w),
        linear_velocity=(rotation.T @ data.qvel[adr:adr+3]).tolist(),
        angular_velocity=data.qvel[adr+3:adr+6].tolist(), child_frame_id='base_footprint')
    ground = native.geom('ground').id
    feet = [native.body(foot).id for foot in model.feet]
    forces, points, weighted = np.zeros(4), np.zeros((4, 3)), np.zeros(4)
    unexpected = 0
    for contact_index, contact in enumerate(data.contact):
        if contact.efc_address < 0:
            continue
        index, side = None, 0
        for i, foot in enumerate(feet):
            if contact.geom[0] == ground and native.geom_bodyid[contact.geom[1]] == foot:
                index, side = i, 1
            elif contact.geom[1] == ground and native.geom_bodyid[contact.geom[0]] == foot:
                index, side = i, -1
        if index is None:
            unexpected += 1
            continue
        wrench = np.zeros(6)
        mujoco.mj_contactForce(native, data, contact_index, wrench)
        world = side*contact.frame.reshape(3, 3).T @ wrench[:3]
        load = max(0., world[2])
        forces[index] += load
        points[index] += load*contact.pos
        weighted[index] += load
    for i, foot in enumerate(feet):
        points[i] = points[i]/weighted[i] if weighted[i] else data.xpos[foot]
    contacts = dict(names=model.feet, points=points.tolist(), forces=forces.tolist(),
                    touching=(forces >= 2.).tolist(), unexpected_contacts=unexpected)
    imu = dict(acceleration=data.sensor('navigation_accelerometer').data.tolist(),
               angular_velocity=data.sensor('navigation_gyro').data.tolist())
    return SensorBundle(sample('base_link', dict(position=position, velocity=velocity)),
        sample('base_link', imu), sample('odom', contacts), sample('odom', body), None, None)


def stand_probe(native, data, model, limits, *, duration_s=5.):
    from integrated_robot_navigation.gait import CrawlMachine
    for _ in range(round(10./native.opt.timestep)):
        mujoco.mj_step(native, data)
    bundle = measured_bundle(native, data, model)
    machine = CrawlMachine(model, limits)
    machine.reset(bundle, bundle.body.stamp_ns, time.monotonic_ns())
    anchors = np.array([data.xpos[native.body(foot).id].copy() for foot in model.feet])
    maximum_motion, maximum_error = 0., 0.
    final = machine._result()
    start = data.time
    while data.time-start < duration_s:
        bundle = measured_bundle(native, data, model)
        final = machine.advance(bundle, (0., 0., 0.), bundle.body.stamp_ns, time.monotonic_ns())
        if final.joint_targets is None:
            break
        for name, target in final.joint_targets.items():
            data.ctrl[native.actuator(name+'_motor').id] = target
            maximum_error = max(maximum_error, abs(target-bundle.joints.data['position'][name]))
        for _ in range(round(.02/native.opt.timestep)):
            mujoco.mj_step(native, data)
        actual = np.array([data.xpos[native.body(foot).id] for foot in model.feet])
        maximum_motion = max(maximum_motion, float(np.linalg.norm(actual-anchors, axis=1).max()))
    return dict(engine='python_mujoco_component_only', version=mujoco.__version__,
        state=final.state, reason=final.reason, duration_s=float(data.time-start),
        maximum_native_foot_motion_m=maximum_motion, maximum_joint_error_rad=maximum_error,
        final_q={name: float(data.qpos[native.joint(name).qposadr[0]]) for name in model.joint_names},
        final_ctrl={name: float(data.ctrl[native.actuator(name+'_motor').id]) for name in model.joint_names})


def calibration_probe(native, data, model, limits, *, trace=None):
    """Component only: physical carry hold during the unchanged contact shift."""
    from integrated_robot_navigation.gait import CrawlMachine, blend
    target = dict(zip(('arm_joint_'+str(i) for i in range(1, 7)), (0., 1.2, -2., 0., .8, 0.)))
    # Normal position-actuator trajectory from the keyframe, no qpos/root writes.
    for _ in range(round(10./native.opt.timestep)):
        for name, q in target.items():
            data.ctrl[native.actuator(name+'_motor').id] = q*blend(data.time/3.)
        mujoco.mj_step(native, data)
    bundle = measured_bundle(native, data, model)
    machine = CrawlMachine(model, limits)
    machine.reset(bundle, bundle.body.stamp_ns, time.monotonic_ns())
    start = data.time
    triggered, completed = False, False
    maximum_error, maximum_velocity = 0., 0.
    maximum_gripper_error, maximum_gripper_velocity = 0., 0.
    final = machine._result()
    while data.time-start < 20.:  # 10s stand + the runner's bounded 10s calibration
        bundle = measured_bundle(native, data, model)
        if not triggered and data.time-start >= 10.:
            machine.request_contact_calibration()
            triggered = True
        final = machine.advance(bundle, (0., 0., 0.), bundle.body.stamp_ns, time.monotonic_ns())
        if triggered and trace is not None:
            from integrated_robot_navigation.support import support_margin
            contact = bundle.contacts.data
            com = data.subtree_com[native.body('base_link').id].tolist()
            support = [point for point, touching in zip(contact['points'], contact['touching']) if touching]
            without_fl = [point for name, point, touching in zip(model.feet, contact['points'], contact['touching'])
                          if touching and name != 'fl_foot']
            trace.append(dict(time_s=float(data.time-start), state=final.state, phase=final.phase,
                swing=final.swing_foot, reason=final.reason, native_com=com,
                body=bundle.body.data, forces=contact['forces'], points=contact['points'],
                margin_all=support_margin(com, support) if len(support) >= 3 else None,
                margin_without_fl=support_margin(com, without_fl) if len(without_fl) >= 3 else None,
                reference=machine.reference_body.tolist(), offset_goal=machine._offset_goal.tolist()))
            trace[-1]['foot_targets'] = {name: point.tolist() for name, point in machine._targets.items()}
            trace[-1]['carry_velocity'] = {name: bundle.joints.data['velocity'][name] for name in target}
            trace[-1]['gripper_velocity'] = {name: bundle.joints.data['velocity'][name]
                for name in ('gripper_left_joint', 'gripper_right_joint')}
        if final.joint_targets is None:
            break
        for name, q in final.joint_targets.items():
            data.ctrl[native.actuator(name+'_motor').id] = q
        if triggered:
            q, qd = bundle.joints.data['position'], bundle.joints.data['velocity']
            maximum_error = max(maximum_error, *(abs(q[name]-value) for name, value in target.items()))
            maximum_velocity = max(maximum_velocity, *(abs(qd[name]) for name in target))
            maximum_gripper_error = max(maximum_gripper_error,
                *(abs(q[name]-.015) for name in ('gripper_left_joint', 'gripper_right_joint')))
            maximum_gripper_velocity = max(maximum_gripper_velocity,
                *(abs(qd[name]) for name in ('gripper_left_joint', 'gripper_right_joint')))
            if final.state == 'STAND':
                completed = True
                break
        for _ in range(round(.02/native.opt.timestep)):
            mujoco.mj_step(native, data)
    return dict(engine='python_mujoco_component_only', version=mujoco.__version__,
        state=final.state, reason=final.reason, completed=completed, duration_s=float(data.time-start),
        maximum_carry_error_rad=maximum_error, maximum_carry_velocity_rps=maximum_velocity,
        maximum_gripper_error_m=maximum_gripper_error, maximum_gripper_velocity_mps=maximum_gripper_velocity)
