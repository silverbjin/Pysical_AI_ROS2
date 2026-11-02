"""Measured-support crawl kernel; references are targets, never odometry.

Only the ROS owner may call this kernel with an authorized motion command.
Ideal-feedback tests cannot validate physical tracking; both native gates remain
mandatory. No simulator API, root setter, force override, or command odom exists.
"""
import math
from copy import deepcopy

import numpy as np

from .carry_profile import _validate_limits
from .leg_kinematics import fk_leg, ik_leg, thigh_trunk_clearance
from .projection import body_rotation
from .samples import ControlResult, sample_valid
from .support import center_of_mass, support_margin, nearest_halfplane_point
from .calibration import InPlaceCalibration, precondition_loaded_reference


def blend(value):
    u = min(1., max(0., value))
    return u*u*u*(10.+u*(-15.+6.*u))


class CrawlMachine:
    ORDER = ('fl_foot', 'rr_foot', 'fr_foot', 'rl_foot')
    # Intermittent static crawl: body movement ends before measured unloading.
    # Continue the same contact-gated foot curve with the body reference held.
    TRAVEL_BUDGET = {'SHIFT': .7, 'SWING': 0., 'TOUCHDOWN': 0., 'SETTLE': 0.}

    def __init__(self, model, limits):
        _validate_limits(limits)
        self.model, self.limits = model, dict(limits)
        self.state, self.phase, self.reason = 'INACTIVE', 'STAND', ''
        self.generation = -1
        self.epoch = 0  # the supported native plugins start one immutable engine epoch
        self.reference_body = np.eye(4)
        self.stopping, self.urgent = False, False
        self._explicit_stop = self._paused = False
        self.calibrating = False
        self.swing_foot = None
        self._initialized = False
        self._shift_plan = None
        self._calibration_request = self._calibration_vertical = None
        self._calibration_rest_z = None
        self._calibration_stages, self._calibration_sources = [],None
        self._calibration_shift_clock = None
        self._crawl_shift_clock = None
        self._crawl_swing_clock = None
        self._unload_time_credit_ns = 0
        self._touchdown_time_credit_ns = 0
        self._fault_landing_foot = None
        self._fault_hold_observation = False
        self.fault_stop_confirmed = False
        self._fault_settle_origin = self._fault_capture = None
        self._fault_capture_count = 0

    def _result(self, targets=None):
        return ControlResult(self.state, self.phase, self.swing_foot,
                             self.generation, targets, self.reason)

    def _fail(self, reason):
        self._shift_plan = None
        self._fault_hold_observation=(not self.calibrating and self.phase=='SHIFT'
            and self.swing_foot is None and self._unload_start is None
            and reason=='shift timeout; measured support/settle not gained')
        self.fault_stop_confirmed = False
        self._fault_settle_origin = self._fault_capture = None
        self._fault_capture_count = 0
        self._fault_landing_foot=(self.swing_foot if not self.calibrating
            and reason in ('measured unload timeout','touchdown timeout') else None)
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

    def reset(self, bundle, ros_ns, wall_ns, *, held_targets=None):
        self._shift_plan = None
        self._fault_landing_foot = None
        self._fault_hold_observation = self.fault_stop_confirmed = False
        self._fault_settle_origin = self._fault_capture = None
        self._fault_capture_count = 0
        self._calibration_request = self._calibration_vertical = None
        self._calibration_rest_z = None
        self._calibration_stages, self._calibration_sources = [],None
        self.generation += 1
        self.state, self.phase, self.reason = 'STAND', 'STAND', ''
        self.stopping = self.urgent = False
        self._explicit_stop = self._paused = False
        self.calibrating = False
        self.swing_foot = None
        self.epoch = bundle.body.epoch if bundle.body is not None else 0
        self._initialized = False
        try:
            _, pose, centers, _, _, _ = self._measure(bundle, ros_ns, wall_ns)
            commanded_centers = centers
            if held_targets is not None:
                if set(held_targets) != set(self.model.joint_names) or any(
                        not math.isfinite(v) or not self.model.limits[n][0] <= v <= self.model.limits[n][1]
                        for n, v in held_targets.items()):
                    raise ValueError('invalid held leg command handoff')
                commanded_centers = {}
                for foot in self.model.feet:
                    angles = tuple(held_targets[foot[:2]+'_'+part+'_joint']
                                   for part in ('hip', 'thigh', 'calf'))
                    commanded_centers[foot] = (pose @ np.array((*fk_leg(self.model, foot, angles), 1.)))[:3]
        except (ValueError, KeyError, TypeError, IndexError) as error:
            self._fail(str(error))
            return
        self.reference_body = pose.copy()
        self.travel = pose.copy()
        self.anchors = {name: p.copy() for name, p in centers.items()}
        self.floor = {name: p[2] for name, p in centers.items()}
        # Encoders under load are not the position servo's held commands.
        # Preserve spring preload at activation; actual anchors/floor above
        # remain measured and continue to guard slip/support independently.
        self._targets = {name: p.copy() for name, p in commanded_centers.items()}
        inverse=np.linalg.inv(self.travel)
        self._nominal_feet={name:(inverse@np.r_[point,1.])[:3]
            for name,point in self._targets.items()}
        self.offset = np.zeros(2)
        self._phase_start = ros_ns
        self._stand_start_z = pose[2, 3]
        self._stand_start = ros_ns
        self._last_ros, self._last_wall, self._progress_wall = ros_ns, wall_ns, wall_ns
        self._index = 0
        self._stop_start = self._settled_start = None
        self._initialized = True

    def request_stop(self, urgent):
        self._shift_plan = None
        self.stopping, self.urgent = True, self.urgent or bool(urgent)
        self._explicit_stop = True

    def request_contact_calibration(self, *, ros_ns=None, wall_ns=None):
        if not self._initialized or self.state != 'STAND' or self.stopping or self.calibrating:
            raise ValueError('contact calibration requires idle measured STAND')
        self.calibrating = True
        self._index = 0  # G1's explicit FL request agrees with its force index1
        self._calibration_rest_z = float(self._targets['fl_foot'][2])
        self._calibration_vertical = None
        self._calibration_request = None if wall_ns is None else dict(
            ros_ns=ros_ns,wall_ns=wall_ns,deadline_wall_ns=wall_ns+10_000_000_000)
        self._calibration_stages, self._calibration_sources = [],None
        self._calibration_shift_clock = None

    def confirm_contact_calibration(self, *, wall_ns):
        """Called only by the command owner's measured one-wall-second gate."""
        if (not self.calibrating or self.stopping or self.state!='STAND'
                or self._calibration_vertical is None or self._calibration_vertical.phase!='STAND'):
            raise ValueError('calibration measured STAND confirmation unavailable')
        if wall_ns>=self._calibration_request['deadline_wall_ns']:
            raise ValueError('calibration original wall deadline')
        self.calibrating = False

    def _record_calibration(self, bundle, ros_ns, wall_ns):
        self._calibration_sources = {key:dict(stamp_ns=getattr(bundle,key).stamp_ns,
            received_ns=getattr(bundle,key).received_ns) for key in ('joints','body','contacts')}
        if not self._calibration_stages or self._calibration_stages[-1]['phase']!=self.phase:
            self._calibration_stages.append(dict(phase=self.phase,ros_ns=ros_ns,wall_ns=wall_ns))

    def calibration_snapshot(self):
        if self._calibration_request is None:
            return None
        return deepcopy(dict(request=self._calibration_request,stages=self._calibration_stages,
            selected_sources=self._calibration_sources,
            preconditioning_rest_z=self._calibration_rest_z,
            shift_accel_budget_mps2=getattr(self,'_shift_accel_budget',None),
            shift_reference_clock=self._calibration_shift_clock,
            vertical=self._calibration_vertical.snapshot() if self._calibration_vertical else None))

    def _g1_shift_reference_time(self,ros_ns,wall_ns):
        """Advance the same G1 curve at most one 50Hz reference step.

        Capture/decision clocks and every measured deadline remain original.
        This is trajectory progress, not a motor interpolation or new clock.
        """
        clock=self._calibration_shift_clock
        if clock is None or clock['phase_origin_ros_ns']!=self._phase_start:
            clock=dict(phase_origin_ros_ns=self._phase_start,reference_elapsed_ns=0,
                last_ros_ns=ros_ns,last_wall_ns=wall_ns,last_step_ns=0,nominal_step_ns=20_000_000)
            self._calibration_shift_clock=clock
        else:
            step=max(0,min(20_000_000,ros_ns-clock['last_ros_ns'],wall_ns-clock['last_wall_ns']))
            clock['reference_elapsed_ns']+=step
            clock.update(last_ros_ns=ros_ns,last_wall_ns=wall_ns,last_step_ns=step)
        clock['unconsumed_ros_ns']=max(0,ros_ns-self._phase_start-clock['reference_elapsed_ns'])
        return clock['reference_elapsed_ns']/1e9,clock['last_step_ns']/1e9

    def _margin(self, com, loads, points, exclude=None):
        support = [points[n] for n in self.model.feet if loads[n] and n != exclude]
        if len(support) < 3:
            return -math.inf
        return support_margin(com, support)

    def _crawl_reference_time(self,ros_ns,wall_ns,decision_step_ns,permitted=True):
        """Same moving curve, without catching up missed control references.

        This bounds high-level curve progress only. The native motor controller,
        actual sensor clocks and actual phase timeout are unchanged.
        """
        attribute='_crawl_shift_clock' if self.phase=='SHIFT' else '_crawl_swing_clock'
        clock=getattr(self,attribute)
        if clock is None or clock['phase_origin_ros_ns']!=self._phase_start:
            clock=dict(phase_origin_ros_ns=self._phase_start,reference_elapsed_ns=0,
                nominal_step_ns=20_000_000)
            setattr(self,attribute,clock)
            step=max(0,min(20_000_000,ros_ns-self._phase_start,decision_step_ns))
            clock.update(last_advance_ros_ns=ros_ns-step,last_advance_wall_ns=wall_ns-step)
        else:
            step=max(0,min(20_000_000,ros_ns-clock['last_advance_ros_ns'],
                wall_ns-clock['last_advance_wall_ns']))
        if not permitted:step=0
        if step:
            clock.update(last_advance_ros_ns=ros_ns,last_advance_wall_ns=wall_ns)
        clock['reference_elapsed_ns']+=step
        clock.update(last_ros_ns=ros_ns,last_wall_ns=wall_ns,last_step_ns=step,
            unconsumed_ros_ns=max(0,ros_ns-self._phase_start-clock['reference_elapsed_ns']))
        return clock['reference_elapsed_ns']/1e9,step/1e9

    def _body_duration(self, phase, minimum, offset_distance=0.):
        """Normal moving-body time law, including input ramp and rotation.

        Keep phase travel integrals unchanged; holds never integrate extra
        distance. Peak quintic speed gain <=1/2 reserves input acceleration,
        while the remaining budget bounds offset+travel curve acceleration.
        G1's separate zero-command calibration remains unchanged.
        """
        if self.state != 'CRAWL' or self.calibrating:
            return minimum
        budget = self.TRAVEL_BUDGET[phase]
        vx, wz = self.limits['max_vx'], self.limits['max_wz']
        available = (self.limits['max_support_shift_accel_mps2']
            -.5*self.limits['max_accel_x']-.25*vx*wz)
        if available <= 0.:
            raise ValueError('no combined body acceleration budget')
        peak = 10.*math.sqrt(3.)/3.
        return max(minimum, 3.75*budget,
            math.sqrt(peak*(offset_distance+vx*budget)/available),
            math.sqrt(peak*wz*budget/(.5*self.limits['max_accel_wz'])))

    def _begin_shift(self, com, loads, points, now, joints, command=(0.,0.,0.)):
        self._shift_plan = None
        self._unload_time_credit_ns = 0
        self.phase, self.swing_foot, self._phase_start = 'SHIFT', None, now
        foot = self.ORDER[self._index]
        self._offset_start = self.offset.copy()
        self._shift_duration = self._body_duration('SHIFT', .7)
        self._shift_settled_start = None
        self._unload_start = None
        self._unloaded_since = None
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
        self._shift_plan = self._plan_shift(direction, support, desired_margin, dict(joints),
            self.reference_body.copy(),
            measured_com=np.asarray(com).copy() if self.state=='CRAWL' and not self.calibrating else None,
            command=command)

    def _plan_shift(self, direction, support, desired_margin, joints, reference_body, *, measured_com=None,
                    command=(0.,0.,0.)):
        """At most one full IK/CoM candidate per next(); no actuator writes.

        The caller holds its previous reference while planning and performs all
        live safety checks before every slice. No thread owns stale commands.
        """
        normal=self.state=='CRAWL' and not self.calibrating
        # Check the phase's bounded motion as well as its support translation.
        # A ramp can rise after planning starts; use its existing full bound.
        vx=math.copysign(self.limits['max_vx'],command[0]) if normal and command[0] else 0.
        wz=math.copysign(self.limits['max_wz'],command[2]) if normal and command[2] else 0.
        future_targets=None
        if normal:
            # The next swing foot is not a stance anchor at the end of this
            # phase group. Predict its existing bounded neutral endpoint.
            travel=self.travel.copy();horizon=self.TRAVEL_BUDGET['SHIFT'];angle=wz*horizon
            c,s=math.cos(angle),math.sin(angle)
            local=(np.array([vx*horizon,0.]) if abs(wz)<1e-12 else
                np.array([vx*math.sin(angle)/wz,vx*2*math.sin(angle/2)**2/wz]))
            travel[:2,3]+=self.travel[:2,:2]@local
            travel[:3,:3]=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])@travel[:3,:3]
            foot=self.ORDER[self._index];future_targets=dict(self._targets)
            future_targets[foot]=np.r_[self._centered_swing_goal(foot,vx,wz,travel=travel),self.floor[foot]]
        def predicted_center(weight,ray=direction,progress=1.,motion=True,horizon_budget=None):
            body = reference_body.copy()
            budget=self.TRAVEL_BUDGET['SHIFT'] if horizon_budget is None else horizon_budget
            horizon=budget*progress if motion else 0.
            angle=wz*horizon;c,s=math.cos(angle),math.sin(angle)
            local=(np.array([vx*horizon,0.]) if abs(wz)<1e-12 else
                np.array([vx*math.sin(angle)/wz,vx*2*math.sin(angle/2)**2/wz]))
            body[:2,3]+=reference_body[:2,:2]@local+ray*weight*progress
            body[:3,:3]=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])@body[:3,:3]
            q = dict(joints)
            moved=future_targets if horizon_budget is not None else None
            q.update(self._solve(joints, True, body,foot_targets=moved))
            return np.asarray(center_of_mass(self.model, q, body))

        baseline=None
        if measured_com is not None:
            # Actual support points cannot be combined with an absolute CoM
            # from the virtual command pose (46921c07: 27.2mm vs 9.88mm).
            # Predict only the IK/mass-model change from the measured CoM.
            # Slice the baseline too: at most one model candidate per yield.
            baseline=predicted_center(0.,motion=False)
            yield

        def predicted_margin(weight,ray):
            predicted=predicted_center(weight,ray)
            if baseline is not None:
                predicted=measured_com+predicted-baseline
            return support_margin(predicted, support)

        rays=[direction]
        selected=None
        for ray in rays:
            low,high=0.,None
            for candidate in np.linspace(0.,1.,9):
                try:safe=predicted_margin(candidate,ray)>=desired_margin
                except ValueError:safe=False
                yield
                if safe:high=float(candidate);break
                low=float(candidate)
            if high is None:continue
            for _ in range(8):
                candidate=(low+high)/2
                try:safe=predicted_margin(candidate,ray)>=desired_margin
                except ValueError:safe=False
                yield
                if safe:high=candidate
                else:low=candidate
            path_safe=True
            if normal:
                for progress in (.25,.5,.75):
                    try:predicted_center(high,ray,progress)
                    except ValueError:path_safe=False
                    yield
                    if not path_safe:break
                if path_safe:
                    # Other stance legs remain planted during the subsequent
                    # swing/landing/settle while body yaw keeps advancing.
                    try:predicted_center(high,ray,horizon_budget=sum(self.TRAVEL_BUDGET.values()))
                    except ValueError:path_safe=False
                    yield
            if path_safe:selected=ray*high;break
        if selected is None and normal:
            # A feasible pose can lie between every old search ray (982b
            # regression). Use bounded local constraint projection, keeping
            # one full IK/mass evaluation per yielded control slice.
            selected=yield from self._constrained_shift(support,desired_margin,joints,
                reference_body,measured_com,baseline,vx,wz,future_targets)
        if selected is None:raise ValueError('no footprint-bound collision-clear support shift')
        self._offset_goal += selected
        # Quintic blend has peak |d²s/du²| = 10*sqrt(3)/3. Bound the
        # *internal* support translation, not just the incoming cmd_vel ramp.
        distance = float(np.linalg.norm(self._offset_goal-self._offset_start))
        self._shift_accel_budget = self.limits['max_support_shift_accel_mps2']
        self._shift_duration = max(.7, math.sqrt((10.*math.sqrt(3.)/3.)*distance/
            self._shift_accel_budget))
        self._shift_duration = self._body_duration('SHIFT',self._shift_duration,distance)

    def _constrained_shift(self,support,margin,joints,reference,measured,baseline,vx,wz,future_targets):
        points=np.asarray(support)[:,:2];center=points.mean(axis=0)
        points=points[np.argsort(np.arctan2(points[:,1]-center[1],points[:,0]-center[0]))]
        edges=np.roll(points,-1,axis=0)-points
        normals=np.column_stack((-edges[:,1],edges[:,0]))/np.linalg.norm(edges,axis=1)[:,None]
        def evaluate(delta,progress=1.,horizon_budget=None):
            budget=self.TRAVEL_BUDGET['SHIFT'] if horizon_budget is None else horizon_budget
            body=reference.copy();horizon=budget*progress
            angle=wz*horizon;c,s=math.cos(angle),math.sin(angle)
            local=(np.array([vx*horizon,0.]) if abs(wz)<1e-12 else
                np.array([vx*math.sin(angle)/wz,vx*2*math.sin(angle/2)**2/wz]))
            body[:2,3]+=reference[:2,:2]@local+delta*progress
            body[:3,:3]=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])@body[:3,:3]
            inverse=np.linalg.inv(body);q=dict(joints);clear=[];bounds=[]
            targets=self._targets if horizon_budget is None else future_targets
            for foot in self.model.feet:
                names=tuple(foot[:2]+'_'+part+'_joint' for part in ('hip','thigh','calf'))
                point=(inverse@np.r_[targets[foot],1.])[:3]
                angles=ik_leg(self.model,foot,point,tuple(joints[n] for n in names))
                q.update(zip(names,angles))
                clear.append(thigh_trunk_clearance(self.model,foot,angles)-.0001)
                for part,value in zip(('hip','thigh','calf'),angles):
                    lo,hi=self.limits['gait_joint_bounds'][part];bounds.extend((value-lo,hi-value))
            com=np.asarray(center_of_mass(self.model,q,body))
            if measured is not None:com=measured+com-baseline
            margins=np.einsum('ij,ij->i',normals,com[:2]-points)-margin
            return np.r_[margins,clear,bounds]
        delta=np.zeros(2);epsilon=1e-5;interior=1e-8
        def all_constraints(point):
            now=evaluate(point);yield
            future=evaluate(point,horizon_budget=sum(self.TRAVEL_BUDGET.values()));yield
            # Before-lift support plus the actual planned foot endpoint and
            # fixed stance feet until the next shift. Motion is tick-checked.
            return np.r_[now,future[len(points):]]
        for iteration in range(20):
            constraints=yield from all_constraints(delta)
            if np.min(constraints)>=0.:
                path_safe=True
                for progress in (.25,.5,.75):
                    row=evaluate(delta,progress);yield
                    # Support inset is required before lift, not during the
                    # shift toward it; geometry/joint bounds apply throughout.
                    if np.min(row[len(points):])<0.:path_safe=False;break
                if path_safe:return delta
                raise ValueError('support projection path is not collision-clear')
            jacobian=np.empty((len(constraints),2))
            for axis in range(2):
                probe=delta.copy();probe[axis]+=epsilon
                derivative=yield from all_constraints(probe)
                jacobian[:,axis]=(derivative-constraints)/epsilon
            trust=self.limits['max_foot_displacement_m']
            matrix=np.vstack((jacobian,np.eye(2),-np.eye(2)))
            bounds=np.r_[jacobian@delta-constraints+interior,delta-trust,-delta-trust]
            delta=nearest_halfplane_point(matrix,bounds)
        raise ValueError('bounded support constraint projection did not converge')

    def _effective_command(self, command):
        vx, _, wz = command
        duration = self.limits['cycle_s']
        yaw = math.atan2(self.travel[1, 0], self.travel[0, 0])
        theta = wz*duration
        rotation = np.array([[math.cos(theta), -math.sin(theta)],
                             [math.sin(theta), math.cos(theta)]])
        translation = np.array([math.cos(yaw), math.sin(yaw)])*vx*duration
        displacements = [np.linalg.norm((rotation-np.eye(2)) @
                         (p[:2]-self.travel[:2, 3])+translation) for p in self._targets.values()]
        maximum = max(displacements)
        scale = min(1., self.limits['max_foot_displacement_m']/maximum) if maximum else 1.
        return vx*scale, wz*scale

    def _centered_swing_goal(self, foot, vx, wz,*,travel=None):
        """Neutral stance at remaining swing + half the next stance budget.

        Use the commanded travel frame, excluding temporary support shifts.
        Never accumulate old world endpoints or replace measured odometry.
        These are integrated travel budgets, not physical wall durations.
        """
        travel=self.travel if travel is None else travel
        horizon=(len(self.ORDER)*sum(self.TRAVEL_BUDGET.values())+self.TRAVEL_BUDGET['SWING'])/2
        angle=wz*horizon;c,s=math.cos(angle),math.sin(angle)
        yaw=math.atan2(travel[1,0],travel[0,0])
        local=(np.array([vx*horizon,0.]) if abs(wz)<1e-12 else
            np.array([vx*math.sin(angle)/wz,vx*2*math.sin(angle/2)**2/wz]))
        future=travel.copy()
        future[:2,3]+=np.array([[math.cos(yaw),-math.sin(yaw)],
                               [math.sin(yaw),math.cos(yaw)]])@local
        future[:3,:3]=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])@future[:3,:3]
        centered=(future@np.r_[self._nominal_feet[foot],1.])[:2]
        start=self._targets[foot][:2]
        displacement=centered-start;distance=float(np.linalg.norm(displacement))
        # The last leg's first step may begin after travel already progressed.
        # Plan a shorter endpoint inside the existing 8cm step budget, before
        # constructing the smooth curve. Never clip IK angles or curve samples.
        reach=min(1.,self.limits['max_foot_displacement_m']/distance) if distance else 1.
        return start+reach*displacement

    def _solve(self, q, moving, body_pose=None,*,foot_targets=None):
        inverse = np.linalg.inv(self.reference_body if body_pose is None else body_pose)
        foot_targets=self._targets if foot_targets is None else foot_targets
        targets = {}
        for foot in self.model.feet:
            names = tuple(foot[:2]+'_'+part+'_joint' for part in ('hip', 'thigh', 'calf'))
            point = inverse @ np.array((*foot_targets[foot], 1.))
            result = ik_leg(self.model, foot, tuple(point[:3]), tuple(q[n] for n in names))
            if (moving and self.state=='CRAWL' and not self.calibrating
                    and thigh_trunk_clearance(self.model,foot,result)<.0001):
                raise ValueError('thigh/trunk collision clearance')
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
                # Keep the previous motor reference at t=0. A measured world
                # center contains root tracking/compliance error; it does not
                # authorize a discontinuous new desired world reference.
                self._land_start = self._targets[self.swing_foot].copy()
                self._land_goal = self._land_start.copy()
                self._land_goal[2] = self.floor[self.swing_foot]-.002
                self._land_duration=(max(.75,1.875*np.linalg.norm(self._land_goal-self._land_start)
                    /self.limits['max_swing_speed_mps'])
                    if self.reason in ('measured unload timeout','touchdown timeout') else .75)
        elapsed = (now-self._stop_start)/1e9
        if self.swing_foot:
            foot = self.swing_foot
            self.phase = 'TOUCHDOWN'
            weight = blend(elapsed/self._land_duration)
            self._targets[foot] = self._land_start*(1-weight)+self._land_goal*weight
            if loads[foot]:
                self.anchors[foot] = centers[foot].copy()
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

    def _observe_fault_hold_stop(self,bundle,command,ros_ns,wall_ns):
        """Read-only settling after an explicit stop of a held SHIFT timeout.

        Keep FAULT/reason/generation and never solve or emit new motor targets.
        Any invalid/stale support or clock permanently closes this observation;
        later transport recovery cannot grant a stop acknowledgement.
        """
        if not self._fault_hold_observation or not self._explicit_stop:
            return self._result()
        try:
            if command!=(0.,0.,0.):raise ValueError('fault stop requires zero command')
            if (ros_ns<self._last_ros or wall_ns<self._last_wall
                    or ros_ns-self._last_ros>200_000_000):
                raise ValueError('fault stop clock gap/rollback')
            if ros_ns>self._last_ros:self._progress_wall=wall_ns
            if wall_ns-self._progress_wall>200_000_000:
                raise ValueError('fault stop clock paused')
            self._last_ros,self._last_wall=ros_ns,wall_ns
            _,_,centers,loads,points,com=self._measure(bundle,ros_ns,wall_ns)
            if (not all(loads.values())
                    or self._margin(com,loads,points)<self.limits['min_support_margin_m']
                    or any(np.linalg.norm(centers[foot]-self.anchors[foot])>
                        self.limits['max_stance_slip_m'] for foot in self.model.feet)):
                raise ValueError('fault stop held support lost')
            body=bundle.body.data
            if (np.linalg.norm(body['linear_velocity'])>self.limits['stopped_v_mps']
                    or np.linalg.norm(body['angular_velocity'])>self.limits['stopped_wz_rps']):
                self._fault_settle_origin=self._fault_capture=None
                self._fault_capture_count=0;self.fault_stop_confirmed=False
                return self._result()
            if self._fault_settle_origin is None:self._fault_settle_origin=(ros_ns,wall_ns)
            capture=tuple(getattr(bundle,key).stamp_ns for key in ('joints','imu','contacts','body'))
            if self._fault_capture is None or all(a>b for a,b in zip(capture,self._fault_capture)):
                self._fault_capture=capture;self._fault_capture_count=min(3,self._fault_capture_count+1)
            origin_ros,origin_wall=self._fault_settle_origin
            self.fault_stop_confirmed=(self._fault_capture_count>=3
                and min(ros_ns-origin_ros,wall_ns-origin_wall)>=int(self.limits['settle_s']*1e9))
        except (ValueError,KeyError,TypeError,IndexError):
            self._fault_hold_observation=False;self.fault_stop_confirmed=False
        return self._result()

    def advance(self, bundle, command, ros_ns, wall_ns, *, reference_permitted=True):
        fault_landing=(self.state=='FAULT' and self.stopping and self._fault_landing_foot is not None)
        if self.state == 'FAULT' and not fault_landing:
            return self._observe_fault_hold_stop(bundle,command,ros_ns,wall_ns)
        if not self._initialized:
            return self._fail('not initialized')
        try:
            if (len(command) != 3 or not all(math.isfinite(v) for v in command)
                    or abs(command[0]) > self.limits['max_vx'] or command[1] != 0.
                    or abs(command[2]) > self.limits['max_wz']):
                raise ValueError('command limit/nonfinite')
            if self.calibrating and command != (0., 0., 0.):
                raise ValueError('contact calibration forbids navigation velocity')
            if ros_ns < self._last_ros or wall_ns < self._last_wall:
                raise ValueError('clock rollback')
            if ros_ns > self._last_ros:
                self._progress_wall = wall_ns
            if wall_ns-self._progress_wall > 200_000_000:
                raise ValueError('clock paused')
            decision_step_ns=min(ros_ns-self._last_ros,wall_ns-self._last_wall)
            dt = (ros_ns-self._last_ros)/1e9
            if dt > .2:
                raise ValueError('control gap')
            self._last_ros, self._last_wall = ros_ns, wall_ns
            q, pose, centers, loads, points, com = self._measure(bundle, ros_ns, wall_ns)
            if fault_landing:
                self.swing_foot=self._fault_landing_foot
            for foot in self.model.feet:
                if foot != self.swing_foot and loads[foot] and np.linalg.norm(centers[foot]-self.anchors[foot]) > self.limits['max_stance_slip_m']:
                    raise ValueError('stance slip')
            if self._margin(com, loads, points) < self.limits['min_support_margin_m']:
                raise ValueError('current measured support lost')
            if fault_landing:
                if (self._margin(com,loads,points,self.swing_foot)<self.limits['min_support_margin_m']
                        or np.linalg.norm(np.asarray(bundle.body.data['linear_velocity']))>self.limits['stopped_v_mps']
                        or np.linalg.norm(np.asarray(bundle.body.data['angular_velocity']))>self.limits['stopped_wz_rps']):
                    raise ValueError('fault landing measured support/settle lost')
                # Explicit STOP may only land this known foot. The original
                # failure reason/generation and explicit-stop latch remain;
                # no CRAWL activation or general fault recovery is performed.
                self.state='STOPPING';self._fault_landing_foot=None
                self._stop_start=self._settled_start=None
            if self.calibrating:
                if self._calibration_request is None:
                    self._calibration_request = dict(ros_ns=ros_ns,wall_ns=wall_ns,
                        deadline_wall_ns=wall_ns+10_000_000_000)
                if wall_ns>=self._calibration_request['deadline_wall_ns']:
                    raise ValueError('calibration original wall deadline')
                self._record_calibration(bundle,ros_ns,wall_ns)
            if (self.calibrating and self.state == 'STAND' and not self.stopping
                    and self._calibration_vertical is None):
                self.state = 'CALIBRATING'
                self._begin_shift(com, loads, points, ros_ns, q)
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
                if not self.calibrating:
                    weight = blend((ros_ns-self._stand_start)/2e9)
                    self.reference_body[2, 3] = self._stand_start_z*(1-weight)+self.limits['nominal_body_height_m']*weight
            else:
                if self.state == 'STAND':
                    self.state = 'CRAWL'
                    self._begin_shift(com, loads, points, ros_ns, q,command)
                unload_dt=touchdown_dt=max(0,decision_step_ns)/1e9
                if not self.calibrating and self.phase=='SHIFT' and self._unload_start is not None:
                    foot=self.ORDER[self._index]
                    eligible=(loads[foot]
                        and self._margin(com,loads,points,foot)>=self.limits['min_support_margin_m']
                        and np.linalg.norm(np.asarray(bundle.body.data['linear_velocity']))<=self.limits['stopped_v_mps']
                        and np.linalg.norm(np.asarray(bundle.body.data['angular_velocity']))<=self.limits['stopped_wz_rps'])
                    # Contact search is a bounded physical-time rate, separate
                    # from body/swing curve progress. Waiting for the previous
                    # application cannot erase eligible time or bank unsafe time.
                    self._unload_time_credit_ns=(min(200_000_000,
                        self._unload_time_credit_ns+max(0,decision_step_ns)) if eligible else 0)
                    unload_dt=self._unload_time_credit_ns/1e9 if reference_permitted else 0.
                    if reference_permitted:self._unload_time_credit_ns=0
                if not self.calibrating and self.phase=='TOUCHDOWN':
                    foot=self.ORDER[self._index]
                    self._touchdown_time_credit_ns=(min(200_000_000,
                        self._touchdown_time_credit_ns+max(0,decision_step_ns)) if not loads[foot] else 0)
                    touchdown_dt=self._touchdown_time_credit_ns/1e9 if reference_permitted else 0.
                    if reference_permitted:self._touchdown_time_credit_ns=0
                if not self.calibrating and not reference_permitted:
                    foot=self.ORDER[self._index]
                    if (self.phase=='SWING'
                            and self._margin(com,loads,points,foot)<self.limits['min_support_margin_m']):
                        raise ValueError('swing support lost')
                    if (self.phase=='TOUCHDOWN' and not loads[foot]
                            and (ros_ns-self._phase_start)/1e9>1.):
                        raise ValueError('touchdown timeout')
                    if (self.phase=='SHIFT' and self._unload_start is not None
                            and (ros_ns-self._unload_start)/1e9>
                                self.limits['max_unload_height_m']/self.limits['unload_speed_mps']+1.):
                        raise ValueError('measured unload timeout')
                    if self.phase in ('SHIFT','SWING'):
                        self._crawl_reference_time(ros_ns,wall_ns,decision_step_ns,False)
                    if (self.phase=='SHIFT' and self._unload_start is None
                            and self._shift_plan is None
                            and (ros_ns-self._phase_start)/1e9>self._shift_duration+1.):
                        raise ValueError('shift timeout; measured support/settle not gained')
                    # The already validated/published reference is unchanged.
                    # Safety measurement and phase deadlines above still run,
                    # but this owner cannot publish a new target until credit.
                    # Re-solving IK here only delays that application boundary.
                    return self._result()
                if self._shift_plan is not None:
                    # Bounded G1-only arithmetic batch, measured separately
                    # from live control. No motor/body reference is advanced
                    # while planning; every tick still checks current support.
                    for _ in range(4 if self.calibrating else 1):
                        try:
                            next(self._shift_plan)
                        except StopIteration:
                            self._shift_plan = None
                            # Planning is not executed body/foot motion.
                            self._phase_start = ros_ns
                            break
                    else:
                        return self._result(self._solve(q, True))
                if self.calibrating and self._calibration_vertical is not None:
                    foot = self.ORDER[self._index]
                    if self._margin(com,loads,points,foot)<self.limits['min_support_margin_m']:
                        raise ValueError('calibration three-stance support lost')
                    step = self._calibration_vertical.advance(ros_ns=ros_ns,wall_ns=wall_ns,
                        center_z=float(centers[foot][2]),forces=bundle.contacts.data['forces'],
                        capture_ns=bundle.contacts.stamp_ns)
                    if step.phase!=self.phase:
                        self._phase_start = ros_ns
                    self._targets[foot][2],self.phase = step.z,step.phase
                    self._record_calibration(bundle,ros_ns,wall_ns)
                    if step.complete:
                        self.state,self.phase,self.swing_foot = 'STAND','STAND',None
                        self.travel,self.offset = self.reference_body.copy(),np.zeros(2)
                        self._stand_start,self._stand_start_z = ros_ns,self.reference_body[2,3]
                    return self._result(self._solve(q,self.state!='STAND'))
                vx, wz = self._effective_command(command)
                elapsed = (ros_ns-self._phase_start)/1e9
                actual_elapsed=elapsed
                if self.calibrating and self.phase=='SHIFT':
                    elapsed,dt=self._g1_shift_reference_time(ros_ns,wall_ns)
                elif self.phase in ('SHIFT','SWING'):
                    elapsed,dt=self._crawl_reference_time(ros_ns,wall_ns,decision_step_ns)
                # Progress is phase-bounded: physical support waits do not
                # integrate extra body travel while the feet remain planted.
                token = (self.phase, self._phase_start)
                if getattr(self, '_travel_token', None) != token:
                    self._travel_token, self._travel_progress = token, 0.
                budgets = self.TRAVEL_BUDGET
                phase_time = elapsed*.7/self._shift_duration if self.phase == 'SHIFT' else elapsed
                if self.phase == 'SWING':
                    phase_time = elapsed*.8/self._swing_duration
                if self.calibrating:
                    progress = min(budgets[self.phase], max(0., phase_time))
                else:
                    duration = (self._shift_duration if self.phase == 'SHIFT' else
                        self._swing_duration if self.phase == 'SWING' else
                        self._body_duration(self.phase,.25))
                    progress = budgets[self.phase]*blend(elapsed/duration)
                travel_dt = max(0., progress-self._travel_progress)
                self._travel_progress = progress
                yaw = math.atan2(self.travel[1, 0], self.travel[0, 0])+wz*travel_dt
                self.travel[:2, 3] += np.array([math.cos(yaw), math.sin(yaw)])*vx*travel_dt
                # Integrate only the requested world-z rotation. Replacing this
                # with a yaw-only pose instantly erases the standing roll/pitch,
                # creating an IK target step even at dt=0 and zero command.
                delta = wz*travel_dt
                yaw_step = np.array([[math.cos(delta), -math.sin(delta), 0.],
                                     [math.sin(delta), math.cos(delta), 0.], [0., 0., 1.]])
                self.travel[:3, :3] = yaw_step @ self.travel[:3, :3]
                foot = self.ORDER[self._index]
                if self.phase == 'SHIFT':
                    weight = blend(elapsed/self._shift_duration)
                    self.offset = self._offset_start*(1-weight)+self._offset_goal*weight
                    if self.calibrating and self._unload_start is None:
                        local_center = pose[:3,:3].T @ (centers[foot]-pose[:3,3])
                        measured_reference_z = (self.reference_body[:3,:3] @ local_center
                                                +self.reference_body[:3,3])[2]
                        self._targets[foot][2] = precondition_loaded_reference(
                            z=float(self._targets[foot][2]),rest_z=self._calibration_rest_z,
                            measured_reference_z=float(measured_reference_z),forces=bundle.contacts.data['forces'],
                            dt=dt,limits=self.limits)
                    # The phase travel budget has ended before unloading. Check
                    # actual settled motion, not command=0 or geometric CoM alone.
                    measured_v = np.asarray(bundle.body.data['linear_velocity'])
                    settled = (elapsed >= self._shift_duration
                        and self._margin(com, loads, points, foot) >= self.limits['min_support_margin_m']
                        and np.linalg.norm(measured_v) <= self.limits['stopped_v_mps']
                        and np.linalg.norm(np.asarray(bundle.body.data['angular_velocity']))
                            <= self.limits['stopped_wz_rps'])
                    if settled:
                        if self._shift_settled_start is None:
                            self._shift_settled_start = ros_ns
                    else:
                        self._shift_settled_start = None
                    if (self._unload_start is None and self._shift_settled_start is not None
                            and ros_ns-self._shift_settled_start >= 100_000_000):
                        self._unload_start = ros_ns
                        self._unload_origin_z = (self._calibration_rest_z if self.calibrating
                                                 else self._targets[foot][2])
                        self.swing_foot = foot  # same owner must also land during an unload STOP
                    if self._unload_start is not None:
                        if settled and (loads[foot] or self.calibrating):
                            height = self._targets[foot][2]-self._unload_origin_z
                            if height >= self.limits['max_unload_height_m']-1e-12:
                                raise ValueError('measured unload height bound reached')
                            self._targets[foot][2] += min(self.limits['unload_speed_mps']*(dt if self.calibrating else unload_dt),
                                self.limits['max_unload_height_m']-height)
                        if settled and not loads[foot]:
                            if self._unloaded_since is None:
                                self._unloaded_since = ros_ns
                        else:
                            self._unloaded_since = None
                        unload_deadline = self.limits['max_unload_height_m']/self.limits['unload_speed_mps']+1.
                        if (ros_ns-self._unload_start)/1e9 > unload_deadline:
                            raise ValueError('measured unload timeout')
                    if self._unloaded_since is not None and ros_ns-self._unloaded_since >= 100_000_000:
                        self.phase, self.swing_foot, self._phase_start = 'SWING', foot, ros_ns
                        if self.calibrating:
                            self._calibration_vertical = InPlaceCalibration(
                                start_z=float(self._targets[foot][2]),rest_z=self._unload_origin_z,
                                baseline_z=self.floor[foot],limits=self.limits,ros_ns=ros_ns,wall_ns=wall_ns,
                                deadline_wall_ns=self._calibration_request['deadline_wall_ns'])
                            self._record_calibration(bundle,ros_ns,wall_ns)
                            return self._result(self._solve(q,True))
                        self._swing_start = self._targets[foot].copy()
                        self._swing_goal = self._swing_start.copy()
                        self._swing_goal[2] = self.floor[foot]
                        self._swing_amplitude = max(0., self.floor[foot]+self.limits['swing_height_m']
                                                   -self._swing_start[2])
                        self._swing_goal[:2] = self._centered_swing_goal(foot,vx,wz)
                        if np.linalg.norm(self._swing_goal[:2]-self._swing_start[:2]) > self.limits['max_foot_displacement_m']+1e-12:
                            raise ValueError('foot stride bound')
                        # Triangle bound on the full world-foot curve velocity:
                        # max blend'(u)=15/8; max bump'(u)=16/(3*sqrt(3)).
                        # Do not clip positions or integrate extra body travel
                        # while the slower physical foot curve is executing.
                        rate_bound = (1.875*np.linalg.norm(self._swing_goal-self._swing_start)
                            +16./(3.*math.sqrt(3.))*self._swing_amplitude)
                        self._swing_duration = max(.8, rate_bound/self.limits['max_swing_speed_mps'])
                        self._swing_duration = self._body_duration('SWING',self._swing_duration)
                    elif self._unload_start is None and actual_elapsed > self._shift_duration+1.:
                        raise ValueError('shift timeout; measured support/settle not gained')
                elif self.phase == 'SWING':
                    if self._margin(com, loads, points, foot) < self.limits['min_support_margin_m']:
                        raise ValueError('swing support lost')
                    u = min(1., elapsed/self._swing_duration)
                    # Contact can precede the command endpoint under compliant
                    # position control. It is not permission to latch a raised,
                    # shortened reference as the next stance anchor (99ee5235).
                    # Finish the same speed-bounded planned curve, including
                    # after contact; measured support and physical limits are
                    # still checked on every tick. TOUCHDOWN's separate slow
                    # contact search begins only at the planned endpoint.
                    weight = blend(u)
                    self._targets[foot] = self._swing_start*(1-weight)+self._swing_goal*weight
                    self._targets[foot][2] += self._swing_amplitude*16*u*u*(1-u)*(1-u)
                    if u >= 1.:
                        self.phase, self._phase_start = 'TOUCHDOWN', ros_ns
                        self._touchdown_time_credit_ns=0
                elif self.phase == 'TOUCHDOWN':
                    if loads[foot] and elapsed >= self._body_duration('TOUCHDOWN',.25):
                        # Slip is measured motion since actual landing, not error
                        # against a world command (69f58225). Keep the motor
                        # reference untouched; a measured baseline must never
                        # rewind the planned command under compliant load.
                        self.anchors[foot] = centers[foot].copy()
                        self.swing_foot = None
                        self.phase, self._phase_start = 'SETTLE', ros_ns
                    elif not loads[foot]:
                        if elapsed > 1.:
                            raise ValueError('touchdown timeout')
                        self._targets[foot][2] = max(self.floor[foot]-.002,
                            self._targets[foot][2]-self.limits['unload_speed_mps']*(dt if self.calibrating else touchdown_dt))
                elif self.phase == 'SETTLE' and elapsed >= self._body_duration('SETTLE',.25):
                    if self.calibrating:
                        self.calibrating = False
                        self.state, self.phase = 'STAND', 'STAND'
                        self.travel, self.offset = self.reference_body.copy(), np.zeros(2)
                        self._stand_start, self._stand_start_z = ros_ns, self.reference_body[2, 3]
                    else:
                        self._index = (self._index+1)%4
                        self._begin_shift(com, loads, points, ros_ns, q,command)
                self.reference_body[:3, :3] = self.travel[:3, :3]
                self.reference_body[:2, 3] = self.travel[:2, 3]+self.offset
            return self._result(self._solve(q, self.state != 'STAND'))
        except (ValueError, KeyError, TypeError, IndexError, np.linalg.LinAlgError) as error:
            return self._fail(str(error))
