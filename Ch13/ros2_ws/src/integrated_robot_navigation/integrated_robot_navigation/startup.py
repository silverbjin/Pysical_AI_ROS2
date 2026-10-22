"""One-shot, nonblocking measured STAND -> actual carry startup, never CRAWL."""
import time

from rclpy.node import Node
from rclpy.clock import Clock
from rclpy.clock_type import ClockType
from lifecycle_msgs.msg import Transition
from lifecycle_msgs.srv import ChangeState
from std_srvs.srv import Trigger
from integrated_robot_interfaces.msg import MotionState
from integrated_robot_interfaces.srv import SetMode

from .samples import Sample, sample_valid


class StartupManager(Node):
    def __init__(self, **kwargs):
        super().__init__('crawl_startup', **kwargs)
        self.state, self.fault = 'WAIT_GUARD', ''
        self.generation, self.model = None, ''
        self.messages = dict.fromkeys(('guard', 'crawl', 'carry'))
        self.future = None
        self.deadline = time.monotonic()+45.
        self.mode = self.create_client(SetMode, '/navigation/set_mode')
        self.lifecycle = self.create_client(ChangeState, '/crawl_controller/change_state')
        self.prepare = self.create_client(Trigger, '/carry_manager/prepare')
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
            raise ValueError('startup service rejected: '+self.state)
        return True

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
                            and crawl['phase'] == 'BOOTSTRAP_FEEDBACK_READY'):
                        self._transition(Transition.TRANSITION_ACTIVATE, 'ACTIVATING')
                elif self.state == 'ACTIVATING' and self._result('success'):
                    self.state = 'WAIT_STAND'
                elif self.state == 'WAIT_STAND':
                    crawl = self._fresh('crawl')
                    if (guard and guard['state'] == 'STAND' and crawl and crawl['ready']
                            and crawl['stopped'] and crawl['state'] in ('STAND', 'STOPPED')
                            and self.prepare.service_is_ready()):
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
