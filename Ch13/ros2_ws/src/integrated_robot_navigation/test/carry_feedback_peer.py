"""Independent, hand-defined DDS test feedback; never native physics evidence."""
import multiprocessing
import time
import traceback


def _publish(model_hash, positions, values, enabled, stopping, ready, phase, result):
    phase.value = 1
    import rclpy
    from rclpy.context import Context
    from rclpy.node import Node
    from rclpy.time import Time
    from rosgraph_msgs.msg import Clock
    from sensor_msgs.msg import JointState
    from std_msgs.msg import Header
    from integrated_robot_interfaces.msg import MotionState

    phase.value = 2

    ctx, node, spans = Context(), None, []
    error = None
    try:
        rclpy.init(context=ctx)
        phase.value = 3
        node = Node('carry_feedback_peer', context=ctx)
        phase.value = 4
        joints = node.create_publisher(JointState, '/joint_states', 10)
        crawl = node.create_publisher(MotionState, '/navigation/crawl_state', 10)
        guard = node.create_publisher(MotionState, '/navigation/guard_state', 10)
        clock = node.create_publisher(Clock, '/clock', 10)
        names = list(positions)
        origin = time.monotonic_ns()
        phase.value = 5
        ready.set()
        while not stopping.is_set():
            begin, cpu_begin = time.monotonic_ns(), time.thread_time_ns()
            if enabled.is_set():
                with values.get_lock():
                    generation, stand, velocity, arm_error, gripper_error, gripper_velocity = values[:]
                # This communication fixture models the engine's simulation
                # clock, independently of host SYSTEM/NTP corrections. Each new
                # capture and /clock share one monotonic-paced source; no old
                # message is retagged and no wall watchdog is bypassed.
                stamp = Time(nanoseconds=1_000_000_000+time.monotonic_ns()-origin).to_msg()
                clock.publish(Clock(clock=stamp))
                q = [(.015+gripper_error) if name.startswith('gripper_') else
                     positions[name]+(arm_error if name == 'arm_joint_2' else 0.) for name in names]
                qd = [gripper_velocity if name.startswith('gripper_') else velocity for name in names]
                joints.publish(JointState(header=Header(stamp=stamp), name=names, position=q, velocity=qd))
                for publisher in (crawl, guard):
                    msg = MotionState(generation=int(generation), model_sha256=model_hash,
                                      state='STAND', ready=bool(stand), stopped=bool(stand))
                    msg.header.stamp, msg.header.frame_id = stamp, 'base_link'
                    publisher.publish(msg)
            published = time.monotonic_ns()
            # CPython3.12 multiprocessing.Event uses a realtime semaphore
            # deadline. Local comparison measured 305ms for a requested20ms
            # while sleep/thread-event stayed below22ms. Pace this independent
            # fixture on monotonic sleep; poll the same stop flag next loop.
            # No catch-up, retagging, watchdog relaxation or product change.
            time.sleep(.02)
            spans.append(dict(begin_ns=begin, published_ns=published, end_ns=time.monotonic_ns(),
                              cpu_ns=time.thread_time_ns()-cpu_begin, enabled=enabled.is_set(),
                              source_system_ns=time.time_ns(),
                              capture_ns=stamp.sec*1_000_000_000+stamp.nanosec))
    except BaseException:
        error = traceback.format_exc()
    finally:
        if node is not None:
            node.destroy_node()
        ctx.try_shutdown()
        result.send(dict(error=error, publish_spans=spans))
        result.close()


class CarryFeedbackPeer:
    def __init__(self, model_hash, positions):
        context = multiprocessing.get_context('spawn')
        self.values = context.Array('d', [0., 1., 0., 0., 0., 0.])
        self.enabled, self.stopping, ready = (context.Event() for _ in range(3))
        phase = context.Value('i', 0)
        self.startup_trace = []
        self.enabled.set()
        self.result, sender = context.Pipe(duplex=False)
        self.process = context.Process(target=_publish, args=(model_hash, positions, self.values,
            self.enabled, self.stopping, ready, phase, sender), name='carry-feedback-peer')
        started = time.monotonic()
        self.process.start()
        sender.close()
        # This is interpreter/DDS process startup, not a sensor freshness limit.
        # Keep phase evidence instead of interpreting import delay as input loss.
        while not ready.is_set() and self.process.is_alive() and time.monotonic()-started < 15.:
            current = phase.value
            if not self.startup_trace or self.startup_trace[-1]['phase'] != current:
                self.startup_trace.append(dict(phase=current, elapsed_s=time.monotonic()-started))
            ready.wait(.05)
        self.startup_trace.append(dict(phase=phase.value, elapsed_s=time.monotonic()-started))
        if not ready.is_set():
            self.close()
            raise AssertionError('independent DDS feedback failed to start: '+str(self.startup_trace))

    def update(self, generation, stand, velocity, arm_error, gripper_error, gripper_velocity):
        with self.values.get_lock():
            self.values[:] = [generation, stand, velocity, arm_error, gripper_error, gripper_velocity]

    def close(self):
        self.stopping.set()
        assert self.result.poll(5.), 'feedback child did not report normal resource cleanup'
        report = self.result.recv()  # drain before join; trace can exceed the pipe buffer
        self.process.join(3.)
        assert not self.process.is_alive() and self.process.exitcode == 0, 'feedback child not reaped normally'
        self.result.close()
        assert not report['error'], report['error']
        return report['publish_spans']
