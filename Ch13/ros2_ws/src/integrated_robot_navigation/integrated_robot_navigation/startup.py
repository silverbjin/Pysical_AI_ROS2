"""One-shot, nonblocking measured STAND -> actual carry startup, never CRAWL."""
import time
from pathlib import Path

from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from std_srvs.srv import Trigger
from controller_manager_msgs.srv import ListControllers
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_interfaces.srv import SetMode

from .samples import Sample, sample_valid
from .model import compile_model


class StartupManager(Node):
    def __init__(self, **kwargs):
        super().__init__('crawl_startup', **kwargs)
        try:
            clock_mode = self.declare_parameter('control_clock_mode', 'native').value
            validation = self.declare_parameter('validation_mode', False).value
            if clock_mode not in ('native', 'relay100') or (clock_mode == 'relay100' and not validation):
                raise ValueError('control_clock_mode experiment requires validation_mode')
            self.clock_mode, self.clock_armed = clock_mode, False
            model_file = self.declare_parameter('model_file', '').value
            self.contract = compile_model(Path(model_file).read_text())
            arms = tuple('arm_joint_'+str(i) for i in range(1, 7))
            gripper = ('gripper_left_joint', 'gripper_right_joint')
            if set(self.contract.limits) != set(self.contract.joint_names+arms+gripper):
                raise ValueError('startup interface model partition')
            self.expected_claims = {name: {joint+'/position' for joint in joints}
                for name, joints in (
                    ('leg_position_controller', self.contract.joint_names),
                    ('arm_trajectory_controller', arms), ('gripper_position_controller', gripper),
                    ('joint_state_broadcaster', ()))}
        except Exception:
            super().destroy_node()
            raise
        self.state, self.fault = 'WAIT_GUARD', ''
        self.generation, self.model = None, ''
        self.messages = dict.fromkeys(('guard', 'crawl', 'carry'))
        self.future = None
        self.controller_future = None
        self.deadline = time.monotonic()+45.
        self.mode = self.create_client(SetMode, '/navigation/set_mode')
        self.lifecycle = self.create_client(ChangeState, '/crawl_controller/change_state')
        self.prepare = self.create_client(Trigger, '/carry_manager/prepare')
        self.controllers = self.create_client(ListControllers, '/controller_manager/list_controllers')
        self.clock_arm = self.create_client(Trigger, '/navigation_control_clock/arm') if clock_mode == 'relay100' else None
        self.status = self.create_publisher(MotionState, '/navigation/startup_state', 10)
        for key in self.messages:
            self.create_subscription(MotionState, '/navigation/'+key+'_state',
                                     lambda msg, stream=key: self._receive(stream, msg), 10)
        self.create_timer(.05, self._tick, clock=Clock(clock_type=ClockType.STEADY_TIME))

    def _receive(self, key, msg):
        stamp = msg.header.stamp.sec*1_000_000_000+msg.header.stamp.nanosec
        previous = self.messages[key]
        if previous is None or stamp > previous.stamp_ns:
            self.messages[key] = Sample(stamp, time.monotonic_ns(), 0, stamp, msg.header.frame_id,
                dict(state=msg.state, ready=msg.ready, stopped=msg.stopped, generation=msg.generation,
                     model_sha256=msg.model_sha256, fault=msg.fault_reason, phase=msg.phase))

    def _fresh(self, key):
        sample = self.messages[key]
        ok, _ = sample_valid(sample, self.get_clock().now().nanoseconds, time.monotonic_ns(),
                             0, max_age_ns=200_000_000)
        if not ok:
            return None
        value = sample.data
        if value['fault']:
            raise ValueError(key+':'+value['fault'])
        if (key == 'crawl' and self.state == 'WAIT_FEEDBACK' and not value['model_sha256']
                and value['state'] == 'INACTIVE' and value['phase'] == 'BOOTSTRAP_WAIT_FEEDBACK'
                and not value['ready'] and not value['stopped']):
            # A service configure ACK can overtake the previous unconfigured
            # status in DDS. This is absence of readiness, never authority.
            return None
        if value['model_sha256'] != self.contract.model_sha256:
            raise ValueError(key+':startup scene model mismatch')
        if self.generation is not None and (value['generation'] != self.generation
                                           or value['model_sha256'] != self.model):
            raise ValueError(key+':startup generation/model changed')
        return value

    def _transition(self, identifier, state):
        self.future = self.lifecycle.call_async(ChangeState.Request(transition=Transition(id=identifier)))
        self.state = state

    def _result(self, attribute):
        if not self.future.done():
            return False
        value = self.future.result()
        if value is None or not getattr(value, attribute):
            reason = getattr(value, 'message', 'no response') if value is not None else 'no response'
            raise ValueError('startup service rejected: '+self.state+': '+reason)
        return True

    def _controllers_ready(self):
        # One read-only request at a time; never retry a rejected motor command.
        if self.controller_future is None:
            if self.controllers.service_is_ready():
                self.controller_future = self.controllers.call_async(ListControllers.Request())
            return False
        if not self.controller_future.done():
            return False
        result, self.controller_future = self.controller_future.result(), None
        if result is None:
            raise ValueError('controller interface response missing')
        names, owners = {}, {}
        for controller in result.controller:
            if not controller.name or controller.name in names:
                raise ValueError('duplicate controller interface owner name')
            names[controller.name] = controller
            claims = controller.claimed_interfaces
            if len(claims) != len(set(claims)):
                raise ValueError('duplicate command interface claim')
            for claim in claims:
                if claim in owners:
                    raise ValueError('duplicate command interface owner: '+claim)
                owners[claim] = controller.name
                if (claim.split('/')[0] in self.contract.limits
                        and claim not in self.expected_claims.get(controller.name, set())):
                    raise ValueError('foreign command interface owner: '+claim)
        ready = True
        for name, expected in self.expected_claims.items():
            controller = names.get(name)
            if controller is None or controller.state != 'active':
                ready = False
            elif set(controller.claimed_interfaces) != expected:
                raise ValueError('active controller interface claims mismatch: '+name)
        return ready

    def _tick(self):
        try:
            if self.fault:
                pass
            elif self.state != 'READY' and time.monotonic() > self.deadline:
                raise ValueError('startup wall deadline; no automatic retry')
            else:
                guard = self._fresh('guard')
                if self.state == 'WAIT_GUARD':
                    if guard and self.mode.service_is_ready():
                        self.generation, self.model = guard['generation'], guard['model_sha256']
                        self.future = self.mode.call_async(SetMode.Request(mode='STAND'))
                        self.state = 'MODE_REQUESTED'
                elif self.state == 'MODE_REQUESTED' and self._result('accepted'):
                    self.state = 'WAIT_STAND_GATE'
                elif self.state == 'WAIT_STAND_GATE':
                    if guard and guard['state'] == 'STAND' and self.lifecycle.service_is_ready():
                        self._transition(Transition.TRANSITION_CONFIGURE, 'CONFIGURING')
                elif self.state == 'CONFIGURING' and self._result('success'):
                    self.state = 'WAIT_FEEDBACK'
                elif self.state == 'WAIT_FEEDBACK':
                    crawl = self._fresh('crawl')
                    if (guard and guard['state'] == 'STAND' and crawl
                            and crawl['state'] == 'INACTIVE'
                            and crawl['phase'] == 'BOOTSTRAP_FEEDBACK_READY'
                            and self._controllers_ready()):
                        if self.clock_arm is not None and not self.clock_armed:
                            if self.clock_arm.service_is_ready():
                                self.future = self.clock_arm.call_async(Trigger.Request())
                                self.state = 'ARMING_CLOCK'
                        else:
                            self._transition(Transition.TRANSITION_ACTIVATE, 'ACTIVATING')
                elif self.state == 'ARMING_CLOCK' and self._result('success'):
                    self.clock_armed = True
                    self.state = 'WAIT_FEEDBACK'  # recheck fresh sensors/claims before activation
                elif self.state == 'ACTIVATING' and self._result('success'):
                    self.state = 'WAIT_STAND'
                elif self.state == 'WAIT_STAND':
                    crawl = self._fresh('crawl')
                    if (guard and guard['state'] == 'STAND' and crawl and crawl['ready']
                            and crawl['stopped'] and crawl['state'] in ('STAND', 'STOPPED')
                            and self.prepare.service_is_ready() and self._controllers_ready()):
                        self.future = self.prepare.call_async(Trigger.Request())
                        self.state = 'CARRY_REQUESTED'
                elif self.state == 'CARRY_REQUESTED' and self._result('success'):
                    self.state = 'WAIT_CARRY'
                elif self.state == 'WAIT_CARRY':
                    carry = self._fresh('carry')
                    if guard and carry and carry['ready']:
                        self.state = 'READY'
                elif self.state == 'READY':
                    # This records startup completion, not current permission to
                    # move. The live guard/crawl/carry gates remain authoritative.
                    self._fresh('carry')
        except (ValueError, RuntimeError) as error:
            self.fault, self.state = str(error), 'FAULT'
        msg = MotionState(generation=self.generation or 0, model_sha256=self.model,
                          state=self.state, ready=self.state == 'READY' and not self.fault,
                          fault_reason=self.fault)
        msg.header.stamp, msg.header.frame_id = self.get_clock().now().to_msg(), 'base_link'
        self.status.publish(msg)


def main(args=None):
    from integrated_robot_vision.execution import run_node
    run_node(StartupManager, args=args)
