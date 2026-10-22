"""Measured-support crawl kernel; references are targets, never odometry.

Only the ROS owner may call this kernel with an authorized motion command.
Ideal-feedback tests cannot validate physical tracking; both native gates remain
mandatory. No simulator API, root setter, force override, or command odom exists.
"""
import math

import numpy as np

from .carry_profile import _validate_limits
from .leg_kinematics import fk_leg, ik_leg
from .projection import body_rotation
from .samples import ControlResult, sample_valid
from .support import center_of_mass, support_margin


def blend(value):
    u = min(1., max(0., value))
    return u*u*u*(10.+u*(-15.+6.*u))


class CrawlMachine:
    ORDER = ('fl_foot', 'rr_foot', 'fr_foot', 'rl_foot')

    def __init__(self, model, limits):
        _validate_limits(limits)
        self.model, self.limits = model, dict(limits)
        self.state, self.phase, self.reason = 'INACTIVE', 'STAND', ''
        self.generation = -1
        self.reference_body = np.eye(4)
        self.stopping, self.urgent = False, False
        self._explicit_stop = self._paused = False
        self.swing_foot = None
        self._initialized = False

    def _result(self, targets=None):
        return ControlResult(self.state, self.phase, self.swing_foot,
                             self.generation, targets, self.reason)

    def _fail(self, reason):
        self.state, self.reason = 'FAULT', self.reason or reason
        self.swing_foot = None
        return self._result()

    def _measure(self, bundle, ros_ns, wall_ns):
        for key in ('joints', 'imu', 'contacts', 'body'):
            ok, reason = sample_valid(getattr(bundle, key), ros_ns, wall_ns,
                                      self.epoch, max_age_ns=200_000_000)
            if not ok:
                raise ValueError(key+':'+reason)
        q, qd = bundle.joints.data['position'], bundle.joints.data['velocity']
        if set(q) != set(self.model.limits) or set(qd) != set(q):
            raise ValueError('joint names')
        if any(not lo <= q[name] <= hi or abs(qd[name]) > velocity
               for name, (lo, hi, velocity, _) in self.model.limits.items()):
            raise ValueError('physical joint limits')
        if bundle.body.frame_id != 'odom' or bundle.body.data['child_frame_id'] != 'base_footprint':
            raise ValueError('body frame')
        pose = np.eye(4)
        pose[:3, :3], (roll, pitch, _) = body_rotation(bundle.body.data)
        pose[:3, 3] = bundle.body.data['position']
        if (max(abs(roll), abs(pitch)) > self.limits['max_roll_pitch']
                or not self.limits['min_body_height_m'] <= pose[2, 3] <= self.limits['max_body_height_m']):
            raise ValueError('body stability')
        data = bundle.contacts.data
        if (bundle.contacts.frame_id != 'odom' or tuple(data['names']) != self.model.feet
                or data['unexpected_contacts'] != 0):
            raise ValueError('contact names/frame/unexpected')
        if len(data['forces']) != 4 or len(data['touching']) != 4 or len(data['points']) != 4:
            raise ValueError('contact dimensions')
        loads = {name: force >= self.limits['min_contact_force_n']
                 for name, force in zip(self.model.feet, data['forces'])}
        if tuple(loads.values()) != tuple(data['touching']):
            raise ValueError('contact force/touching mismatch')
        centers = {}
        for foot in self.model.feet:
            angles = tuple(q[foot[:2]+'_'+part+'_joint'] for part in ('hip', 'thigh', 'calf'))
            centers[foot] = (pose @ np.array((*fk_leg(self.model, foot, angles), 1.)))[:3]
        points = dict(zip(self.model.feet, data['points']))
        com = center_of_mass(self.model, q, pose)
        return q, pose, centers, loads, points, com

    def reset(self, bundle, ros_ns, wall_ns):
        self.generation += 1
        self.state, self.phase, self.reason = 'STAND', 'STAND', ''
        self.stopping = self.urgent = False
        self._explicit_stop = self._paused = False
        self.swing_foot = None
        self.epoch = bundle.body.epoch if bundle.body is not None else 0
        self._initialized = False
        try:
            _, pose, centers, _, _, _ = self._measure(bundle, ros_ns, wall_ns)
        except (ValueError, KeyError, TypeError, IndexError) as error:
            self._fail(str(error))
            return
        self.reference_body = pose.copy()
        self.travel = pose.copy()
        self.anchors = {name: p.copy() for name, p in centers.items()}
        self.floor = {name: p[2] for name, p in centers.items()}
        self._targets = {name: p.copy() for name, p in centers.items()}
        self.offset = np.zeros(2)
        self._phase_start = ros_ns
        self._stand_start_z = pose[2, 3]
        self._stand_start = ros_ns
        self._last_ros, self._last_wall, self._progress_wall = ros_ns, wall_ns, wall_ns
        self._index = 0
        self._stop_start = self._settled_start = None
        self._initialized = True

    def request_stop(self, urgent):
        self.stopping, self.urgent = True, self.urgent or bool(urgent)
        self._explicit_stop = True

    def _margin(self, com, loads, points, exclude=None):
        support = [points[n] for n in self.model.feet if loads[n] and n != exclude]
        if len(support) < 3:
            return -math.inf
        return support_margin(com, support)

    def _begin_shift(self, com, loads, points, now, joints):
        self.phase, self.swing_foot, self._phase_start = 'SHIFT', None, now
        foot = self.ORDER[self._index]
        self._offset_start = self.offset.copy()
        support = [points[n] for n in self.model.feet if n != foot and loads[n]]
        self._offset_goal = self.offset.copy()
        if len(support) < 3:
            return
        centroid = np.mean(np.asarray(support, dtype=float), axis=0)
        desired_margin = self.limits['min_support_margin_m']+.015
        if support_margin(centroid, support) < desired_margin:
            raise ValueError('support triangle has no safe inset')
        # Root translation does NOT translate every link's CoM equally: stance
        # feet stay fixed while their leg joints move. Predict with the full
        # IK/URDF mass model, not COM_new = COM_old + body_delta.
        direction = centroid[:2]-np.asarray(com)[:2]

        def predicted_margin(weight):
            body = self.reference_body.copy()
            body[:2, 3] += direction*weight
            q = dict(joints)
            q.update(self._solve(joints, True, body))
            return support_margin(center_of_mass(self.model, q, body), support)

        low, high = 0., None
        for candidate in np.linspace(0., 1., 9):
            try:
                safe = predicted_margin(candidate) >= desired_margin
            except ValueError:
                safe = False
            if safe:
                high = float(candidate)
                break
            low = float(candidate)
        if high is None:
            raise ValueError('no footprint-bound kinematic support shift')
        # Keep the safe side of a bounded bracket; precision is not achieved by
        # relaxing the required measured support margin.
        for _ in range(8):
            candidate = (low+high)/2
            try:
                safe = predicted_margin(candidate) >= desired_margin
            except ValueError:
                safe = False
            if safe:
                high = candidate
            else:
                low = candidate
        self._offset_goal += direction*high

    def _effective_command(self, command):
        vx, _, wz = command
        duration = self.limits['cycle_s']
        yaw = math.atan2(self.travel[1, 0], self.travel[0, 0])
        theta = wz*duration
        rotation = np.array([[math.cos(theta), -math.sin(theta)],
                             [math.sin(theta), math.cos(theta)]])
        translation = np.array([math.cos(yaw), math.sin(yaw)])*vx*duration
        displacements = [np.linalg.norm((rotation-np.eye(2)) @
                         (p[:2]-self.travel[:2, 3])+translation) for p in self.anchors.values()]
        maximum = max(displacements)
        scale = min(1., self.limits['max_foot_displacement_m']/maximum) if maximum else 1.
        return vx*scale, wz*scale

    def _solve(self, q, moving, body_pose=None):
        inverse = np.linalg.inv(self.reference_body if body_pose is None else body_pose)
        targets = {}
        for foot in self.model.feet:
            names = tuple(foot[:2]+'_'+part+'_joint' for part in ('hip', 'thigh', 'calf'))
            point = inverse @ np.array((*self._targets[foot], 1.))
            result = ik_leg(self.model, foot, tuple(point[:3]), tuple(q[n] for n in names))
            for name, value, part in zip(names, result, ('hip', 'thigh', 'calf')):
                if not math.isfinite(value) or not self.model.limits[name][0] <= value <= self.model.limits[name][1]:
                    raise ValueError('ik physical bound')
                if moving and not self.limits['gait_joint_bounds'][part][0] <= value <= self.limits['gait_joint_bounds'][part][1]:
                    raise ValueError('ik footprint joint bound')
                targets[name] = value
        return targets

    def _stop(self, bundle, centers, loads, now):
        self.state = 'STOPPING'
        if self._stop_start is None:
            self._stop_start = now
            if self.swing_foot:
                self._land_start = centers[self.swing_foot].copy()
                self._land_goal = self._land_start.copy()
                self._land_goal[2] = self.floor[self.swing_foot]-.002
        elapsed = (now-self._stop_start)/1e9
        if self.swing_foot:
            foot = self.swing_foot
            self.phase = 'TOUCHDOWN'
            weight = blend(elapsed/.75)
            self._targets[foot] = self._land_start*(1-weight)+self._land_goal*weight
            if loads[foot]:
                self.anchors[foot] = centers[foot].copy()
                self._targets[foot] = centers[foot].copy()
                self.swing_foot = None
            elif elapsed > self.limits['stop_landing_s']:
                raise ValueError('landing timeout; stopped unconfirmed')
        body = bundle.body.data
        speed = math.hypot(*body['linear_velocity'][:2])
        yaw_speed = abs(body['angular_velocity'][2])
        if (all(loads.values()) and self.swing_foot is None
                and speed <= self.limits['stopped_v_mps'] and yaw_speed <= self.limits['stopped_wz_rps']):
            if self._settled_start is None:
                self._settled_start = now
            if (now-self._settled_start)/1e9 >= self.limits['settle_s']:
                self.state, self.phase = 'STOPPED', 'STAND'
        else:
            self._settled_start = None

    def advance(self, bundle, command, ros_ns, wall_ns):
        if self.state == 'FAULT':
            return self._result()
        if not self._initialized:
            return self._fail('not initialized')
        try:
            if (len(command) != 3 or not all(math.isfinite(v) for v in command)
                    or abs(command[0]) > self.limits['max_vx'] or command[1] != 0.
                    or abs(command[2]) > self.limits['max_wz']):
                raise ValueError('command limit/nonfinite')
            if ros_ns < self._last_ros or wall_ns < self._last_wall:
                raise ValueError('clock rollback')
            if ros_ns > self._last_ros:
                self._progress_wall = wall_ns
            if wall_ns-self._progress_wall > 200_000_000:
                raise ValueError('clock paused')
            dt = (ros_ns-self._last_ros)/1e9
            if dt > .2:
                raise ValueError('control gap')
            self._last_ros, self._last_wall = ros_ns, wall_ns
            q, pose, centers, loads, points, com = self._measure(bundle, ros_ns, wall_ns)
            for foot in self.model.feet:
                if foot != self.swing_foot and loads[foot] and np.linalg.norm(centers[foot]-self.anchors[foot]) > self.limits['max_stance_slip_m']:
                    raise ValueError('stance slip')
            if self._margin(com, loads, points) < self.limits['min_support_margin_m']:
                raise ValueError('current measured support lost')
            if self._paused and not self._explicit_stop and self.state == 'STOPPED' and command != (0., 0., 0.):
                # Resuming an authorized velocity pause is not recovery from a
                # fault. Explicit stop/fault still requires a caller reset.
                self.stopping = self._paused = False
                self._stop_start = self._settled_start = None
                self.state, self.phase = 'STAND', 'STAND'
                self.travel = self.reference_body.copy()
                self.offset = np.zeros(2)
            if command == (0., 0., 0.) and self.state == 'CRAWL' and not self.stopping:
                self.stopping = self._paused = True
            if self.stopping:
                self._stop(bundle, centers, loads, ros_ns)
            elif command == (0., 0., 0.) and self.state == 'STAND':
                # Bootstrap stance can precede carry; only leg targets are emitted.
                weight = blend((ros_ns-self._stand_start)/2e9)
                self.reference_body[2, 3] = self._stand_start_z*(1-weight)+self.limits['nominal_body_height_m']*weight
            else:
                if self.state == 'STAND':
                    self.state = 'CRAWL'
                    self._begin_shift(com, loads, points, ros_ns, q)
                vx, wz = self._effective_command(command)
                yaw = math.atan2(self.travel[1, 0], self.travel[0, 0])+wz*dt
                self.travel[:2, 3] += np.array([math.cos(yaw), math.sin(yaw)])*vx*dt
                self.travel[:3, :3] = [[math.cos(yaw), -math.sin(yaw), 0.],
                                       [math.sin(yaw), math.cos(yaw), 0.], [0., 0., 1.]]
                elapsed = (ros_ns-self._phase_start)/1e9
                foot = self.ORDER[self._index]
                if self.phase == 'SHIFT':
                    weight = blend(elapsed/.7)
                    self.offset = self._offset_start*(1-weight)+self._offset_goal*weight
                    if elapsed >= .7 and self._margin(com, loads, points, foot) >= self.limits['min_support_margin_m']:
                        self.phase, self.swing_foot, self._phase_start = 'SWING', foot, ros_ns
                        self._swing_start = self.anchors[foot].copy()
                        theta = wz*self.limits['cycle_s']
                        rotation = np.array([[math.cos(theta), -math.sin(theta)], [math.sin(theta), math.cos(theta)]])
                        self._swing_goal = self._swing_start.copy()
                        self._swing_goal[:2] = self.travel[:2, 3]+rotation @ (self._swing_start[:2]-self.travel[:2, 3])+np.array([math.cos(yaw), math.sin(yaw)])*vx*self.limits['cycle_s']
                        if np.linalg.norm(self._swing_goal[:2]-self._swing_start[:2]) > self.limits['max_foot_displacement_m']+1e-12:
                            raise ValueError('foot stride bound')
                    elif elapsed > 2.:
                        raise ValueError('shift timeout; measured support not gained')
                elif self.phase == 'SWING':
                    if self._margin(com, loads, points, foot) < self.limits['min_support_margin_m']:
                        raise ValueError('swing support lost')
                    u = min(1., elapsed/.8)
                    weight = blend(u)
                    self._targets[foot] = self._swing_start*(1-weight)+self._swing_goal*weight
                    self._targets[foot][2] += self.limits['swing_height_m']*16*u*u*(1-u)*(1-u)
                    if u >= 1.:
                        self.phase, self._phase_start = 'TOUCHDOWN', ros_ns
                elif self.phase == 'TOUCHDOWN':
                    if loads[foot] and elapsed >= .25:
                        self.anchors[foot] = centers[foot].copy()
                        self._targets[foot] = centers[foot].copy()
                        self.swing_foot = None
                        self.phase, self._phase_start = 'SETTLE', ros_ns
                    elif elapsed > 1.:
                        raise ValueError('touchdown timeout')
                    elif not loads[foot]:
                        self._targets[foot][2] = self.floor[foot]-.002*min(1., elapsed/.25)
                elif self.phase == 'SETTLE' and elapsed >= .25:
                    self._index = (self._index+1)%4
                    self._begin_shift(com, loads, points, ros_ns, q)
                self.reference_body[:3, :3] = self.travel[:3, :3]
                self.reference_body[:2, 3] = self.travel[:2, 3]+self.offset
            return self._result(self._solve(q, self.state != 'STAND'))
        except (ValueError, KeyError, TypeError, IndexError, np.linalg.LinAlgError) as error:
            return self._fail(str(error))
