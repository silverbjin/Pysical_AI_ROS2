"""G1-only measured vertical reference; no actuator, clock or ROS ownership.

STAND is a candidate, not an acceptance result. The existing controller must
still measure all contacts, joint/body speeds and its full wall settle lease.
"""
from dataclasses import dataclass
import math


def precondition_loaded_reference(*, z, rest_z, measured_reference_z, forces, dt, limits):
    """Release a little held compression while ALL four measured feet stay loaded.

    Not a lift authorization: final tripod/settle/unload checks remain the owner.
    The original rest is immutable and still bounds the complete unload/return.
    """
    if (not all(math.isfinite(v) for v in (z,rest_z,measured_reference_z,dt)) or not 0<=dt<=.2
            or len(forces)!=4 or not all(math.isfinite(f) and f>=0 for f in forces)
            or not rest_z<=z<=rest_z+limits['max_unload_height_m']+1e-12):
        raise ValueError('invalid preconditioning reference/time')
    force=limits['min_contact_force_n']
    if any(f<force for f in forces):
        raise ValueError('preconditioning support lost before settled unload')
    if forces[1]<5*force:
        return float(z)
    # FK of measured joints in the SAME reference body frame measures the
    # tracking compression still available. An ideal stiff follower has none.
    # Consume at most half that gap, retaining actual10N/all-four-load checks.
    # Neither the reference nor this gap is a physical foot-height observation.
    ceiling=min(rest_z+limits['max_unload_height_m'],
                z+.5*max(0.,measured_reference_z-z))
    return float(min(ceiling,z+limits['unload_speed_mps']*dt) if z<ceiling else z)


@dataclass(frozen=True)
class CalibrationStep:
    z: float
    phase: str
    complete: bool


class InPlaceCalibration:
    def __init__(self, *, start_z, rest_z, baseline_z, limits, ros_ns, wall_ns, deadline_wall_ns,
                 return_policy='loaded_quintic'):
        if return_policy not in ('loaded_quintic','bounded_preload','bounded_preload_smooth'):
            raise ValueError('unknown calibration return policy')
        self.return_policy=return_policy
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
        self.return_brake = None
        self.loaded_contact = None
        self.loaded_brake = None
        self.previous_return_plan = None
        self.loaded_speed = min(self.speed,.01,2*self.seek)
        self.settle_s = limits['settle_s']

    def _make_return_plan(self, start_ros_ns, start_z, speed, acceleration):
        distance = start_z-self.rest_z
        if distance < -1e-12:
            raise ValueError('calibration preload stopping distance')
        distance=max(0.,distance)
        # Preserve the existing brake's jerk envelope as lower-speed ramps
        # otherwise get shorter even when their acceleration remains bounded.
        shape=10*math.sqrt(3)/3
        jerk=shape*.02/.1875**2
        peak = min(speed,math.sqrt(distance*acceleration/1.875),
                   (distance*distance*jerk/shape)**(1/3))
        ramp = max(1.875*peak/acceleration,math.sqrt(shape*peak/jerk))
        cruise = max(0.,distance/peak-ramp) if peak else 0.
        return dict(profile='quintic_velocity',start_ros_ns=start_ros_ns,start_z=start_z,
            ramp_s=ramp,cruise_s=cruise,peak_mps=peak,duration_s=2*ramp+cruise,
            nominal_speed_mps=speed,nominal_acceleration_mps2=acceleration)

    def _bounded_preload_return(self,ros_ns,dt):
        """Gazebo's measured G1 return from the fixed af6da055 success source.

        Reuses the original .02m/s/.2m/s² envelope and preload endpoint. Contact
        and unique loaded captures remain completion conditions in advance().
        This is explicit configuration, never a fallback after a budget fault.
        """
        acceleration=self.speed/.1
        if self.return_plan is None:
            previous=self.velocity
            self.velocity=max(0.,previous-acceleration*dt)
            self.z=min(self.ceiling,self.z+.5*(previous+self.velocity)*dt)
            if self.velocity>0.:return
            distance=self.z-self.rest_z
            if self.return_policy=='bounded_preload_smooth':
                self.return_plan=self._make_return_plan(ros_ns,self.z,self.speed,acceleration)
            else:
                peak=min(self.speed,math.sqrt(distance*acceleration))
                ramp=peak/acceleration
                cruise=max(0.,distance/peak-ramp) if peak else 0.
                self.return_plan=dict(start_ros_ns=ros_ns,start_z=self.z,
                    ramp_s=ramp,cruise_s=cruise,peak_mps=peak,duration_s=2*ramp+cruise)
        if self.return_policy=='bounded_preload_smooth':
            self._sample_quintic_return(ros_ns);return
        plan=self.return_plan;elapsed=(ros_ns-plan['start_ros_ns'])/1e9
        ramp,cruise,peak=plan['ramp_s'],plan['cruise_s'],plan['peak_mps']
        if elapsed>=plan['duration_s']:
            self.z,self.velocity=self.rest_z,0.
        elif elapsed<=ramp:
            self.z=plan['start_z']-.5*acceleration*elapsed**2
            self.velocity=-acceleration*elapsed
        elif elapsed<=ramp+cruise:
            self.z=plan['start_z']-.5*peak*ramp-peak*(elapsed-ramp)
            self.velocity=-peak
        else:
            remaining=plan['duration_s']-elapsed
            self.z=self.rest_z+.5*acceleration*remaining**2
            self.velocity=-acceleration*remaining

    def _planned_return(self, ros_ns, dt):
        """G1-only rest return, independent of early compliant contact.

        Brake upward motion, then use quintic velocity ramps. The original
        speed and acceleration bounds are retained, with continuous acceleration
        at brake/ramp/cruise/end boundaries. Contact still cannot truncate the
        original preload endpoint or replace measured owner settle.
        """
        if self.return_policy in ('bounded_preload','bounded_preload_smooth'):
            return self._bounded_preload_return(ros_ns,dt)
        acceleration = self.speed/.1
        def blend(u):return u*u*u*(10.+u*(-15.+6.*u))
        def integral(u):return u**4*(2.5+u*(-3.+u))
        if self.return_plan is None:
            if self.return_brake is None:
                self.return_brake=dict(start_ros_ns=ros_ns-int(round(dt*1e9)),start_z=self.z,
                    start_velocity=self.velocity,duration_s=1.875*self.velocity/acceleration)
            brake=self.return_brake;duration=brake['duration_s']
            elapsed=(ros_ns-brake['start_ros_ns'])/1e9
            u=min(1.,max(0.,elapsed/duration)) if duration else 1.
            self.velocity=brake['start_velocity']*(1.-blend(u))
            self.z=min(self.ceiling,brake['start_z']+brake['start_velocity']*duration*(u-integral(u)))
            if elapsed<duration:
                return
            # G1 only: contact may occur before the preload endpoint while
            # the return is still cruising. Use a lower nominal descent;
            # keep the original envelope and upward brake unchanged.
            return_speed=self.loaded_speed if self.loaded_contact else min(self.speed,.01)
            return_acceleration=min(acceleration,.1)
            self.return_plan = self._make_return_plan(
                brake['start_ros_ns']+int(round(duration*1e9)),self.z,return_speed,return_acceleration)
            remaining=max(0.,self.return_plan['duration_s']-
                (ros_ns-self.return_plan['start_ros_ns'])/1e9)
            if (self.loaded_contact and self.last_wall+int((remaining+self.settle_s)*1e9)
                    >= self.deadline):
                raise ValueError('calibration loaded return leaves no original wall settle budget')
        plan = self.return_plan
        elapsed = max(0.,(ros_ns-plan['start_ros_ns'])/1e9)
        ramp,cruise,peak = plan['ramp_s'],plan['cruise_s'],plan['peak_mps']
        if (self.loaded_contact and self.loaded_brake is None and peak>self.loaded_speed
                and ramp<=elapsed<ramp+cruise):
            # Join the zero-acceleration cruise at the current decision, never
            # rewind to a delayed contact capture or latch a raised endpoint.
            z=plan['start_z']-.5*peak*ramp-peak*(elapsed-ramp)
            duration=1.875*peak/min(acceleration,.1)
            endpoint=z-.5*peak*duration
            tail=self._make_return_plan(ros_ns+int(round(duration*1e9)),endpoint,
                                       self.loaded_speed,min(acceleration,.1))
            if self.last_wall+int((duration+tail['duration_s']+self.settle_s)*1e9)>=self.deadline:
                raise ValueError('calibration loaded return leaves no original wall settle budget')
            self.previous_return_plan=dict(plan)
            self.loaded_brake=dict(start_ros_ns=ros_ns,start_z=z,start_velocity=-peak,
                                   duration_s=duration,complete=False)
        if self.loaded_brake is not None and not self.loaded_brake['complete']:
            brake=self.loaded_brake
            elapsed=(ros_ns-brake['start_ros_ns'])/1e9
            duration=brake['duration_s'];u=min(1.,max(0.,elapsed/duration))
            self.z=brake['start_z']+brake['start_velocity']*duration*(u-integral(u))
            self.velocity=brake['start_velocity']*(1-blend(u))
            if elapsed<duration:return
            self.return_plan=self._make_return_plan(brake['start_ros_ns']+int(round(duration*1e9)),
                self.z,self.loaded_speed,min(acceleration,.1))
            brake['complete']=True
            plan=self.return_plan;elapsed=max(0.,(ros_ns-plan['start_ros_ns'])/1e9)
            ramp,cruise,peak=plan['ramp_s'],plan['cruise_s'],plan['peak_mps']
        self._sample_quintic_return(ros_ns)

    def _sample_quintic_return(self,ros_ns):
        # Same quintic velocity integral used by the existing loaded policy.
        # The G1-only full-speed profile changes no physical endpoint or cap.
        def blend(u):return u*u*u*(10.+u*(-15.+6.*u))
        def integral(u):return u**4*(2.5+u*(-3.+u))
        plan=self.return_plan;elapsed=max(0.,(ros_ns-plan['start_ros_ns'])/1e9)
        ramp,cruise,peak=plan['ramp_s'],plan['cruise_s'],plan['peak_mps']
        if elapsed >= plan['duration_s']:
            self.z,self.velocity = self.rest_z,0.
        elif elapsed <= ramp:
            u=elapsed/ramp
            self.z = plan['start_z']-peak*ramp*integral(u)
            self.velocity = -peak*blend(u)
        elif elapsed <= ramp+cruise:
            self.z = plan['start_z']-.5*peak*ramp-peak*(elapsed-ramp)
            self.velocity = -peak
        else:
            remaining = plan['duration_s']-elapsed
            u=remaining/ramp
            self.z = self.rest_z+peak*ramp*integral(u)
            self.velocity = -peak*blend(u)

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
                if fresh and forces[1]>=self.force and self.loaded_contact is None:
                    self.loaded_contact=dict(capture_ns=capture_ns,ros_ns=ros_ns,wall_ns=wall_ns,
                        force_n=forces[1])
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
            return_policy=self.return_policy,
            deadline_wall_ns=self.deadline,last_update_wall_ns=self.last_wall,
            remaining_wall_ns=max(0,self.deadline-self.last_wall),
            target_z=self.z,velocity=self.velocity,rest_z=self.rest_z,baseline_z=self.baseline_z,
            lift_captures=list(self.lift_captures),landing_captures=list(self.landing_captures),
            transitions=[dict(row) for row in self.transitions],
            return_plan=None if self.return_plan is None else dict(self.return_plan),
            return_brake=None if self.return_brake is None else dict(self.return_brake),
            loaded_contact=None if self.loaded_contact is None else dict(self.loaded_contact),
            loaded_brake=None if self.loaded_brake is None else dict(self.loaded_brake),
            previous_return_plan=None if self.previous_return_plan is None else dict(self.previous_return_plan),
            measurement=None if self.measurement is None else dict(self.measurement),fault=self.fault)
