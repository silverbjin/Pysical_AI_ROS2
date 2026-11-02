"""Explicit ideal-feedback unit plant, NOT a physical engine or G1/G2 proof.

Only sequencing/math is tested here. Real body/torque/contact tracking must be
accepted separately in both engines; this ideal follower cannot establish it.
"""
from dataclasses import replace
import math

import numpy as np
from integrated_robot_navigation.leg_kinematics import fk_leg
from guard_fixture import bundle


class IdealFeedback:
    def __init__(self, model):
        self.model = model
        self.state = bundle(model)
        self.ros, self.wall = 1_000_000_000, 10_000_000_000
        self.pose = np.eye(4)
        self.pose[2, 3] = .46
        self.floor_center = .46-.5*math.cos(.5)

    def tick(self, machine=None, result=None, *, follow=True):
        q = dict(self.state.joints.data['position'])
        old_q, old_pose = dict(q), self.pose.copy()
        if follow and result is not None and result.joint_targets is not None:
            q.update(result.joint_targets)
            self.pose = np.asarray(machine.reference_body).copy()
        yaw = math.atan2(self.pose[1, 0], self.pose[0, 0])
        old_yaw = math.atan2(old_pose[1, 0], old_pose[0, 0])
        velocity = self.pose[:3, :3].T @ ((self.pose[:3, 3]-old_pose[:3, 3])/.02)
        points, forces = [], []
        for foot in self.model.feet:
            angles = tuple(q[foot[:2]+'_'+p+'_joint'] for p in ('hip', 'thigh', 'calf'))
            center = self.pose @ np.array((*fk_leg(self.model, foot, angles), 1.))
            loaded = center[2] <= self.floor_center+.0015
            points.append((float(center[0]), float(center[1]), 0. if loaded else float(center[2])))
            forces.append(30. if loaded else 0.)
        self.ros += 20_000_000
        self.wall += 20_000_000
        values = dict(
            joints=dict(position=q, velocity={n: (q[n]-old_q[n])/.02 for n in q}),
            body=dict(position=tuple(self.pose[:3, 3]), orientation=(0., 0., math.sin(yaw/2), math.cos(yaw/2)),
                linear_velocity=tuple(velocity), angular_velocity=(0., 0., (yaw-old_yaw)/.02),
                child_frame_id='base_footprint'),
            contacts=dict(names=self.model.feet, points=tuple(points), forces=tuple(forces),
                          touching=tuple(f >= 2. for f in forces), unexpected_contacts=0))
        self.state = replace(self.state, **{
            key: replace(getattr(self.state, key), stamp_ns=self.ros, received_ns=self.wall,
                         sequence=self.ros, data=values.get(key, getattr(self.state, key).data))
            for key in ('joints', 'imu', 'contacts', 'body', 'scan', 'carry')})
        return self.state
