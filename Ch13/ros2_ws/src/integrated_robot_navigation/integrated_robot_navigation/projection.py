"""A measured planar projection is a new frame, never a replacement for 6D TF."""
from copy import deepcopy
from dataclasses import replace
import math
import time

import numpy as np
from .dispatch_node import NavigationNode as Node
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

from .samples import Sample


def body_rotation(data):
    x, y, z, w = data['orientation']
    if (not all(math.isfinite(v) for v in (x, y, z, w))
            or abs(x*x+y*y+z*z+w*w-1.) > 1e-6):
        raise ValueError('invalid measured body quaternion')
    rotation = np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
    roll = math.atan2(rotation[2, 1], rotation[2, 2])
    pitch = math.asin(float(np.clip(-rotation[2, 0], -1., 1.)))
    yaw = math.atan2(rotation[1, 0], rotation[0, 0])
    return rotation, (roll, pitch, yaw)


def project_body(sample: Sample) -> Sample:
    try:
        data = deepcopy(sample.data)
        if (sample.frame_id != 'odom' or data['child_frame_id'] != 'base_footprint'
                or any(len(data[key]) != size or not all(math.isfinite(v) for v in data[key])
                       for key, size in (('position', 3), ('orientation', 4),
                                         ('linear_velocity', 3), ('angular_velocity', 3)))):
            raise ValueError('invalid native body frame/data')
        rotation, (roll, pitch, yaw) = body_rotation(data)
        if abs(math.cos(pitch)) < 1e-6:
            raise ValueError('singular planar heading')
        c, s = math.cos(yaw), math.sin(yaw)
        planar_inverse = np.array([[c, s, 0.], [-s, c, 0.], [0., 0., 1.]])
        velocity = planar_inverse @ rotation @ np.asarray(data['linear_velocity'])
        # yaw is a projected heading, not simply world angular-velocity.z.
        _, wy, wz = data['angular_velocity']
        yaw_rate = (math.sin(roll)*wy+math.cos(roll)*wz)/math.cos(pitch)
        data.update(position=(*data['position'][:2], 0.),
                    orientation=(0., 0., math.sin(yaw/2), math.cos(yaw/2)),
                    linear_velocity=(float(velocity[0]), float(velocity[1]), 0.),
                    angular_velocity=(0., 0., yaw_rate), child_frame_id='nav_base')
        return replace(sample, data=data)
    except (KeyError, TypeError, IndexError) as error:
        raise ValueError('invalid native body schema') from error


def body_data(message):
    p, q, v, w = (message.pose.pose.position, message.pose.pose.orientation,
                   message.twist.twist.linear, message.twist.twist.angular)
    return dict(position=(p.x, p.y, p.z), orientation=(q.x, q.y, q.z, q.w),
                linear_velocity=(v.x, v.y, v.z), angular_velocity=(w.x, w.y, w.z),
                child_frame_id=message.child_frame_id)


class NavProjection(Node):
    def __init__(self, **kwargs):
        super().__init__('nav_projection', **kwargs)
        self.pub = self.create_publisher(Odometry, '/navigation/odom', 10)
        self.tf = TransformBroadcaster(self)
        self.create_subscription(Odometry, '/odom', self.receive, 10)

    def receive(self, message):
        stamp = message.header.stamp.sec*1_000_000_000+message.header.stamp.nanosec
        if stamp <= 0:
            return
        try:
            sample = project_body(Sample(stamp, time.monotonic_ns(), 0, stamp,
                                          message.header.frame_id, body_data(message)))
        except ValueError as error:
            self.get_logger().warning(str(error))
            return
        msg = Odometry()
        msg.header = deepcopy(message.header)
        msg.child_frame_id = 'nav_base'
        msg.pose.pose.position.x, msg.pose.pose.position.y, msg.pose.pose.position.z = sample.data['position']
        q = sample.data['orientation']
        msg.pose.pose.orientation.x, msg.pose.pose.orientation.y = q[:2]
        msg.pose.pose.orientation.z, msg.pose.pose.orientation.w = q[2:]
        v, w = sample.data['linear_velocity'], sample.data['angular_velocity']
        msg.twist.twist.linear.x, msg.twist.twist.linear.y, msg.twist.twist.linear.z = v
        msg.twist.twist.angular.x, msg.twist.twist.angular.y, msg.twist.twist.angular.z = w
        # Native-ground-truth benchmark only, not an estimator covariance.
        for index in (14, 21, 28):
            msg.pose.covariance[index] = 1e6
            msg.twist.covariance[index] = 1e6
        transform = TransformStamped()
        transform.header = deepcopy(msg.header)
        transform.child_frame_id = msg.child_frame_id
        transform.transform.translation.x, transform.transform.translation.y = sample.data['position'][:2]
        transform.transform.rotation = deepcopy(msg.pose.pose.orientation)
        self.tf.sendTransform(transform)
        self.pub.publish(msg)


def main(args=None):
    from .dispatch_node import run_navigation_node
    run_navigation_node(NavProjection, args=args)
