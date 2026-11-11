"""Standard actions with engine-measured completion and a sole PD target slot."""
import math
from ch13_navigation_reuse.callback_timing import timed_callback
import time
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from rclpy.action import ActionServer,GoalResponse,CancelResponse
from rclpy.callback_groups import ReentrantCallbackGroup
from rclpy.task import Future
from control_msgs.action import FollowJointTrajectory,GripperCommand
from trajectory_msgs.msg import JointTrajectoryPoint
from ch13_navigation_reuse.command_gateway import N
from .trajectory import JOINTS,Trajectory
from .bias_reference import bias_reference
from .gripper_force import ForceHold

ARM=N+'/manipulation/arm_controller/follow_joint_trajectory'
GRIPPER=N+'/manipulation/gripper_controller/gripper_cmd'


def gripper_stalled(position,command,velocity,effort):
    # A position PD can balance a contact below the actuator cap. This only
    # reports mechanical blockage; dual contact/lift are separate pick checks.
    return abs(position-command)>.002 and abs(velocity)<=.001 and abs(effort)>.01


class ActionBridge:
    def __init__(self,extension):
        self.extension,self.node=extension,extension.node
        self.measured=None;self.limits=None;self.reserved=False;self.active=None
        self.command=None;self.gripper_command=None;self.gripper_effort=.5
        self.pending_path=None;self.feedback=None;self.rows=[];self.events=[]
        self.bias_start=None;self.servo_command=None
        self.gripper_hold=ForceHold()
        self.validation_worker=ThreadPoolExecutor(max_workers=1,thread_name_prefix='reuse_trajectory_validation')
        group=ReentrantCallbackGroup()
        self.arm_server=ActionServer(self.node,FollowJointTrajectory,ARM,self.arm_execute,
                                     goal_callback=self.arm_goal,cancel_callback=self.cancel,
                                     callback_group=group)
        self.gripper_server=ActionServer(self.node,GripperCommand,GRIPPER,self.gripper_execute,
                                         goal_callback=self.gripper_goal,cancel_callback=self.cancel,
                                         callback_group=group)

    @property
    def busy(self):
        return self.reserved or self.active is not None

    def admissible(self):
        return self.extension.lease.phase=='READY' and self.measured is not None and not self.busy

    async def arm_goal(self,request):
        with self.node.lock:
            if not self.admissible() or self.limits is None:
                self.events.append(dict(event='goal_rejected',reason='admission',phase=self.extension.lease.phase,busy=self.busy))
                return GoalResponse.REJECT
            current=np.array(self.measured,copy=True);limits=np.array(self.limits,copy=True)
            self.reserved=True
        completed=Future(executor=self.node.executor)
        def validate():
            try:return self.validate_request(request,current,limits)
            except (ValueError,TypeError,KeyError) as error:return error
        job=self.validation_worker.submit(validate)
        job.add_done_callback(lambda done:completed.set_result(done.result()))
        outcome=await completed
        with self.node.lock:
            if isinstance(outcome,Exception):
                self.events.append(dict(event='goal_rejected',reason=str(outcome),
                                        stamp_sec=request.trajectory.header.stamp.sec,
                                        stamp_nanosec=request.trajectory.header.stamp.nanosec,
                                        point_count=len(request.trajectory.points)))
                self.reserved=False
                return GoalResponse.REJECT
            if self.extension.lease.phase!='READY' or np.max(abs(np.array(self.measured)-current))>.025:
                self.reserved=False
                self.events.append(dict(event='goal_rejected',reason='state_or_lease_changed_during_validation'))
                return GoalResponse.REJECT
            self.pending_path=outcome
            return GoalResponse.ACCEPT

    @staticmethod
    def validate_request(request,current,limits):
        if request.trajectory.header.stamp.sec or request.trajectory.header.stamp.nanosec:
            raise ValueError('only immediate, engine-timed trajectories supported')
        if request.trajectory.header.frame_id not in ('','reuse/base','reuse/odom','reuse/map'):
            raise ValueError('joint trajectory frame')
        if request.multi_dof_trajectory.points or request.path_tolerance or request.goal_tolerance:
            raise ValueError('only fixed audited tolerances and arm joints supported')
        if len(request.trajectory.points)>2000:raise ValueError('trajectory admission point budget')
        points=[dict(time=p.time_from_start.sec+p.time_from_start.nanosec/1e9,
                     positions=p.positions,velocities=p.velocities,accelerations=p.accelerations)
                for p in request.trajectory.points]
        return Trajectory.from_points(tuple(request.trajectory.joint_names),points,current,limits,
                                      validation_deadline=time.monotonic()+2.)

    def gripper_goal(self,request):
        with self.node.lock:
            position,effort=request.command.position,request.command.max_effort
            if (not self.admissible() or not all(math.isfinite(x) for x in (position,effort))
                    or not 0<=position<=.05 or not 0<=effort<=.5):
                self.events.append(dict(event='goal_rejected',kind='gripper',reason='admission_or_command',
                    phase=self.extension.lease.phase,fault=self.extension.lease.fault,
                    busy=self.busy,reserved=self.reserved,measured=self.measured is not None,
                    active_kind=None if self.active is None else self.active['kind'],
                    active_done=None if self.active is None else self.active['done'],
                    position=position,max_effort=effort,wall=time.monotonic()))
                return GoalResponse.REJECT
            self.reserved=True
            self.events.append(dict(event='goal_admitted',kind='gripper',position=position,
                                    max_effort=effort,wall=time.monotonic()))
            return GoalResponse.ACCEPT

    def cancel(self,handle):
        with self.node.lock:
            if self.active is None or self.active['handle'] is not handle:return CancelResponse.REJECT
            self.active['stop_request']='cancel'
            self.events.append(dict(event='cancel_ack',goal=bytes(handle.goal_id.uuid).hex(),wall=time.monotonic()))
        return CancelResponse.ACCEPT

    async def execute(self,handle,kind):
        with self.node.lock:
            if self.extension.lease.phase!='READY':
                self.reserved=False;handle.abort()
                if kind=='arm':return FollowJointTrajectory.Result(error_code=-1,error_string='live lease lost before execution')
                return GripperCommand.Result(reached_goal=False,stalled=False)
            self.extension.lease.begin_execution()
            if kind=='arm' and self.bias_start is None:self.bias_start=self.node.guard.clock_ns/1e9
            future=Future(executor=self.node.executor)
            self.active=dict(kind=kind,handle=handle,future=future,start=self.node.guard.clock_ns/1e9,
                             wall_start=time.monotonic(),path=self.pending_path if kind=='arm' else None,
                             stop_request='',stopping=False,settle_since=None,done=False)
            if kind=='gripper':
                self.gripper_command=float(handle.request.command.position)
                self.gripper_effort=float(handle.request.command.max_effort) or .5
            self.reserved=False
            self.events.append(dict(event='started',kind=kind,goal=bytes(handle.goal_id.uuid).hex(),
                                    sim_s=self.active['start'],wall=self.active['wall_start']))
        outcome=await future
        with self.node.lock:
            self.active=None
            if self.extension.lease.phase=='EXECUTING':self.extension.lease.phase='READY'
        if outcome['terminal']=='succeeded':handle.succeed()
        elif outcome['terminal']=='canceled':handle.canceled()
        else:handle.abort()
        if kind=='arm':
            return FollowJointTrajectory.Result(error_code=0 if outcome['terminal'] in ('succeeded','canceled') else -4,
                                                 error_string=outcome['reason'])
        return GripperCommand.Result(position=outcome['position'],effort=outcome['effort'],
                                     reached_goal=outcome['reached'],stalled=outcome['stalled'])

    async def arm_execute(self,handle):return await self.execute(handle,'arm')
    async def gripper_execute(self,handle):return await self.execute(handle,'gripper')

    def finish(self,terminal,reason,**values):
        active=self.active
        if active is None or active['done']:return
        active['done']=True
        outcome=dict(terminal=terminal,reason=reason,**values)
        self.events.append(dict(event='measured_terminal',kind=active['kind'],
                                goal=bytes(active['handle'].goal_id.uuid).hex(),
                                wall=time.monotonic(),**outcome))
        active['future'].set_result(outcome)

    def before(self,p,clock_ns):
        sim_s=clock_ns/1e9
        if self.command is None:self.command=p.desired_joint_pos_arm.copy()
        if self.gripper_command is None:self.gripper_command=float(p.desired_joint_pos_gripper)
        active=self.active
        if active is not None and not active['done']:
            if self.extension.lease.phase in ('FAULT','REVOKED') and not active['stop_request']:
                active['stop_request']='lease:'+self.extension.lease.fault
            if active['stop_request'] and not active['stopping']:
                active['stopping']=True;active['settle_since']=None
                if active['kind']=='arm':
                    try:
                        active['path']=active['path'].brake(sim_s-active['start'])
                        active['start']=sim_s
                    except ValueError:
                        # Do not pretend an unachievable brake was a successful cancel.
                        self.extension.lease.trip('BRAKE_NOT_FEASIBLE')
                        active['path']=None
                elif self.gripper_hold.start is None:self.gripper_command=float(p.mjData.qpos[25])
            if active['kind']=='arm' and active['path'] is not None:
                self.command=active['path'].sample(sim_s-active['start'])[0]
        if self.servo_command is None:self.servo_command=self.command.copy()
        if self.bias_start is not None:
            try:
                scale=max(0.,min(1.,(sim_s-self.bias_start)/.5))
                self.servo_command=bias_reference(self.command,p.mjData.qfrc_bias[18:24],p.Kp_arm,
                                                  p.mjModel.actuator_forcerange[12:18,1],scale)
            except ValueError:self.extension.lease.trip('MODEL_BIAS_INVALID')
        else:self.servo_command=self.command.copy()
        p.desired_joint_pos_arm[:]=self.servo_command
        p.desired_joint_pos_gripper=self.gripper_command
        if hasattr(self.extension,'pick_monitor'):
            message=self.extension.lease.message or {}
            allowed=(self.extension.lease.phase in ('READY','EXECUTING') and active is not None
                     and active['kind']=='gripper' and not active['stopping'])
            try:
                p.desired_joint_pos_gripper=self.gripper_hold.update(sim_s,message.get('task_phase','WAITING'),
                    self.gripper_command,self.gripper_effort,self.extension.pick_monitor.forces,
                    float(p.mjData.qpos[25]),float(p.mjData.qvel[24]),p.Kp_gripper,p.Kd_gripper,allowed)
            except ValueError:self.extension.lease.trip('GRIPPER_FORCE_REFERENCE_INVALID')
        # The upstream loop computed this same PD force before the step hook.
        p.mjData.ctrl[18]=np.clip(p.mjData.ctrl[18],-self.gripper_effort,self.gripper_effort)

    def after(self,p,state,q,v):
        self.measured=q[19:25].copy()
        if self.limits is None:
            self.limits=np.array([p.mjModel.jnt_range[p.mjModel.joint(j).id] for j in JOINTS])
        active=self.active
        if active is None or active['done']:return
        sim_s=state['stamp_ns']/1e9
        if time.monotonic()-active['wall_start']>240.:
            active['stop_request']='wall_deadline'
        if active['kind']=='arm':
            desired=self.command.copy();error=float(np.max(abs(q[19:25]-desired)))
            self.feedback=dict(handle=active['handle'],desired=desired.tolist(),actual=q[19:25].tolist(),
                               velocity=v[18:24].tolist(),elapsed=sim_s-active['start'])
            if len(self.rows)==0 or sim_s-self.rows[-1]['sim_s']>=.019:
                self.rows.append(dict(sim_s=sim_s,q=q[19:25].tolist(),qd=v[18:24].tolist(),
                                      target=desired.tolist(),error=error,
                                      servo_reference=self.servo_command.tolist(),
                                      force=p.mjData.actuator_force[12:19].tolist(),stopping=active['stopping']))
            if error>.10:active['stop_request']='tracking_error'
            path=active['path']
            ended=path is None or sim_s-active['start']>=path.duration
            good=ended and error<=.05 and np.max(abs(v[18:24]))<=.05
            if good:
                if active['settle_since'] is None:active['settle_since']=(sim_s,time.monotonic())
                ready=sim_s-active['settle_since'][0]>=.5 and time.monotonic()-active['settle_since'][1]>=1.
                if ready:
                    terminal='canceled' if active['stop_request']=='cancel' else ('aborted' if active['stop_request'] else 'succeeded')
                    self.finish(terminal,active['stop_request'] or 'measured_goal_hold')
            else:active['settle_since']=None
            if ended and path is not None and sim_s-active['start']>path.duration+5.:
                active['stop_request']='goal_hold_timeout'
        else:
            position,velocity,effort=float(q[25]),float(v[24]),float(p.mjData.actuator_force[18])
            reached=abs(position-self.gripper_command)<=.002
            stalled=gripper_stalled(position,self.gripper_command,velocity,effort)
            if reached and abs(velocity)<=.01 or stalled:
                if active['settle_since'] is None:active['settle_since']=sim_s
                if sim_s-active['settle_since']>=.5:
                    terminal='canceled' if active['stop_request']=='cancel' else ('aborted' if active['stop_request'] else 'succeeded')
                    self.finish(terminal,active['stop_request'] or 'measured_gripper',position=position,
                                effort=effort,reached=reached,stalled=stalled)
            else:active['settle_since']=None
            if sim_s-active['start']>8. and not active['stopping']:active['stop_request']='gripper_timeout'

    @timed_callback('action.monitor')
    def monitor(self):
        for action in (ARM,GRIPPER):
            if self.node.count_publishers(action+'/_action/status')>1:
                with self.node.lock:self.extension.lease.trip('DUPLICATE_ACTION_SERVER')
        with self.node.lock:feedback=self.feedback;self.feedback=None
        if feedback is not None and feedback['handle'].is_active:
            value=FollowJointTrajectory.Feedback();value.joint_names=list(JOINTS)
            value.desired.positions=feedback['desired'];value.actual.positions=feedback['actual']
            value.actual.velocities=feedback['velocity']
            value.error.positions=[a-b for a,b in zip(feedback['desired'],feedback['actual'])]
            feedback['handle'].publish_feedback(value)

    def close(self):
        self.validation_worker.shutdown(wait=True,cancel_futures=True)
        if self.active is not None and not self.active['done']:
            if self.active['kind']=='arm':self.finish('aborted','engine_closed')
            else:self.finish('aborted','engine_closed',position=0.,effort=0.,reached=False,stalled=False)
        self.arm_server.destroy();self.gripper_server.destroy()
