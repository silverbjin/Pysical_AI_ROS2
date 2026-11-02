"""Measured-support crawl kernel; references are targets, never odometry.

Only the ROS owner may call this kernel with an authorized motion command.
Ideal-feedback tests cannot validate physical tracking; both native gates remain
mandatory. No simulator API, root setter, force override, or command odom exists.
"""
import math
import time
from copy import deepcopy

import numpy as np

from .carry_profile import _validate_limits
from .acceptance_policy import calibration_timeout_s
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

    def __init__(self, model, limits, *, reference_time_policy='bounded_20ms',mass_evaluator=None,
                 calibration_return_policy='loaded_quintic',load_transfer_policy='geometric',async_load_transfer=False,
                 kinematics_evaluator=None,load_result_timing='strict',load_receipt_mode='model_poll'):
        _validate_limits(limits)
        if kinematics_evaluator is not None and kinematics_evaluator.model_sha256!=model.model_sha256:
            raise ValueError('kinematics evaluator model binding')
        self._kinematics_evaluator=kinematics_evaluator
        if reference_time_policy not in ('bounded_20ms','applied_shift_elapsed'):
            raise ValueError('unknown reference time policy')
        self.reference_time_policy=reference_time_policy
        if calibration_return_policy not in ('loaded_quintic','bounded_preload','bounded_preload_smooth'):
            raise ValueError('unknown calibration return policy')
        self.calibration_return_policy=calibration_return_policy
        if load_transfer_policy not in ('geometric','stance_admittance','coupled_contact'):
            raise ValueError('unknown load transfer policy')
        self.load_transfer_policy=load_transfer_policy
        if (load_result_timing not in ('strict','mature_horizon','same_cycle') or
                load_result_timing in ('mature_horizon','same_cycle') and not (async_load_transfer and load_transfer_policy=='coupled_contact')
                or load_result_timing=='same_cycle' and load_receipt_mode!='event_receiver'):
            raise ValueError('load result timing requires explicit async coupled horizon scope')
        self.load_result_timing=load_result_timing
        if (load_receipt_mode not in ('model_poll','event_receiver') or
                load_receipt_mode=='event_receiver' and not (async_load_transfer and load_transfer_policy=='coupled_contact')):
            raise ValueError('event receipt requires explicit async coupled scope')
        self.load_receipt_mode=load_receipt_mode
        self._load_transfer=None
        self._reference_geometry=None
        self._actuation_evaluator=None
        if load_transfer_policy=='stance_admittance':
            from .contact_transfer import StanceLoadTransfer
            self._load_transfer=StanceLoadTransfer(model)
        elif load_transfer_policy=='coupled_contact':
            if async_load_transfer:
                from .load_process import SpatialLoadProcess
                from .native_reference import NativeReferenceEnvelope
                self._reference_geometry=NativeReferenceEnvelope(model,limits)
                if load_result_timing=='same_cycle' and self._kinematics_evaluator is None:
                    # One immutable plan, one owner/close; no additional cache.
                    self._kinematics_evaluator=self._reference_geometry
                if load_result_timing=='same_cycle':
                    from .native_equilibrium import NativeEquilibrium
                    try:self._actuation_evaluator=NativeEquilibrium(model.urdf)
                    except BaseException:
                        self._reference_geometry.close();raise
                self._load_transfer=SpatialLoadProcess(model,expected_library_sha256=(
                    mass_evaluator.provenance['library_sha256'] if mass_evaluator is not None else None),
                    command_space='stance_xyz',limits=limits,
                    receipt_mode=load_receipt_mode,
                    force_model=('gazebo_discrete_equilibrium_v1' if load_result_timing=='same_cycle' else 'spring'),
                    expected_reference_library_sha256=self._reference_geometry.provenance['library_sha256'])
            else:
                from .load_transition import SpatialLoadTransition
                self._load_transfer=SpatialLoadTransition(model,
                    terms_evaluator=mass_evaluator.contact_terms if mass_evaluator is not None else None)
        self._load_transfer_capture=None
        self._load_submitted_capture=None
        self._load_collected_reply=None
        self.load_transfer_observation=None
        self.load_balance_plan=None
        self.support_feasibility_evaluations=0
        self._planning_contact_points=None
        self.planning_reference_envelope=None
        self.planning_future_targets=None
        self._load_transfer_rest_z={}
        self._load_transfer_rest_xyz={}
        self._load_transfer_origin_xyz=None
        self._restore_next_index=True
        self._stage_observer=None
        self._mass_evaluator=mass_evaluator
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
        self._stance_reference_z = {}
        self._crawl_shift_clock = None
        self._crawl_swing_clock = None
        self._unload_time_credit_ns = 0
        self._touchdown_time_credit_ns = 0
        self._fault_landing_foot = None
        self._fault_hold_observation = False
        self._fault_transport_first_sample = False
        self.fault_stop_confirmed = False
        self._fault_settle_origin = self._fault_capture = None
        self._fault_capture_count = 0
        self.fault_events=[]
        self.fault_recovery_stage='NONE'
        self._fault_wait_start=None

    def _result(self, targets=None):
        return ControlResult(self.state, self.phase, self.swing_foot,
                             self.generation, targets, self.reason)

    def prepare_load_transfer(self):
        if self.load_transfer_policy=='coupled_contact':return self._load_transfer.prepare()
        return None

    def _discard_load_transfer(self):
        self._load_collected_reply=None
        if getattr(self._load_transfer,'asynchronous',False):self._load_transfer.discard()

    def _collect_load_transfer(self,wall_ns):
        """Receive one owned completion before model work, never apply it here.

        The existing process enforces its original 40ms transport deadline.
        Current measurements, owner/reference and original age are checked at
        the later application point. Stop/reset/fault discard this single slot.
        """
        if (self.load_result_timing=='same_cycle' or not getattr(self._load_transfer,'asynchronous',False)
                or self._load_collected_reply is not None):
            return
        try:self._load_collected_reply=self._load_transfer.poll(now_wall_ns=wall_ns)
        except ValueError as error:
            self.load_transfer_observation=dict(outcome='rejected_optimization',error=str(error),
                attempt=deepcopy(self._load_transfer.last_attempt),worker=self._load_transfer.snapshot(),
                numeric_input=deepcopy(getattr(self._load_transfer,'last_input',None)),
                original_snapshot=deepcopy(getattr(self._load_transfer,'last_context',None)),
                numeric_input_job_id=getattr(self._load_transfer,'last_input_id',None))
            raise

    def close_load_transfer(self):
        self._discard_load_transfer()
        try:
            if getattr(self._load_transfer,'asynchronous',False):return self._load_transfer.close()
            return None
        finally:
            if self._reference_geometry is not None and hasattr(self._reference_geometry,'close'):
                self._reference_geometry.close()
            if self._kinematics_evaluator is not None and self._kinematics_evaluator is not self._reference_geometry:
                self._kinematics_evaluator.close()
            if self._actuation_evaluator is not None:self._actuation_evaluator.close()

    def _fail(self, reason):
        self._discard_load_transfer()
        self._record_fault_event(reason)
        if (self.state=='FAULT' and self._fault_landing_foot is not None
                and reason=='fault landing measured support/settle lost'):
            self.fault_recovery_stage='WAIT_SAFE_ENTRY'
            return self._result()
        self._shift_plan = None
        self._fault_transport_first_sample=(self.load_result_timing=='same_cycle'
            and not self.calibrating and self.phase=='SHIFT' and self.swing_foot is None
            and self._unload_start is None and reason=='contacts:wall_age')
        self._fault_hold_observation=(self._fault_transport_first_sample or not self.calibrating and ((self.phase=='SHIFT' and (
            (self.swing_foot is None and self._unload_start is None
                and reason=='shift timeout; measured support/settle not gained')
            or (self.swing_foot is not None and self._unload_start is not None
                and reason=='measured unload height bound reached')))
            or (self.phase=='SETTLE' and reason=='stance preload restore timeout')))
        self.fault_stop_confirmed = False
        self._fault_settle_origin = self._fault_capture = None
        self._fault_capture_count = 0
        landing_reason=(reason in ('measured unload timeout','touchdown timeout')
            or self.load_transfer_policy=='coupled_contact' and reason.startswith('transition optimization'))
        self._fault_landing_foot=(self.swing_foot if not self.calibrating and landing_reason else None)
        self._fault_wait_start=None
        self.fault_recovery_stage=('WAIT_EXPLICIT_STOP' if self._fault_landing_foot is not None
            else 'HOLD_OBSERVATION' if self._fault_hold_observation else 'BLOCKED')
        self.state, self.reason = 'FAULT', self.reason or reason
        self.swing_foot = None
        return self._result()

    def _record_fault_event(self,reason):
        if self.fault_events and self.fault_events[-1]['reason']==reason:
            self.fault_events[-1]['occurrences']+=1
        else:
            self.fault_events.append(dict(reason=reason,occurrences=1,
                ros_ns=getattr(self,'_last_ros',None),wall_ns=getattr(self,'_last_wall',None)))
            if len(self.fault_events)>16:del self.fault_events[0]

    def set_stage_observer(self,observer):
        """Optional numeric boundary callback, invoked by the same model owner.

        The callback receives only a fixed stage name. It grants no credit,
        changes no input timestamp and starts no worker or file operation.
        """
        if observer is not None and not callable(observer):
            raise ValueError('stage observer must be callable or None')
        self._stage_observer=observer

    def _observe_stage(self,name):
        if self._stage_observer is not None:self._stage_observer(name)

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
        self._observe_stage('model_validate')
        centers = {}
        for foot in self.model.feet:
            angles = tuple(q[foot[:2]+'_'+part+'_joint'] for part in ('hip', 'thigh', 'calf'))
            centers[foot] = (pose @ np.array((*fk_leg(self.model, foot, angles), 1.)))[:3]
        self._observe_stage('model_fk')
        points = dict(zip(self.model.feet, data['points']))
        com = (self._mass_evaluator or center_of_mass)(self.model, q, pose)
        self._observe_stage('model_mass')
        return q, pose, centers, loads, points, com

    def reset(self, bundle, ros_ns, wall_ns, *, held_targets=None):
        self._discard_load_transfer()
        self._shift_plan = None
        self.load_balance_plan=None
        self.support_feasibility_evaluations=0
        self._planning_contact_points=None
        self.fault_events=[];self.fault_recovery_stage='NONE';self._fault_wait_start=None
        self.planning_reference_envelope=None
        self._fault_landing_foot = None
        self._fault_hold_observation = self.fault_stop_confirmed = False
        self._fault_transport_first_sample = False
        self._fault_settle_origin = self._fault_capture = None
        self._fault_capture_count = 0
        self._calibration_request = self._calibration_vertical = None
        self._stance_reference_z = {}
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
        # Supported scenes are flat. Preserve the held servo's world reference
        # height through every step, independently of measured floor/anchors.
        # Replacing it with encoder-derived floor discards preload after landing.
        self._stance_reference_z = {name:float(point[2]) for name,point in self._targets.items()}
        self._stance_origin_z=dict(self._stance_reference_z)
        self._load_transfer_capture=None
        self._load_submitted_capture=None
        self.load_transfer_observation=None
        self._load_transfer_rest_z={}
        self._load_transfer_rest_xyz={}
        self._load_transfer_origin_xyz=None
        self.planning_future_targets=None
        self._restore_next_index=True
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
        self._discard_load_transfer()
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
            ros_ns=ros_ns,wall_ns=wall_ns,deadline_wall_ns=wall_ns+int(calibration_timeout_s(self.limits)*1e9))
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
        """Sample the same curve within BOTH original elapsed-time budgets.

        Default retains the original one-nominal-step policy. The opt-in
        MuJoCo G2 SHIFT can use the actual interval after a confirmed application,
        capped at two nominal periods; the 200ms feedback/application contract
        remains independent and unchanged. No progress
        is emitted while waiting. SWING retains the original 20ms step to bound
        native sample-and-hold contact impulses. Controllers/clocks/deadlines stay.
        """
        step_limit=(40_000_000 if self.reference_time_policy=='applied_shift_elapsed'
            and self.phase=='SHIFT' else 20_000_000)
        attribute='_crawl_shift_clock' if self.phase=='SHIFT' else '_crawl_swing_clock'
        clock=getattr(self,attribute)
        if clock is None or clock['phase_origin_ros_ns']!=self._phase_start:
            clock=dict(phase_origin_ros_ns=self._phase_start,reference_elapsed_ns=0,
                nominal_step_ns=20_000_000)
            setattr(self,attribute,clock)
            step=max(0,min(step_limit,ros_ns-self._phase_start,decision_step_ns))
            clock.update(last_advance_ros_ns=ros_ns-step,last_advance_wall_ns=wall_ns-step)
        else:
            step=max(0,min(step_limit,ros_ns-clock['last_advance_ros_ns'],
                wall_ns-clock['last_advance_wall_ns']))
        if not permitted:step=0
        if step:
            clock.update(last_advance_ros_ns=ros_ns,last_advance_wall_ns=wall_ns)
        clock['reference_elapsed_ns']+=step
        clock.update(last_ros_ns=ros_ns,last_wall_ns=wall_ns,last_step_ns=step,
            policy=self.reference_time_policy,max_step_ns=step_limit,
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
        self.load_balance_plan=None
        self._planning_contact_points={f:np.asarray(p).copy() for f,p in points.items()}
        self.planning_reference_envelope=None
        self._unload_time_credit_ns = 0
        self.phase, self.swing_foot, self._phase_start = 'SHIFT', None, now
        foot = self.ORDER[self._index]
        self._offset_start = self.offset.copy()
        self._shift_duration = self._body_duration('SHIFT', .7)
        self._shift_settled_start = None
        self._unload_start = None
        self._load_transfer_origin_xyz=None
        self.planning_future_targets=None
        self._unloaded_since = None
        support = [points[n] for n in self.model.feet if n != foot and loads[n]]
        self._offset_goal = self.offset.copy()
        if len(support) < 3:
            return
        if self._load_transfer is not None and self.state=='CRAWL' and not self.calibrating:
            from .reference_envelope import height_envelope
            self.planning_reference_envelope=height_envelope(self.model,foot,points,self._targets,
                self._stance_origin_z,self._stance_reference_z,self.floor,self.limits)
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

    def _reference_constraints(self,joints,body,targets,*,selected,future_targets):
        if self.load_result_timing=='same_cycle' and self._reference_geometry is not None:
            return self._reference_geometry.evaluate(joints=joints,body=body,targets=targets,
                envelope=self.planning_reference_envelope,selected=selected,future_targets=future_targets)
        from .reference_envelope import reference_constraints
        return reference_constraints(self.model,self.limits,joints,body,targets,
            self.planning_reference_envelope,selected=selected,future_targets=future_targets)

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
            future_targets[foot]=np.r_[self._centered_swing_goal(foot,vx,wz,travel=travel),
                                      self._stance_reference_z[foot]]
        self.planning_future_targets=deepcopy(future_targets)
        def predicted_center(weight,ray=direction,progress=1.,motion=True,horizon_budget=None):
            body = reference_body.copy()
            budget=self.TRAVEL_BUDGET['SHIFT'] if horizon_budget is None else horizon_budget
            horizon=budget*progress if motion else 0.
            angle=wz*horizon;c,s=math.cos(angle),math.sin(angle)
            local=(np.array([vx*horizon,0.]) if abs(wz)<1e-12 else
                np.array([vx*math.sin(angle)/wz,vx*2*math.sin(angle/2)**2/wz]))
            body[:2,3]+=reference_body[:2,:2]@local+ray*weight*progress
            body[:3,:3]=np.array([[c,-s,0.],[s,c,0.],[0.,0.,1.]])@body[:3,:3]
            moved=future_targets if horizon_budget is not None else None
            if self.planning_reference_envelope is not None and motion and progress==1.:
                q,clear,bounds=self._reference_constraints(joints,body,
                    self._targets if moved is None else moved,
                    selected=self.ORDER[self._index],future_targets=future_targets)
                if np.min(clear)<0. or np.min(bounds)<0.:
                    raise ValueError('planned reference envelope clearance/bounds')
                self._observe_stage('model_solve')
            else:
                q=dict(joints)
                q.update(self._solve(joints, True, body,foot_targets=moved))
            value=np.asarray((self._mass_evaluator or center_of_mass)(self.model,q,body))
            if self.load_transfer_policy=='coupled_contact' and normal and motion:
                corrected=value if baseline is None else measured_com+value-baseline
                active=None if progress==1. else self.model.feet
                if progress!=1. or support_margin(corrected,support)>=desired_margin:
                    physical=self._support_actuation(q,body,corrected,self._planning_contact_points,active=active)
                    prediction['equilibrium']=physical
                    if physical is not None and not physical['feasible']:
                        raise ValueError('planned actuator support infeasible')
            return value

        baseline=None;prediction={}
        if measured_com is not None:
            # Actual support points cannot be combined with an absolute CoM
            # from the virtual command pose (46921c07: 27.2mm vs 9.88mm).
            # Predict only the IK/mass-model change from the measured CoM.
            # Slice the baseline too: at most one model candidate per yield.
            baseline=predicted_center(0.,motion=False)
            yield

        def predicted_com(weight,ray,**kwargs):
            predicted=predicted_center(weight,ray,**kwargs)
            if baseline is not None:
                predicted=measured_com+predicted-baseline
            return predicted

        def predicted_margin(weight,ray):
            return support_margin(predicted_com(weight,ray), support)

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
            if path_safe:
                if normal and self.load_transfer_policy=='stance_admittance':
                    from .contact_transfer import balanced_support_weight
                    high,self.load_balance_plan=yield from balanced_support_weight(
                        high,ray,predicted_com,support,desired_margin,
                        sum(self.TRAVEL_BUDGET.values()))
                selected=ray*high
                break
        search_method='direction'
        if selected is None and normal:
            # A feasible pose can lie between every old search ray (982b
            # regression). Use bounded local constraint projection, keeping
            # one full IK/mass evaluation per yielded control slice.
            selected=yield from self._constrained_shift(support,desired_margin,joints,
                reference_body,measured_com,baseline,vx,wz,future_targets)
            search_method='projection'
        if selected is None:raise ValueError('no footprint-bound collision-clear support shift')
        if normal and self.load_transfer_policy=='coupled_contact':
            # One common approval/effort objective AFTER either search route.
            # Local model candidates are not repeated engine experiments.
            initial=selected.copy();best=None;best_score=float('inf');best_physical=None;rows=[]
            radius=self.limits['max_foot_displacement_m']/8.
            for dx,dy in ((0.,0.),(-radius,0.),(radius,0.),(0.,-radius),(0.,radius),
                          (-radius,-radius),(-radius,radius),(radius,-radius),(radius,radius)):
                candidate=initial+np.array([dx,dy]);row=dict(delta_xy=candidate.tolist())
                try:
                    prediction.clear();point=predicted_com(1.,candidate)
                    if support_margin(point,support)<desired_margin:raise ValueError('support inset')
                    physical=prediction.get('equilibrium')
                    if physical is None or not physical['feasible']:raise ValueError('actuation evaluation missing/failed')
                    score=physical['torque_utilization'];row['torque_utilization']=score
                    if score<best_score:best,best_score,best_physical=candidate.copy(),score,physical
                except ValueError as error:row['rejected']=str(error)
                rows.append(row);yield
            if best is None:raise ValueError('no common actuation-feasible support candidate')
            rejected=None
            if not np.array_equal(best,initial):
                for progress in (.25,.5,.75):
                    try:predicted_com(1.,best,progress=progress)
                    except ValueError as error:rejected=str(error)
                    yield
                    if rejected:break
                if rejected is None:
                    try:predicted_com(1.,best,horizon_budget=sum(self.TRAVEL_BUDGET.values()))
                    except ValueError as error:rejected=str(error)
                    yield
            if rejected is not None:
                # The original searched candidate still needs the same force
                # proof; no unchecked geometric fallback is admitted.
                prediction.clear();predicted_com(1.,initial);yield
                best,best_physical=initial,prediction.get('equilibrium')
                if best_physical is None or not best_physical['feasible']:
                    raise ValueError('common support fallback force proof missing')
            selected=best
            self.load_balance_plan=dict(scope='actuation_aware_common_support_plan',
                search_method=search_method,equilibrium=best_physical,candidates=rows,
                path_rejection=rejected)
        self._offset_goal += selected
        # Quintic blend has peak |d²s/du²| = 10*sqrt(3)/3. Bound the
        # *internal* support translation, not just the incoming cmd_vel ramp.
        distance = float(np.linalg.norm(self._offset_goal-self._offset_start))
        self._shift_accel_budget = self.limits['max_support_shift_accel_mps2']
        self._shift_duration = max(.7, math.sqrt((10.*math.sqrt(3.)/3.)*distance/
            self._shift_accel_budget))
        self._shift_duration = self._body_duration('SHIFT',self._shift_duration,distance)

    def _support_actuation(self,joints,body,com,points,*,active=None):
        if self.load_transfer_policy!='coupled_contact' or self.calibrating or self.state!='CRAWL':
            return None
        from .contact_equilibrium import static_support
        self.support_feasibility_evaluations+=1
        options={}
        if self.load_result_timing=='same_cycle':
            terms=getattr(self._mass_evaluator,'contact_terms',None)
            if terms is not None:options['terms_evaluator']=terms
            if self._actuation_evaluator is not None:
                options['actuation_evaluator']=self._actuation_evaluator.contact_command_terms
        result=static_support(self.model,joints,body,points,
            tuple(f for f in self.model.feet if f!=self.ORDER[self._index]) if active is None else active,
            com=com,min_force=self.limits['min_contact_force_n'],**options)
        self._observe_stage('model_support_actuation')
        return result

    def _constrained_shift(self,support,margin,joints,reference,measured,baseline,vx,wz,future_targets):
        contact_points=self._planning_contact_points
        if contact_points is None:
            others=[f for f in self.model.feet if f!=self.ORDER[self._index]]
            contact_points={f:np.asarray(p) for f,p in zip(others,support)}
            selected=self.ORDER[self._index];contact_points[selected]=self._targets[selected].copy()
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
            if self.planning_reference_envelope is not None and progress==1.:
                q,clear,bounds=self._reference_constraints(joints,body,targets,
                    selected=self.ORDER[self._index],future_targets=future_targets)
            com=np.asarray((self._mass_evaluator or center_of_mass)(self.model,q,body))
            if measured is not None:com=measured+com-baseline
            margins=np.einsum('ij,ij->i',normals,com[:2]-points)-margin
            if self.load_transfer_policy=='coupled_contact' and (progress!=1. or np.min(margins)>=-1e-8):
                physical=self._support_actuation(q,body,com,contact_points,
                    active=None if progress==1. else self.model.feet)
                if physical is not None:
                    # Preserve the existing <=64 2D constraint dimension by
                    # intersecting one geometric scalar with the effort margin.
                    clear[0]=min(clear[0],.01*physical['margin'])
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

    def _transfer_stance_load(self,bundle,joints,pose,points,foot,dt,*,maintenance=False):
        if maintenance and self.load_result_timing!='same_cycle':
            raise ValueError('stance maintenance requires same-cycle current snapshot')
        if (self._load_transfer is None or self.calibrating or self.stopping
                or self.state!='CRAWL' or self.phase!='SHIFT' or self._unload_start is None):
            return
        coupled=self.load_transfer_policy=='coupled_contact'
        if dt<=0:return True if coupled else None
        contact=bundle.contacts
        capture=(contact.stamp_ns,contact.sequence)
        if self._load_transfer_capture==capture:return True if coupled else None
        if coupled:
            data=contact.data;vectors=np.asarray(data.get('forces_world',()),dtype=float)
            self.load_transfer_observation=dict(contact_capture=capture,selected=foot,dt=dt,
                outcome='received_for_attestation',force_vectors_valid=data.get('force_vectors_valid'),
                measured_forces=list(data['forces']),measured_forces_world=vectors.tolist())
            if (data.get('force_vectors_valid') is not True or vectors.shape!=(4,3)
                    or not np.isfinite(vectors).all()
                    or not np.allclose(vectors[:,2],data['forces'],rtol=1e-6,atol=1e-6)):
                self.load_transfer_observation['outcome']='rejected_force_attestation'
                raise ValueError('attested spatial force feedback required')
            plan=self.load_balance_plan
            if not plan or plan.get('equilibrium',{}).get('feasible') is not True:
                raise ValueError('common spatial force support plan required')
            if self.planning_reference_envelope is None:
                raise ValueError('spatial reference envelope missing')
            if getattr(self._load_transfer,'asynchronous',False):
                return self._transfer_spatial_async(bundle,joints,pose,points,foot,dt,vectors,maintenance=maintenance)
            command=dict(joints);command.update(self._solve(joints,True))
            origins=dict(self._stance_origin_z);origins[foot]=self._unload_origin_z
            try:
                delta=self._load_transfer.step(foot=foot,joints=joints,body_pose=pose,points=points,
                    forces_world=dict(zip(self.model.feet,vectors)),
                    target_forces=plan['equilibrium']['forces_world'],
                    reference_z={f:float(self._targets[f][2]) for f in self.model.feet},
                    origins=origins,allowed_z=self.planning_reference_envelope,dt=dt,
                    speed=self.limits['unload_speed_mps'],min_force=self.limits['min_contact_force_n'],
                    command_joints=command,reference_pose=self.reference_body)
            except ValueError as error:
                self.load_transfer_observation.update(outcome='rejected_optimization',error=str(error),
                    attempt=deepcopy(self._load_transfer.last_attempt))
                raise
            proposed={f:p.copy() for f,p in self._targets.items()}
            for f,step in delta.items():proposed[f][2]+=step
            self._solve(joints,True,foot_targets=proposed)  # transactional geometry validation
            for f in self.model.feet:
                if f!=foot:self._load_transfer_rest_z.setdefault(f,float(self._targets[f][2]))
            self._targets=proposed;self._load_transfer_capture=capture
            self.load_transfer_observation=dict(contact_capture=capture,selected=foot,
                selected_height_owner='coupled_optimizer',measured_forces=list(data['forces']),
                measured_forces_world=vectors.tolist(),dt=dt,applied_delta_z=delta,
                delta_scope='validated_owned_reference_not_native_application',
                linear_model=deepcopy(self._load_transfer.last_model),attempt=deepcopy(self._load_transfer.last_attempt))
            return True
        correction=self._load_transfer.correction(foot=foot,joints=joints,rotation=pose[:3,:3],
            points=points,forces=contact.data['forces'],dt=dt,
            speed=self.limits['unload_speed_mps'],min_force=self.limits['min_contact_force_n'])
        # A bounded total offset from reset prevents accumulating corrections
        # across steps. Neither measured anchors nor floor follow this command.
        applied={}
        for stance,delta in correction.items():
            origin=self._stance_origin_z[stance];bound=self.limits['max_unload_height_m']
            old=float(self._targets[stance][2]);new=min(origin+bound,max(origin-bound,old+delta))
            self._load_transfer_rest_z.setdefault(stance,old)
            self._targets[stance][2]=new
            applied[stance]=new-old
        self._load_transfer_capture=capture
        self.load_transfer_observation=dict(contact_capture=capture,selected=foot,
            measured_forces=list(contact.data['forces']),dt=dt,stance_delta_z=applied,
            linear_model=deepcopy(self._load_transfer.last_linear_model))

    def _spatial_arguments(self,joints,pose,points,foot,dt,vectors,targets=None,*,maintenance=False):
        if maintenance and self.load_result_timing!='same_cycle':
            raise ValueError('stance maintenance requires same-cycle current snapshot')
        targets=self._targets if targets is None else targets
        command=dict(joints);command.update(self._solve(joints,True,foot_targets=targets))
        origins=dict(self._stance_origin_z);origins[foot]=self._unload_origin_z
        args=dict(foot=foot,joints=joints,body_pose=pose,points=points,
            forces_world=dict(zip(self.model.feet,vectors)),
            target_forces=self.load_balance_plan['equilibrium']['forces_world'],
            allowed_z=self.planning_reference_envelope,dt=dt,speed=self.limits['unload_speed_mps'],
            min_force=self.limits['min_contact_force_n'],command_joints=command,reference_pose=self.reference_body)
        if getattr(self._load_transfer,'command_space','height')=='stance_xyz':
            if self._load_transfer_origin_xyz is None or self.planning_future_targets is None:
                raise ValueError('transition optimization original/future XYZ geometry missing')
            args.update(reference_xyz=targets,origins=self._load_transfer_origin_xyz,
                future_targets=self.planning_future_targets)
        else:args.update(reference_z={f:float(targets[f][2]) for f in self.model.feet},origins=origins)
        if maintenance:
            if 'reference_xyz' not in args:raise ValueError('stance maintenance requires XYZ geometry')
            # A STRICT subset of the original geometry. No selected motion
            # and no zero-force/unload objective while the body is unsettled.
            args['target_forces']=deepcopy(args['forces_world'])
            args['allowed_z']=dict(args['allowed_z']);z=float(targets[foot][2])
            args['allowed_z'][foot]=(z,z)
            args['future_targets']=deepcopy(args['future_targets'])
            args['future_targets'][foot]=deepcopy(targets[foot])
        return args

    def _load_context(self,bundle,foot,dt,targets=None):
        targets=self._targets if targets is None else targets
        result=dict(generation=self.generation,foot=foot,dt=dt,
            requested_ros_ns=self._last_ros,requested_wall_ns=self._last_wall,
            reference=(tuple(float(v) for v in self.reference_body.ravel()),
                tuple(tuple(float(x) for x in targets[f]) for f in self.model.feet)),
            capture=(bundle.contacts.stamp_ns,bundle.contacts.sequence),
            samples={key:(getattr(bundle,key).stamp_ns,getattr(bundle,key).received_ns,
                getattr(bundle,key).epoch) for key in ('joints','imu','body','contacts')},
            forces_world=deepcopy(bundle.contacts.data['forces_world']))
        if getattr(self._load_transfer,'command_space','height')=='stance_xyz':
            if self._load_transfer_origin_xyz is None or self.planning_future_targets is None:
                raise ValueError('transition optimization original/future XYZ geometry missing')
            result['geometry']=tuple((tuple(self._load_transfer_origin_xyz[f]),
                tuple(self.planning_future_targets[f]),tuple(self.planning_reference_envelope[f])) for f in self.model.feet)
        return result

    def _transfer_spatial_async(self,bundle,joints,pose,points,foot,dt,vectors,*,maintenance=False):
        worker=self._load_transfer;context=self._load_context(bundle,foot,dt)
        try:
            same_cycle=self.load_result_timing=='same_cycle'
            collected_before_model=self._load_collected_reply is not None
            if same_cycle:
                context['maintenance']=maintenance
                if collected_before_model:raise ValueError('same-cycle unexpected stored result')
                reply=worker.transact(self._spatial_arguments(joints,pose,points,foot,dt,vectors,maintenance=maintenance),context)
            else:
                reply=self._load_collected_reply;self._load_collected_reply=None
                if reply is None:reply=worker.poll(now_wall_ns=self._last_wall)
            if reply is None:
                if not worker.snapshot()['pending'] and context['capture']!=self._load_submitted_capture:
                    worker.submit(self._spatial_arguments(joints,pose,points,foot,dt,vectors),context)
                    self._load_submitted_capture=context['capture']
                    outcome='submitted'
                else:outcome=('waiting_for_numeric_result' if worker.snapshot()['pending'] else 'awaiting_new_capture')
                self.load_transfer_observation.update(outcome=outcome,worker=worker.snapshot(),
                    numeric_input=deepcopy(getattr(worker,'last_input',None)),
                    original_snapshot=deepcopy(getattr(worker,'last_context',None)))
                return True
            original=reply['context']
            application_wall_ns=max(self._last_wall,reply['received_wall_ns'],
                time.monotonic_ns() if collected_before_model or same_cycle else 0)
            keys=('generation','foot','reference')+(('geometry',) if 'geometry' in context else ())
            if same_cycle:keys+=('maintenance',)
            if any(original[key]!=context[key] for key in keys):
                raise ValueError('transition optimization result ownership/reference mismatch')
            for stamp,receipt,epoch in original['samples'].values():
                if (epoch!=self.epoch or not 0<=self._last_ros-stamp<=200_000_000
                        or not 0<=application_wall_ns-receipt<=200_000_000):
                    raise ValueError('transition optimization stale original snapshot')
            delta=reply['delta']
            xyz=getattr(worker,'command_space','height')=='stance_xyz'
            values=np.asarray([delta[f] for f in self.model.feet],dtype=float)
            if (set(delta)!=set(self.model.feet) or values.shape!=((4,3) if xyz else (4,))
                    or not np.isfinite(values).all()):
                raise ValueError('transition optimization result vector shape')
            magnitudes=np.linalg.norm(values,axis=1) if xyz else np.abs(values)
            if maintenance and (not xyz or np.any(values[self.model.feet.index(foot)]!=0.)):
                raise ValueError('stance maintenance selected foot must remain fixed')
            if np.max(magnitudes)>self.limits['unload_speed_mps']*original['dt']+1e-12:
                raise ValueError('transition optimization result height rate')
            elapsed=min(self._last_ros-original['requested_ros_ns'],
                self._last_wall-original['requested_wall_ns'])/1e9
            if same_cycle:
                # dt is already earned before this decision from the minimum
                # ROS/wall interval. This job uses that SAME current snapshot,
                # not a proposal whose future requested horizon must mature.
                if original['capture']!=context['capture'] or original['dt']!=dt:
                    raise ValueError('same-cycle current snapshot mismatch')
                elapsed=dt
            if elapsed<0.:
                raise ValueError('transition optimization elapsed reference rate')
            original_delta=deepcopy(delta);fraction=1.
            if np.max(magnitudes)>self.limits['unload_speed_mps']*elapsed+1e-12:
                if (self.load_result_timing=='mature_horizon' and xyz and elapsed>0.
                        and isinstance(worker.last_model,dict)
                        and worker.last_model.get('linear_origin_feasible') is False
                        and worker.last_model.get('command_space')=='stance_xyz'
                        and worker.last_model.get('future_geometry_validated') is True):
                    # Transport is complete, but this valid endpoint's ROS AND
                    # wall motion horizon has not matured. Retain exactly ONE
                    # unchanged reply; no command, resubmission, scaling or age
                    # renewal. Every next decision repeats ownership/200ms and
                    # current model checks before this same rate gate.
                    self._load_collected_reply=reply
                    self.load_transfer_observation=dict(outcome='waiting_for_reference_horizon',selected=foot,
                        delta_scope='pending_unapplied_numeric_result',
                        required_elapsed_ns=math.ceil(float(np.max(magnitudes))/self.limits['unload_speed_mps']*1e9),
                        evaluated_ros_ns=self._last_ros,evaluated_wall_ns=self._last_wall,
                        original_snapshot=deepcopy(original),numeric_input=deepcopy(reply.get('numeric_input')),
                        numeric_input_job_id=reply.get('job_id'),worker=worker.snapshot(),
                        attempt=deepcopy(worker.last_attempt))
                    return True
                if (not xyz or elapsed<=0. or not isinstance(worker.last_model,dict)
                        or worker.last_model.get('linear_origin_feasible') is not True):
                    raise ValueError('transition optimization elapsed reference rate')
                # One common fraction preserves the six-axis linear wrench
                # balance. Never clip individual feet or bank an unused tail.
                fraction=self.limits['unload_speed_mps']*elapsed/float(np.max(magnitudes))
                delta={f:(np.asarray(d)*fraction).tolist() for f,d in delta.items()}
            proposed={f:p.copy() for f,p in self._targets.items()}
            for f,d in delta.items():
                if xyz:proposed[f]+=np.asarray(d)
                else:proposed[f][2]+=d
                origin=self._unload_origin_z if f==foot else self._stance_origin_z[f]
                lo,hi=self.planning_reference_envelope[f]
                magnitude=(np.linalg.norm(proposed[f]-self._load_transfer_origin_xyz[f])
                    if xyz else abs(proposed[f][2]-origin))
                if (magnitude>self.limits['max_unload_height_m']+1e-12
                        or not lo-1e-12<=proposed[f][2]<=hi+1e-12
                        or f==foot and ((xyz and (np.max(np.abs(np.asarray(d)[:2]))>1e-12 or d[2]<0.))
                            or not xyz and d<0.)):
                    raise ValueError('transition optimization result reference bounds')
            if xyz and (not isinstance(worker.last_model,dict)
                    or worker.last_model.get('command_space')!='stance_xyz'
                    or worker.last_model.get('future_geometry_validated') is not True):
                raise ValueError('transition optimization future geometry proof missing')
            if fraction<1.:
                if self._reference_geometry is None:raise ValueError('transition optimization current geometry unavailable')
                try:
                    exact,clear,bounds=self._reference_geometry.evaluate(joints=joints,body=self.reference_body,
                        targets=proposed,envelope=self.planning_reference_envelope,selected=foot,
                        future_targets=self.planning_future_targets)
                    if np.min(clear)<0. or np.min(bounds)<0.:raise ValueError('clearance/bounds')
                except ValueError as error:
                    raise ValueError('transition optimization current geometry: '+str(error)) from error
                target={n:exact[n] for n in self.model.joint_names}
            else:target=self._solve(joints,True,foot_targets=proposed)
            discrete=(getattr(worker,'force_model','spring')=='gazebo_discrete_equilibrium_v1')
            if discrete and (not isinstance(worker.last_model,dict)
                    or worker.last_model.get('force_model')!='gazebo_discrete_equilibrium_v1'
                    or worker.last_model.get('all_actuator_caps_validated') is not True
                    or worker.last_model.get('actuator_count')!=20):
                raise ValueError('transition optimization actuator proof missing')
            if not discrete and any(abs(worker.gains[n]*(target[n]-joints[n]))>self.model.limits[n][3]+1e-6
                   for n in self.model.joint_names):
                raise ValueError('transition optimization current servo effort')
            model,attempt=deepcopy(worker.last_model),deepcopy(worker.last_attempt)
            scaling=None
            if xyz:
                prediction=model.get('predicted_forces_world')
                if fraction<1.:
                    if not isinstance(prediction,dict) or set(prediction)!=set(self.model.feet):
                        raise ValueError('transition optimization result prediction missing')
                    endpoint=np.asarray([prediction[f] for f in self.model.feet],dtype=float)
                    initial=np.asarray(original['forces_world'],dtype=float)
                    if endpoint.shape!=(4,3) or not np.isfinite(endpoint).all():
                        raise ValueError('transition optimization result prediction invalid')
                    applied=initial+fraction*(endpoint-initial)
                else:applied=None
                scaling=dict(fraction=fraction,elapsed_ros_wall_s=elapsed,
                    scope=('same_cycle_elapsed_credit_not_future_horizon' if same_cycle else
                        'convex_linear_segment_plus_current_exact_geometry_not_measurement'),
                    original_delta_xyz=original_delta,
                    predicted_forces_world=None if applied is None else dict(zip(self.model.feet,applied.tolist())))
            # Submit against the validated new reference BEFORE committing it.
            # A transport failure cannot integrate a command that was not issued.
            queued=not same_cycle and context['capture']!=original['capture']
            if queued:
                worker.submit(self._spatial_arguments(joints,pose,points,foot,dt,vectors,proposed),
                    self._load_context(bundle,foot,dt,proposed))
                self._load_submitted_capture=context['capture']
            for f in self.model.feet:
                if f!=foot:
                    if xyz:self._load_transfer_rest_xyz.setdefault(f,self._targets[f].copy())
                    else:self._load_transfer_rest_z.setdefault(f,float(self._targets[f][2]))
            self._targets=proposed;self._load_transfer_capture=original['capture']
            self.load_transfer_observation=dict(outcome='validated_numeric_result',
                maintenance=maintenance,geometry_scope=('selected_hold_stance_maintenance' if maintenance else 'full_future_envelope'),
                selected=foot,selected_height_owner='coupled_optimizer_parent_only',
                original_snapshot=original,numeric_input=reply.get('numeric_input'),
                numeric_input_job_id=reply.get('job_id'),
                delta_scope='validated_owned_reference_not_native_application',
                collected_before_model=collected_before_model,application_wall_ns=application_wall_ns,
                linear_model=model,attempt=attempt,queued_next=queued,worker=worker.snapshot())
            self.load_transfer_observation['applied_delta_xyz' if xyz else 'applied_delta_z']=delta
            if same_cycle:self.load_transfer_observation['transaction']=deepcopy(worker.last_transaction)
            if scaling is not None:self.load_transfer_observation['application_scaling']=scaling
            return True
        except ValueError as error:
            self.load_transfer_observation.update(outcome='rejected_optimization',error=str(error),
                attempt=deepcopy(worker.last_attempt),worker=worker.snapshot(),
                numeric_input=deepcopy(getattr(worker,'last_input',None)),
                original_snapshot=deepcopy(getattr(worker,'last_context',None)),
                numeric_input_job_id=getattr(worker,'last_input_id',None))
            raise

    def _restore_stance_load(self,dt):
        if (self.calibrating or self.stopping or self.state!='CRAWL' or self.phase!='SETTLE'):
            return False
        if not math.isfinite(dt) or not 0<=dt<=.2:
            raise ValueError('invalid stance restore time')
        if self._load_transfer_rest_xyz:
            for foot,neutral in self._load_transfer_rest_xyz.items():
                old=self._targets[foot];gap=neutral-old;length=np.linalg.norm(gap)
                step=self.limits['unload_speed_mps']*dt
                self._targets[foot]=(neutral.copy() if length<=step else old+gap*(step/length))
            done=all(np.array_equal(self._targets[f],p) for f,p in self._load_transfer_rest_xyz.items())
            if done:self._load_transfer_rest_xyz.clear()
            return done
        for foot,neutral in self._load_transfer_rest_z.items():
            old=float(self._targets[foot][2]);gap=neutral-old
            step=self.limits['unload_speed_mps']*dt
            self._targets[foot][2]=(neutral if abs(gap)<=step else old+math.copysign(step,gap))
        done=all(self._targets[f][2]==z for f,z in self._load_transfer_rest_z.items())
        if done:self._load_transfer_rest_z.clear()
        return done

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
        body=self.reference_body if body_pose is None else body_pose
        foot_targets=self._targets if foot_targets is None else foot_targets
        solved=None
        if self._kinematics_evaluator is not None:
            solved,clear,_=self._kinematics_evaluator.evaluate(joints=q,body=body,targets=foot_targets,
                envelope={f:(p[2],p[2]) for f,p in foot_targets.items()},
                selected=self.model.feet[0],future_targets=foot_targets)
            if moving and self.state=='CRAWL' and not self.calibrating and np.min(clear)<0.:
                raise ValueError('thigh/trunk collision clearance')
        else:inverse=np.linalg.inv(body)
        targets = {}
        for foot in self.model.feet:
            names = tuple(foot[:2]+'_'+part+'_joint' for part in ('hip', 'thigh', 'calf'))
            if solved is None:
                point = inverse @ np.array((*foot_targets[foot], 1.))
                result = ik_leg(self.model, foot, tuple(point[:3]), tuple(q[n] for n in names))
            else:result=tuple(solved[n] for n in names)
            if (solved is None and moving and self.state=='CRAWL' and not self.calibrating
                    and thigh_trunk_clearance(self.model,foot,result)<.0001):
                raise ValueError('thigh/trunk collision clearance')
            for name, value, part in zip(names, result, ('hip', 'thigh', 'calf')):
                if not math.isfinite(value) or not self.model.limits[name][0] <= value <= self.model.limits[name][1]:
                    raise ValueError('ik physical bound')
                if moving and not self.limits['gait_joint_bounds'][part][0] <= value <= self.limits['gait_joint_bounds'][part][1]:
                    raise ValueError('ik footprint joint bound')
                targets[name] = value
        self._observe_stage('model_solve')
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
                if self.reason:
                    self._land_goal[2]=min(self._land_goal[2],
                        getattr(self,'_unload_origin_z',self._land_goal[2]))
                self._land_duration=(max(.75,1.875*np.linalg.norm(self._land_goal-self._land_start)
                    /self.limits['max_swing_speed_mps'])
                    if self.reason else .75)
        elapsed = (now-self._stop_start)/1e9
        if self.swing_foot:
            foot = self.swing_foot
            self.phase = 'TOUCHDOWN'
            weight = blend(elapsed/self._land_duration)
            self._targets[foot] = self._land_start*(1-weight)+self._land_goal*weight
            if loads[foot] and (not self.reason or elapsed>=self._land_duration):
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
                if self.reason:self.fault_recovery_stage='STOPPED_FAULT'
        else:
            self._settled_start = None

    def _observe_fault_hold_stop(self,bundle,command,ros_ns,wall_ns):
        """Read-only settling after an explicit stop of a held SHIFT fault.

        Keep FAULT/reason/generation and never solve or emit new motor targets.
        A held SHIFT transport fault may begin one fresh read-only window on
        explicit stop. Any invalid/stale support or clock closes that window;
        later transport recovery cannot reopen a failed observation.
        """
        if not self._fault_hold_observation or not self._explicit_stop:
            return self._result()
        try:
            if command!=(0.,0.,0.):raise ValueError('fault stop requires zero command')
            if getattr(self,'_fault_transport_first_sample',False):
                # Explicit shutdown begins a NEW read-only measurement window.
                # Never change the fault/generation, a receipt, or a motor target.
                if ros_ns<self._last_ros or wall_ns<self._last_wall:
                    raise ValueError('fault stop clock rollback')
                self._last_ros,self._last_wall,self._progress_wall=ros_ns,wall_ns,wall_ns
                self._fault_transport_first_sample=False
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
            if (getattr(self._load_transfer,'asynchronous',False) and self.state=='CRAWL'
                    and not self.stopping and command!=(0.,0.,0.)
                    and self.phase=='SHIFT' and self._unload_start is not None):
                self._collect_load_transfer(wall_ns)
                self._observe_stage('model_collect')
            q, pose, centers, loads, points, com = self._measure(bundle, ros_ns, wall_ns)
            if (getattr(self._load_transfer,'asynchronous',False) and self.state=='CRAWL'
                    and not self.stopping and (self.phase!='SHIFT' or self._unload_start is None)):
                self._discard_load_transfer()
                self._load_transfer.poll(now_wall_ns=wall_ns)
            if fault_landing:
                self.swing_foot=self._fault_landing_foot
            for foot in self.model.feet:
                if foot != self.swing_foot and loads[foot] and np.linalg.norm(centers[foot]-self.anchors[foot]) > self.limits['max_stance_slip_m']:
                    raise ValueError('stance slip')
            if self._margin(com, loads, points) < self.limits['min_support_margin_m']:
                raise ValueError('current measured support lost')
            if fault_landing:
                if self._margin(com,loads,points,self.swing_foot)<self.limits['min_support_margin_m']:
                    raise ValueError('fault landing measured support lost')
                # Entry uses the existing bounded crawl motion envelope. The
                # final STOPPED predicate below still uses the stricter original
                # measured stop limits; landing is allowed to precede settling.
                if (np.linalg.norm(np.asarray(bundle.body.data['linear_velocity']))>self.limits['max_vx']
                        or np.linalg.norm(np.asarray(bundle.body.data['angular_velocity']))>self.limits['max_wz']):
                    if self._fault_wait_start is None:self._fault_wait_start=ros_ns
                    if (ros_ns-self._fault_wait_start)/1e9>self.limits['stop_landing_s']:
                        raise ValueError('fault landing safe-entry timeout')
                    self.fault_recovery_stage='WAIT_SAFE_ENTRY'
                    self._record_fault_event('fault landing waiting for bounded motion')
                    return self._result()
                # Explicit STOP may only land this known foot. The original
                # failure reason/generation and explicit-stop latch remain;
                # no CRAWL activation or general fault recovery is performed.
                self.state='STOPPING';self._fault_landing_foot=None
                self.fault_recovery_stage='LANDING'
                self._stop_start=self._settled_start=None
            self._observe_stage('model_safety')
            if self.calibrating:
                if self._calibration_request is None:
                    self._calibration_request = dict(ros_ns=ros_ns,wall_ns=wall_ns,
                        deadline_wall_ns=wall_ns+int(calibration_timeout_s(self.limits)*1e9))
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
                self._discard_load_transfer()
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
                    if self._load_transfer_rest_z or self._load_transfer_rest_xyz:
                        # An explicitly authorized velocity pause can have
                        # landed while holding temporary stance offsets. Finish
                        # their restoration before resuming that same step.
                        self.phase,self._phase_start='SETTLE',ros_ns
                        self._restore_next_index=False
                    else:self._begin_shift(com, loads, points, ros_ns, q,command)
                unload_dt=touchdown_dt=max(0,decision_step_ns)/1e9
                if not self.calibrating and self.phase=='SHIFT' and self._unload_start is not None:
                    foot=self.ORDER[self._index]
                    eligible=((loads[foot] or self._load_transfer is not None)
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
                    if (self.phase=='SETTLE' and self._load_transfer is not None
                            and (ros_ns-self._phase_start)/1e9>
                            self.limits['max_unload_height_m']/self.limits['unload_speed_mps']+.25):
                        raise ValueError('stance preload restore timeout')
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
                        self._load_transfer_origin_xyz=deepcopy(self._targets)
                        self.swing_foot = foot  # same owner must also land during an unload STOP
                    if self._unload_start is not None:
                        # In the explicit force-transfer mode keep the same
                        # bounded unload through100ms confirmation. Stopping
                        # on the first <2N sample makes the spring load rebound
                        # across the threshold and repeatedly resets the dwell.
                        if (not settled and not self.calibrating and self.load_result_timing=='same_cycle'):
                            # Motion eligibility must NOT disable the support
                            # servo barrier. The selected XYZ stays exactly
                            # fixed; only stance maintenance gets the already
                            # elapsed ROS/wall minimum, never banked time.
                            self._transfer_stance_load(bundle,q,pose,points,foot,
                                max(0,decision_step_ns)/1e9,maintenance=True)
                        if settled and (loads[foot] or self.calibrating or self._load_transfer is not None):
                            height = self._targets[foot][2]-self._unload_origin_z
                            if (height>self.limits['max_unload_height_m']+1e-12
                                    or self._load_transfer is None
                                    and height>=self.limits['max_unload_height_m']-1e-12):
                                raise ValueError('measured unload height bound reached')
                            managed=False
                            if not self.calibrating:
                                managed=self._transfer_stance_load(bundle,q,pose,points,foot,unload_dt)
                            if not managed:
                                self._targets[foot][2] += min(self.limits['unload_speed_mps']*(dt if self.calibrating else unload_dt),
                                    max(0.,self.limits['max_unload_height_m']-height))
                        full_future=(self.load_result_timing!='same_cycle' or
                            isinstance(self.load_transfer_observation,dict)
                            and self.load_transfer_observation.get('outcome')=='validated_numeric_result'
                            and self.load_transfer_observation.get('maintenance') is False)
                        if settled and full_future and not loads[foot]:
                            if self._unloaded_since is None:
                                self._unloaded_since = ros_ns
                        else:
                            self._unloaded_since = None
                        unload_deadline = self.limits['max_unload_height_m']/self.limits['unload_speed_mps']+1.
                        if (ros_ns-self._unload_start)/1e9 > unload_deadline:
                            raise ValueError('measured unload timeout')
                    if self._unloaded_since is not None and ros_ns-self._unloaded_since >= 100_000_000:
                        self._discard_load_transfer()
                        self.phase, self.swing_foot, self._phase_start = 'SWING', foot, ros_ns
                        if self.calibrating:
                            self._calibration_vertical = InPlaceCalibration(
                                start_z=float(self._targets[foot][2]),rest_z=self._unload_origin_z,
                                baseline_z=self.floor[foot],limits=self.limits,ros_ns=ros_ns,wall_ns=wall_ns,
                                deadline_wall_ns=self._calibration_request['deadline_wall_ns'],
                                return_policy=self.calibration_return_policy)
                            self._record_calibration(bundle,ros_ns,wall_ns)
                            return self._result(self._solve(q,True))
                        self._swing_start = self._targets[foot].copy()
                        self._swing_goal = self._swing_start.copy()
                        self._swing_goal[2] = self._stance_reference_z[foot]
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
                        self._restore_next_index=True
                    elif not loads[foot]:
                        if elapsed > 1.:
                            raise ValueError('touchdown timeout')
                        self._targets[foot][2] = max(min(self.floor[foot],self._stance_reference_z[foot])-.002,
                            self._targets[foot][2]-self.limits['unload_speed_mps']*(dt if self.calibrating else touchdown_dt))
                elif self.phase == 'SETTLE' and elapsed >= self._body_duration('SETTLE',.25):
                    if self._load_transfer is not None and not self.calibrating:
                        complete=all(loads.values()) and self._restore_stance_load(max(0,decision_step_ns)/1e9)
                        body=bundle.body.data
                        quiet=(np.linalg.norm(body['linear_velocity'])<=self.limits['stopped_v_mps']
                            and np.linalg.norm(body['angular_velocity'])<=self.limits['stopped_wz_rps'])
                        if not complete or not quiet:
                            if elapsed>self.limits['max_unload_height_m']/self.limits['unload_speed_mps']+.25:
                                raise ValueError('stance preload restore timeout')
                            return self._result(self._solve(q,True))
                    if self.calibrating:
                        self.calibrating = False
                        self.state, self.phase = 'STAND', 'STAND'
                        self.travel, self.offset = self.reference_body.copy(), np.zeros(2)
                        self._stand_start, self._stand_start_z = ros_ns, self.reference_body[2, 3]
                    else:
                        if self._restore_next_index:self._index = (self._index+1)%4
                        self._restore_next_index=True
                        self._begin_shift(com, loads, points, ros_ns, q,command)
                self.reference_body[:3, :3] = self.travel[:3, :3]
                self.reference_body[:2, 3] = self.travel[:2, 3]+self.offset
                self._observe_stage('model_reference')
            return self._result(self._solve(q, self.state != 'STAND'))
        except (ValueError, KeyError, TypeError, IndexError, np.linalg.LinAlgError) as error:
            return self._fail(str(error))
