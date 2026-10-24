"""G1-only measured vertical reference; no actuator, clock or ROS ownership.

STAND is a candidate, not an acceptance result. The existing controller must
still measure all contacts, joint/body speeds and its full wall settle lease.
"""
from dataclasses import dataclass
import math


def precondition_loaded_reference(*, z, rest_z, floor_z, forces, dt, limits):
    """Release a little held compression while ALL four measured feet stay loaded.

    Not a lift authorization: final tripod/settle/unload checks remain the owner.
    The original rest is immutable and still bounds the complete unload/return.
    """
    if (not all(math.isfinite(v) for v in (z,rest_z,floor_z,dt)) or not 0<=dt<=.2
            or len(forces)!=4 or not all(math.isfinite(f) and f>=0 for f in forces)
            or not rest_z<=z<=rest_z+limits['max_unload_height_m']+1e-12):
        raise ValueError('invalid preconditioning reference/time')
    force=limits['min_contact_force_n']
    if any(f<force for f in forces):
        raise ValueError('preconditioning support lost before settled unload')
    if forces[1]<5*force:
        return float(z)
    ceiling=min(rest_z+min(.003,limits['max_unload_height_m']),floor_z-.0002)
    return float(min(ceiling,z+limits['unload_speed_mps']*dt) if z<ceiling else z)


@dataclass(frozen=True)
class CalibrationStep:
    z: float
    phase: str
    complete: bool


class InPlaceCalibration:
    def __init__(self, *, start_z, rest_z, baseline_z, limits, ros_ns, wall_ns, deadline_wall_ns):
        if (not all(math.isfinite(v) for v in (start_z,rest_z,baseline_z))
                or limits['swing_height_m'] < .006 or rest_z > start_z
                or start_z > baseline_z+limits['swing_height_m'] or wall_ns >= deadline_wall_ns):
            raise ValueError('invalid calibration reference/budget')
        self.z, self.rest_z, self.baseline_z = float(start_z),float(rest_z),float(baseline_z)
        self.ceiling = baseline_z+limits['swing_height_m']
        self.speed = limits['max_swing_speed_mps']
        self.seek = min(self.speed,limits['unload_speed_mps'])
        self.force = limits['min_contact_force_n']
        self.velocity = self.seek
        self.phase, self.fault = 'SWING',''
        self.last_ros, self.last_wall = ros_ns,wall_ns
        self.deadline = deadline_wall_ns
        self.last_capture = -1
        self.lift_captures, self.landing_captures = [],[]
        self.transitions = [dict(phase='SWING',ros_ns=ros_ns,wall_ns=wall_ns)]
        self.measurement = None
        self.return_plan = None

    def _planned_return(self, ros_ns, dt):
        """G1-only rest return, independent of early compliant contact.

        Brake the upward reference first, then integrate an analytic triangular
        or trapezoidal speed profile. Position and velocity are continuous and
        the endpoint has zero speed; force is still required for completion.
        """
        acceleration = self.speed/.1
        if self.return_plan is None:
            previous = self.velocity
            self.velocity = max(0.,previous-acceleration*dt)
            self.z = min(self.ceiling,self.z+.5*(previous+self.velocity)*dt)
            if self.velocity > 0.:
                return
            distance = self.z-self.rest_z
            peak = min(self.speed,math.sqrt(distance*acceleration))
            ramp = peak/acceleration
            cruise = max(0.,distance/peak-ramp) if peak else 0.
            self.return_plan = dict(start_ros_ns=ros_ns,start_z=self.z,
                ramp_s=ramp,cruise_s=cruise,peak_mps=peak,duration_s=2*ramp+cruise)
        plan = self.return_plan
        elapsed = (ros_ns-plan['start_ros_ns'])/1e9
        ramp,cruise,peak = plan['ramp_s'],plan['cruise_s'],plan['peak_mps']
        if elapsed >= plan['duration_s']:
            self.z,self.velocity = self.rest_z,0.
        elif elapsed <= ramp:
            self.z = plan['start_z']-.5*acceleration*elapsed**2
            self.velocity = -acceleration*elapsed
        elif elapsed <= ramp+cruise:
            self.z = plan['start_z']-.5*peak*ramp-peak*(elapsed-ramp)
            self.velocity = -peak
        else:
            remaining = plan['duration_s']-elapsed
            self.z = self.rest_z+.5*acceleration*remaining**2
            self.velocity = -acceleration*remaining

    def _transition(self, phase, ros_ns, wall_ns):
        self.phase = phase
        self.transitions.append(dict(phase=phase,ros_ns=ros_ns,wall_ns=wall_ns))

    def advance(self, *, ros_ns, wall_ns, center_z, forces, capture_ns):
        if self.fault:
            raise ValueError(self.fault)
        try:
            if ros_ns < self.last_ros or wall_ns < self.last_wall:
                raise ValueError('calibration clock rollback')
            if wall_ns >= self.deadline:
                raise ValueError('calibration original wall deadline')
            dt = (ros_ns-self.last_ros)/1e9
            if dt > .2 or wall_ns-self.last_wall > 200_000_000:
                raise ValueError('calibration control gap')
            if (not math.isfinite(center_z) or len(forces)!=4
                    or not all(math.isfinite(f) and f>=0 for f in forces)
                    or type(capture_ns) is not int or not 0<=capture_ns<=ros_ns):
                raise ValueError('calibration invalid measurement/capture')
            self.last_ros,self.last_wall = ros_ns,wall_ns
            fresh = capture_ns>self.last_capture
            self.last_capture = max(self.last_capture,capture_ns)
            self.measurement = dict(center_z=center_z,forces=list(forces),capture_ns=capture_ns,
                                    ros_ns=ros_ns,wall_ns=wall_ns)
            if self.phase=='SWING':
                qualified = center_z-self.baseline_z>=.006 and forces[1]<self.force
                if not qualified:
                    self.lift_captures.clear()
                elif fresh:
                    self.lift_captures.append(capture_ns)
                if len(self.lift_captures)>=3:
                    self._transition('TOUCHDOWN',ros_ns,wall_ns)
            if self.phase=='TOUCHDOWN':
                self._planned_return(ros_ns,dt)
                qualified = (self.z==self.rest_z and self.velocity==0.
                    and forces[1]>=2*self.force and all(forces[i]>=self.force for i in (0,2,3)))
                if not qualified:
                    self.landing_captures.clear()
                elif fresh:
                    self.landing_captures.append(capture_ns)
                if len(self.landing_captures)>=3:
                    self.velocity = 0.
                    self._transition('STAND',ros_ns,wall_ns)
                return CalibrationStep(self.z,self.phase,self.phase=='STAND')
            if self.phase=='SWING':
                demand = self.speed
                if self.z>=self.ceiling-1e-12:
                    raise ValueError('calibration measured lift not gained within envelope')
            else:
                demand = 0.
            change = self.speed/.1*dt
            self.velocity += min(change,max(-change,demand-self.velocity))
            self.z = min(self.ceiling,max(self.rest_z,self.z+self.velocity*dt))
            return CalibrationStep(self.z,self.phase,self.phase=='STAND')
        except (ValueError,TypeError) as error:
            self.fault = self.fault or str(error)
            raise ValueError(self.fault) from error

    def snapshot(self):
        return dict(scope='candidate_requires_owner_measured_stand_settle', phase=self.phase,
            deadline_wall_ns=self.deadline,last_update_wall_ns=self.last_wall,
            remaining_wall_ns=max(0,self.deadline-self.last_wall),
            target_z=self.z,velocity=self.velocity,rest_z=self.rest_z,baseline_z=self.baseline_z,
            lift_captures=list(self.lift_captures),landing_captures=list(self.landing_captures),
            transitions=[dict(row) for row in self.transitions],
            return_plan=None if self.return_plan is None else dict(self.return_plan),
            measurement=None if self.measurement is None else dict(self.measurement),fault=self.fault)
