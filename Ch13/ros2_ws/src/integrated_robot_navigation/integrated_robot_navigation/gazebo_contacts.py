"""Flat-ground load normalization from actual Gazebo post-step observations.

gz-physics ExtraContactData forces are world-frame vectors. ContactSensorData
may mirror a pair with a different collision1 order; support load uses |Fz|
ONLY for the explicitly mapped foot against the known flat ground. This is not
an arbitrary force norm, slope/contact planner, or a guessed foot collision name.
"""
import copy
import math

from geometry_msgs.msg import Point
from integrated_robot_interfaces.msg import FootContacts

FEET = ('fr_foot', 'fl_foot', 'rr_foot', 'rl_foot')


def _stamp(message):
    return message.header.stamp.sec*1_000_000_000 + message.header.stamp.nanosec


class GazeboContactJoiner:
    """Bounded exact-capture join. Duplicate delivery cannot renew a receipt."""

    def __init__(self, collision_map, ground):
        self.mapping, self.ground = dict(collision_map), ground
        self.contacts, self.feet = {}, {}
        self.last_output = -1
        self.sequence = 0
        self.last_clock = None
        self.stopped = False

    def stop(self):
        self.stopped = True
        self.contacts.clear()
        self.feet.clear()

    def observe_clock(self, now_ros_ns):
        if self.last_clock is not None and now_ros_ns < self.last_clock:
            self.stop()
        self.last_clock = now_ros_ns

    def _receive(self, cache, message, received_ns):
        stamp = _stamp(message)
        if self.stopped or stamp <= self.last_output or message.header.frame_id != 'odom':
            return
        if stamp not in cache:
            cache[stamp] = copy.deepcopy(message), received_ns
        while len(cache) > 10:
            del cache[min(cache)]

    def receive_contacts(self, message, received_ns):
        self._receive(self.contacts, message, received_ns)

    def receive_feet(self, message, received_ns):
        self._receive(self.feet, message, received_ns)

    def take(self, now_ros_ns, now_wall_ns):
        if self.stopped:
            return None
        for cache in (self.contacts, self.feet):
            for stamp, (_, receipt) in list(cache.items()):
                if stamp <= self.last_output or not (
                        0 <= now_ros_ns-stamp <= 200_000_000 and
                        0 <= now_wall_ns-receipt <= 200_000_000):
                    del cache[stamp]
        common = self.contacts.keys() & self.feet.keys()
        if not common:
            return None
        stamp = max(common)
        contacts, _ = self.contacts.pop(stamp)
        feet, _ = self.feet.pop(stamp)
        points = [(p.position.x, p.position.y, p.position.z) for p in feet.poses]
        result = normalize_contacts(contacts, points, self.mapping, self.ground,
                                    epoch=0, sequence=self.sequence+1)
        self.sequence += 1
        self.last_output = stamp
        return result


def normalize_contacts(msg, foot_points, collision_map, ground, *, epoch, sequence):
    if (msg.header.frame_id != 'odom' or len(foot_points) != 4 or len(collision_map) != 4
            or set(collision_map.values()) != set(FEET)
            or epoch < 0 or sequence < 0):
        raise ValueError('invalid native contact frame/mapping/metadata')
    if any(len(p) != 3 or not all(math.isfinite(v) for v in p) for p in foot_points):
        raise ValueError('invalid native foot center')
    result = FootContacts(header=copy.deepcopy(msg.header), epoch=epoch, sequence=sequence)
    result.names = list(FEET)
    result.points = [Point(x=float(p[0]), y=float(p[1]), z=float(p[2])) for p in foot_points]
    totals = [0.]*4
    positions = [[0., 0., 0.] for _ in FEET]
    seen = set()
    for contact in msg.contacts:
        names = (contact.collision1.name, contact.collision2.name)
        key = tuple(sorted(names))
        if not all(names) or key in seen:
            raise ValueError('missing collision name or duplicate native pair')
        seen.add(key)
        if ground not in names or not any(n in collision_map for n in names):
            result.unexpected_contacts += 1
            continue
        foot = next(collision_map[n] for n in names if n in collision_map)
        i = FEET.index(foot)
        if not contact.positions or len(contact.positions) != len(contact.wrenches):
            raise ValueError('native engine has not provided contact force data')
        for p, wrench in zip(contact.positions, contact.wrenches):
            a, b = wrench.body_1_wrench.force, wrench.body_2_wrench.force
            values = (p.x, p.y, p.z, a.x, a.y, a.z, b.x, b.y, b.z)
            if not all(math.isfinite(v) for v in values) or any(
                    abs(u+v) > 1e-5*(1+abs(u)+abs(v))
                    for u, v in zip((a.x, a.y, a.z), (b.x, b.y, b.z))):
                raise ValueError('invalid native world contact wrench')
            load = abs(a.z)
            totals[i] += load
            for j, value in enumerate((p.x, p.y, p.z)):
                positions[i][j] += load*value
    result.normal_forces = totals
    result.touching = [load >= 2. for load in totals]
    for i, load in enumerate(totals):
        if load:
            result.points[i] = Point(**dict(zip(('x', 'y', 'z'), (v/load for v in positions[i]))))
    return result


def main(args=None):
    """Thin ROS adapter; no TF or leg/arm command ownership."""
    import time
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.node import Node
    from rclpy.qos import qos_profile_sensor_data
    from geometry_msgs.msg import PoseArray
    from ros_gz_interfaces.msg import Contacts
    from rosgraph_msgs.msg import Clock
    from std_srvs.srv import Trigger
    from .scene import load_scene

    rclpy.init(args=args)
    node = Node('gazebo_contact_adapter')
    join = None
    try:
        directory = node.declare_parameter('scene_dir', '').value
        record = load_scene('gazebo', directory)
        join = GazeboContactJoiner(record['foot_collision_map'], record['ground_collision'])
        pub = node.create_publisher(FootContacts, '/navigation/foot_contacts', qos_profile_sensor_data)

        def receive(message, method):
            method(message, time.monotonic_ns())
            try:
                result = join.take(node.get_clock().now().nanoseconds, time.monotonic_ns())
                if result is not None:
                    pub.publish(result)
            except ValueError as error:
                join.stop()
                node.get_logger().error(f'native contact data rejected; restart required: {error}')

        node.create_subscription(Contacts, '/navigation/native_contacts',
            lambda msg: receive(msg, join.receive_contacts), qos_profile_sensor_data)
        node.create_subscription(PoseArray, '/navigation/native_feet',
            lambda msg: receive(msg, join.receive_feet), qos_profile_sensor_data)
        node.create_subscription(Clock, '/clock', lambda msg:
            join.observe_clock(msg.clock.sec*1_000_000_000+msg.clock.nanosec), qos_profile_sensor_data)

        def stop(_, response):
            join.stop()
            response.success = True
            response.message = 'contact adapter stopped; engine observer/exit must be confirmed separately'
            return response

        node.create_service(Trigger, '/navigation/stop_native_sensors', stop)
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        if join is not None:
            join.stop()
        node.destroy_node()
        rclpy.try_shutdown()
