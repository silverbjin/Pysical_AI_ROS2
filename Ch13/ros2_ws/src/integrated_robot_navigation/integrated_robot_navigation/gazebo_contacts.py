"""Flat-ground load normalization from actual Gazebo post-step observations.

gz-physics ExtraContactData forces are world-frame vectors. ContactSensorData
may mirror a pair with a different collision1 order; support load uses |Fz|
ONLY for the explicitly mapped foot against the known flat ground. This is not
an arbitrary force norm, slope/contact planner, or a guessed foot collision name.
"""
import copy
from collections import deque
import math

from geometry_msgs.msg import Point, Vector3
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
        # Bounded boundary evidence only. No extra clock reads, disk writes,
        # worker or control input; snapshot serialization happens on request.
        self.counts = dict(contacts=0,feet=0)
        self.duplicates = dict(contacts=0,feet=0)
        self.expired = dict(contacts=0,feet=0)
        self.overflow = dict(contacts=0,feet=0)
        self.ignored = dict(contacts=0,feet=0)
        self.last_input = dict(contacts=None,feet=None)
        self.maximum_receipt_gap = dict(contacts=None,feet=None)
        self.last_pair = None
        self.delivery_trace=deque(maxlen=256)  # metadata only, existing receipt clocks

    def snapshot(self):
        return dict(scope='bounded_pair_delivery_diagnostic_not_motion_authority',
            stopped=self.stopped,outputs=self.sequence,last_output=self.last_output,observed_clock_ns=self.last_clock,
            **{key:dict(getattr(self,key)) for key in
               ('counts','duplicates','expired','overflow','ignored')},
            maximum_receipt_gap={key:None if value is None else dict(value)
                for key,value in self.maximum_receipt_gap.items()},
            last_pair=None if self.last_pair is None else dict(self.last_pair),
            delivery_trace=[dict(row) for row in self.delivery_trace],
            pending={key:[dict(stamp_ns=stamp,received_ns=cache[stamp][1]) for stamp in sorted(cache)]
                for key,cache in (('contacts',self.contacts),('feet',self.feet))})

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
        key='contacts' if cache is self.contacts else 'feet'
        self.counts[key]+=1
        self.delivery_trace.append(dict(event='input',stream=key,capture_ns=stamp,received_ns=received_ns))
        previous=self.last_input[key]
        if previous is not None:
            gap=received_ns-previous[1];maximum=self.maximum_receipt_gap[key]
            if maximum is None or gap>maximum['gap_ns']:
                self.maximum_receipt_gap[key]=dict(previous_stamp_ns=previous[0],stamp_ns=stamp,
                    previous_received_ns=previous[1],received_ns=received_ns,gap_ns=gap)
        self.last_input[key]=(stamp,received_ns)
        if self.stopped or stamp <= self.last_output or message.header.frame_id != 'odom':
            self.ignored[key]+=1
            return
        if stamp not in cache:
            cache[stamp] = copy.deepcopy(message), received_ns
        else:
            self.duplicates[key]+=1
        while len(cache) > 10:
            del cache[min(cache)]
            self.overflow[key]+=1

    def receive_contacts(self, message, received_ns):
        self._receive(self.contacts, message, received_ns)

    def receive_feet(self, message, received_ns):
        self._receive(self.feet, message, received_ns)

    def take(self, now_ros_ns, now_wall_ns):
        if self.stopped:
            return None
        for key,cache in (('contacts',self.contacts),('feet',self.feet)):
            for stamp, (_, receipt) in list(cache.items()):
                if stamp <= self.last_output or not (
                        now_ros_ns-stamp <= 200_000_000 and
                        0 <= now_wall_ns-receipt <= 200_000_000):
                    del cache[stamp]
                    if stamp>self.last_output:
                        self.expired[key]+=1
                        self.delivery_trace.append(dict(event='expired',stream=key,capture_ns=stamp,
                            received_ns=receipt,selected_ros_ns=now_ros_ns,selected_wall_ns=now_wall_ns,
                            ros_age_ns=now_ros_ns-stamp,wall_age_ns=now_wall_ns-receipt))
        common = {stamp for stamp in self.contacts.keys() & self.feet.keys() if stamp <= now_ros_ns}
        if not common:
            return None
        stamp = max(common)
        contacts, contact_receipt = self.contacts.pop(stamp)
        feet, feet_receipt = self.feet.pop(stamp)
        points = [(p.position.x, p.position.y, p.position.z) for p in feet.poses]
        result = normalize_contacts(contacts, points, self.mapping, self.ground,
                                    epoch=0, sequence=self.sequence+1)
        self.sequence += 1
        self.last_output = stamp
        self.last_pair=dict(capture_ns=stamp,contacts_received_ns=contact_receipt,
            feet_received_ns=feet_receipt,selected_wall_ns=now_wall_ns)
        self.delivery_trace.append(dict(event='paired',**self.last_pair))
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
    vectors = [[0.,0.,0.] for _ in FEET]
    vectors_valid = True
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
            force=a if names[0] in collision_map else b
            if force.z < -1e-6:
                vectors_valid=False
            for j,value in enumerate((force.x,force.y,force.z)):
                vectors[i][j]+=value
            totals[i] += load
            for j, value in enumerate((p.x, p.y, p.z)):
                positions[i][j] += load*value
    result.normal_forces = totals
    result.forces_world=[Vector3(x=v[0],y=v[1],z=v[2]) for v in vectors]
    result.force_vectors_valid=vectors_valid and all(
        abs(v[2]-normal)<=1e-6*(1.+normal) for v,normal in zip(vectors,totals))
    result.touching = [load >= 2. for load in totals]
    for i, load in enumerate(totals):
        if load:
            result.points[i] = Point(**dict(zip(('x', 'y', 'z'), (v/load for v in positions[i]))))
    return result


def main(args=None):
    """Thin ROS adapter; no TF or leg/arm command ownership."""
    import time
    import json
    import signal
    from threading import Event
    import rclpy
    from rclpy.executors import ExternalShutdownException
    from rclpy.signals import SignalHandlerOptions
    from .dispatch_node import NavigationNode as Node
    from rclpy.qos import qos_profile_sensor_data
    from geometry_msgs.msg import PoseArray
    from ros_gz_interfaces.msg import Contacts
    from rosgraph_msgs.msg import Clock
    from std_srvs.srv import Trigger
    from .scene import load_scene

    # Reuse Ch13 vision.execution's deferred SIGINT contract: a native event
    # callback finishes while its context is alive, then the owner joins the
    # executor before destroying ROS handles. Do not catch/ignore RuntimeError.
    rclpy.init(args=args,signal_handler_options=SignalHandlerOptions.NO)
    stopping=Event()
    previous=signal.signal(signal.SIGINT,lambda *_:stopping.set())
    node = None
    join = None
    executor = None
    try:
        node = Node('gazebo_contact_adapter')
        directory = node.declare_parameter('scene_dir', '').value
        record = load_scene('gazebo', directory)
        join = GazeboContactJoiner(record['foot_collision_map'], record['ground_collision'])
        pub = node.create_publisher(FootContacts, '/navigation/foot_contacts', qos_profile_sensor_data)

        def publish_ready(now_ros):
            try:
                result=join.take(now_ros,time.monotonic_ns())
                if result is not None:
                    started=time.monotonic_ns();pub.publish(result)
                    join.delivery_trace.append(dict(event='published',capture_ns=_stamp(result),
                        epoch=result.epoch,sequence=result.sequence,started_wall_ns=started,
                        returned_wall_ns=time.monotonic_ns(),scope='ROS_publish_return_not_subscriber_delivery'))
            except ValueError as error:
                join.stop()
                node.get_logger().error(f'native contact data rejected; restart required: {error}')

        def receive(message,info,method,stream):
            from .command_order import metadata_field
            entry=time.monotonic_ns();system=time.time_ns();now_ros=node.get_clock().now().nanoseconds
            method(message,entry)
            gid=metadata_field(info,'publisher_gid')
            join.delivery_trace.append(dict(event='DDS_callback',stream=stream,capture_ns=_stamp(message),epoch=0,
                callback_wall_ns=entry,callback_system_ns=system,selection_ros_ns=now_ros,
                source_system_ns=metadata_field(info,'source_timestamp'),
                rmw_received_system_ns=metadata_field(info,'received_timestamp'),
                publication_sequence=metadata_field(info,'publication_sequence_number'),
                publisher_gid=None if gid is None else bytes(gid).hex()))
            publish_ready(now_ros)

        def clock_received(message):
            now_ros=message.clock.sec*1_000_000_000+message.clock.nanosec
            join.observe_clock(now_ros)
            # The original clock callback releases eligible pending pairs.
            # No packet is restamped or used before its capture time.
            publish_ready(now_ros)

        node.create_subscription(Contacts, '/navigation/native_contacts',
            lambda msg,info: receive(msg,info,join.receive_contacts,'contacts'), qos_profile_sensor_data)
        node.create_subscription(PoseArray, '/navigation/native_feet',
            lambda msg,info: receive(msg,info,join.receive_feet,'feet'), qos_profile_sensor_data)
        node.create_subscription(Clock, '/clock', clock_received, qos_profile_sensor_data)

        def stop(_, response):
            join.stop()
            response.success = True
            response.message = 'contact adapter stopped; engine observer/exit must be confirmed separately'
            return response

        node.create_service(Trigger, '/navigation/stop_native_sensors', stop)
        def report(_, response):
            response.success=True
            response.message=json.dumps(join.snapshot(),separators=(',',':'))
            return response
        node.create_service(Trigger,'~/report',report)
        from .dispatch_node import make_navigation_executor
        executor=make_navigation_executor(node)
        executor.add_node(node)
        while rclpy.ok() and not stopping.is_set():
            executor.spin_once(timeout_sec=.1)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        signal.signal(signal.SIGINT,signal.SIG_IGN)
        try:
            if join is not None:
                join.stop()
            if executor is not None and not executor.shutdown(timeout_sec=2.):
                raise RuntimeError('contact executor not joined; ROS resources retained')
            if node is not None:
                node.destroy_node()
            rclpy.try_shutdown()
        finally:
            signal.signal(signal.SIGINT,previous)
