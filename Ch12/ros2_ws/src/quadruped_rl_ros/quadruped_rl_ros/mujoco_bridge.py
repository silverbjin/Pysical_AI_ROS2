"""Wall-clock-driven MuJoCo plant for the chapter's ROS 2 policy controller.

Targets are absolute joint angles in radians. MuJoCo's position actuators run
their bounded PD servos at every 2 ms physics step, independently of ROS traffic.
Falling never resets the plant, so controller/watchdog failures remain visible.
"""
import json
import math
import time

import mujoco
import numpy as np
import rclpy
from builtin_interfaces.msg import Time
from nav_msgs.msg import Odometry
from rclpy.clock import Clock as RclClock, ClockType
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, JointState
from std_msgs.msg import Bool, String

from quadruped_rl.locomotion_env import QuadrupedLocomotionEnv


def ordered_targets(message, joint_names, limits):
    """Validate the entire named command atomically, then return model order."""
    if (len(message.name) != len(joint_names)
            or len(message.position) != len(joint_names)
            or len(set(message.name)) != len(joint_names)
            or set(message.name) != set(joint_names)):
        raise ValueError('Target must contain each of the 12 canonical joints once')
    by_name = dict(zip(message.name, message.position))
    targets = np.asarray([by_name[name] for name in joint_names], dtype=np.float64)
    if not np.isfinite(targets).all():
        raise ValueError('Joint targets must be finite')
    if np.any(targets < limits[:, 0]) or np.any(targets > limits[:, 1]):
        raise ValueError('Joint target exceeds model joint limits')
    return targets


def simulation_stamp(seconds):
    nanoseconds = int(round(float(seconds) * 1_000_000_000))
    return Time(sec=nanoseconds // 1_000_000_000,
                nanosec=nanoseconds % 1_000_000_000)


class MujocoBridge(Node):
    """Publish simulator truth and accept named position targets at 50 Hz."""

    def __init__(self):
        super().__init__('mujoco_bridge')
        # Publishing /clock must never make the physics timer depend on /clock.
        self.set_parameters([Parameter('use_sim_time', value=False)])
        self.declare_parameter('render', False)
        self.declare_parameter('seed', 0)
        self.declare_parameter('target_timeout', 0.25)
        self.target_timeout = float(self.get_parameter('target_timeout').value)
        if not math.isfinite(self.target_timeout) or self.target_timeout <= 0:
            raise ValueError('target_timeout must be finite and positive')
        self.env = QuadrupedLocomotionEnv(
            command=[0., 0., 0.], max_episode_steps=2**31-1,
            render_mode='human' if self.get_parameter('render').value else None)
        self.env.reset(seed=int(self.get_parameter('seed').value))
        self.targets = self.env.nominal_joint_positions.copy()
        self.env.data.ctrl[self.env._actuator_ids] = self.targets
        self.command_count = 0
        self.bad_commands = 0
        self.last_command_wall = time.monotonic()
        self.last_target_stamp = -np.inf
        self.paused = False
        self.failed = False
        self._closed = False
        self._timeout_warned = False
        self._warnings = (mujoco.mjtWarning.mjWARN_BADQPOS,
                          mujoco.mjtWarning.mjWARN_BADQVEL,
                          mujoco.mjtWarning.mjWARN_BADQACC)
        self.clock_pub = self.create_publisher(Clock, '/clock', 10)
        self.imu_pub = self.create_publisher(Imu, '/imu/data_raw', qos_profile_sensor_data)
        self.joint_pub = self.create_publisher(JointState, '/joint_states', qos_profile_sensor_data)
        self.odom_pub = self.create_publisher(Odometry, '/simulation/odom', qos_profile_sensor_data)
        self.status_pub = self.create_publisher(String, '/rl/simulator_status', 10)
        self.target_sub = self.create_subscription(
            JointState, '/rl/joint_targets', self._on_targets, 10)
        self.pause_sub = self.create_subscription(Bool, '/rl/pause', self._on_pause, 10)
        self._wall_clock = RclClock(clock_type=ClockType.STEADY_TIME)
        self.timer = self.create_timer(.02, self._tick, clock=self._wall_clock)

    def _on_targets(self, message):
        try:
            stamp=message.header.stamp.sec+message.header.stamp.nanosec*1e-9
            age=self.env.data.time-stamp
            if age>self.target_timeout or age<-.04 or stamp<self.last_target_stamp-1e-9:
                raise ValueError('Stale, future or out-of-order target timestamp')
            targets = ordered_targets(message, self.env.joint_names, self.env._joint_limits)
        except (ValueError, TypeError) as exc:
            self.bad_commands += 1
            self.get_logger().warning(f'Rejected joint target: {exc}')
            return
        self.targets = targets
        self.last_target_stamp = stamp
        self.last_command_wall = time.monotonic()
        self.command_count += 1
        self._timeout_warned = False

    def _on_pause(self, message):
        self.paused = bool(message.data)

    def _tick(self):
        stale = time.monotonic() - self.last_command_wall > self.target_timeout
        if stale and not self._timeout_warned:
            self.get_logger().warning('Joint target timeout: holding last accepted position target')
            self._timeout_warned = True
        if not self.paused and not self.failed:
            try:
                self._integrate()
            except (FloatingPointError, mujoco.FatalError) as exc:
                self.failed = True
                self.timer.cancel()
                self._publish_status(stale, error=str(exc))
                self.get_logger().fatal(f'MuJoCo integration stopped: {exc}')
                raise
            self._publish_state()
            if self.env.render_mode == 'human':
                self.env.render()
        self._publish_status(stale)

    def _integrate(self):
        model, data = self.env.model, self.env.data
        before = [data.warning[i].number for i in self._warnings]
        self.env._ensure_finite_state()
        for _ in range(10):
            data.ctrl[self.env._actuator_ids] = self.targets
            mujoco.mj_step(model, data)
            self.env._ensure_finite_state()
            if (not np.isfinite(data.qacc).all()
                    or any(data.warning[i].number > n for i, n in zip(self._warnings, before))):
                raise FloatingPointError('MuJoCo reported numerical instability')
        mujoco.mj_forward(model, data)
        self.env._ensure_finite_state()

    def _publish_state(self):
        env, data = self.env, self.env.data
        stamp = simulation_stamp(data.time)
        clock = Clock()
        clock.clock = stamp
        self.clock_pub.publish(clock)
        imu = Imu()
        imu.header.stamp, imu.header.frame_id = stamp, 'base_link'
        w, x, y, z = map(float, data.qpos[3:7])
        imu.orientation.w, imu.orientation.x = w, x
        imu.orientation.y, imu.orientation.z = y, z
        omega = env.get_base_angular_velocity()
        imu.angular_velocity.x, imu.angular_velocity.y, imu.angular_velocity.z = map(float, omega)
        rotation = data.xmat[env._base_id].reshape(3, 3)
        proper_acceleration = rotation.T @ (data.qacc[:3] - env.model.opt.gravity)
        (imu.linear_acceleration.x, imu.linear_acceleration.y,
         imu.linear_acceleration.z) = map(float, proper_acceleration)
        self.imu_pub.publish(imu)
        joints = JointState()
        joints.header.stamp, joints.header.frame_id = stamp, 'base_link'
        joints.name = list(env.joint_names)
        joints.position = data.qpos[env._qpos_ids].tolist()
        joints.velocity = data.qvel[env._qvel_ids].tolist()
        joints.effort = data.actuator_force[env._actuator_ids].tolist()
        self.joint_pub.publish(joints)
        odom = Odometry()
        odom.header.stamp, odom.header.frame_id = stamp, 'odom'
        odom.child_frame_id = 'base_link'
        odom.pose.pose.orientation = imu.orientation
        (odom.pose.pose.position.x, odom.pose.pose.position.y,
         odom.pose.pose.position.z) = map(float, data.qpos[:3])
        (odom.twist.twist.linear.x, odom.twist.twist.linear.y,
         odom.twist.twist.linear.z) = map(float, env.get_base_linear_velocity())
        odom.twist.twist.angular = imu.angular_velocity
        self.odom_pub.publish(odom)

    def _publish_status(self, stale, error=None):
        rotation = self.env.data.xmat[self.env._base_id].reshape(3, 3)
        status = dict(sim_time=float(self.env.data.time), height=float(self.env.data.qpos[2]),
                      tilt=math.acos(float(np.clip(rotation[2, 2], -1, 1))),
                      command_count=self.command_count, bad_commands=self.bad_commands,
                      target_stale=bool(stale), paused=self.paused, failed=self.failed)
        if error is not None:
            status['error'] = error
        self.status_pub.publish(String(data=json.dumps(status)))

    def destroy_node(self):
        if not self._closed:
            self._closed = True
            self.timer.cancel()
            self.env.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = None
    try:
        node = MujocoBridge()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        if node is not None:
            node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
