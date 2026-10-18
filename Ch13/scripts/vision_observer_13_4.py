"""Read-only real ROS observer; never sends motor commands or synthetic sensor data."""
from collections import Counter, OrderedDict, deque
import json
from pathlib import Path
import time
import xml.etree.ElementTree as ET

from action_msgs.msg import GoalStatusArray
from control_msgs.msg import JointTrajectoryControllerState
import cv2
from cv_bridge import CvBridge
from geometry_msgs.msg import PointStamped
from integrated_robot_interfaces.msg import TrackedTarget
from integrated_robot_runtime.policy import ARM_NAMES, LEG_NAMES, STAND, joint_snapshot, safe_arm
from integrated_robot_vision.cache import RGBDCache, nanoseconds
from integrated_robot_vision.contracts import Box2D
from integrated_robot_vision.geometry import decode_depth, deproject, sample_depth
import numpy as np
from rclpy.duration import Duration
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import DurabilityPolicy, QoSProfile, qos_profile_sensor_data
from rclpy.time import Time
from rosidl_runtime_py.convert import message_to_ordereddict
from sensor_msgs.msg import CameraInfo, Image, JointState
from std_msgs.msg import String
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformException, TransformListener
from vision_msgs.msg import Detection2DArray

from verify_vision_13_4 import visible_surface_point


def matrix(transform):
    t, q = transform.transform.translation, transform.transform.rotation
    x, y, z, w = q.x, q.y, q.z, q.w
    if not np.isfinite([t.x, t.y, t.z, x, y, z, w]).all() or abs(x*x+y*y+z*z+w*w-1.) > 1e-5:
        raise ValueError('finite normalized capture transform required')
    result = np.eye(4)
    result[:3, :3] = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
                      [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
                      [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    result[:3, 3] = [t.x, t.y, t.z]
    return result


class VisionObserver(Node):
    def __init__(self, output):
        super().__init__('section_13_4_observer', parameter_overrides=[Parameter('use_sim_time', value=True)])
        self.output = Path(output)
        self.cache, self.bridge = RGBDCache(), CvBridge()
        self.buffer = Buffer(node=self)
        self.listener = TransformListener(self.buffer, self)
        self.counts, self.invalid = Counter(), Counter()
        self.boxes, self.pending = OrderedDict(), deque(maxlen=64)
        self.latest_images, self.startup, self.tracking, self.legs = {}, {}, {}, {}
        self.samples, self.detections, self.tracks, self.states, self.actions = [], [], [], [], []
        self.joints, self.references = [], []
        self.joint_velocities, self.calibrations = [], {}
        self.commands = []
        self.tf_owners, self.tf_parents, self.model_parents = {}, {}, {}
        self.tf_metadata_fields = set()
        self.collecting, self.saved_frame = False, False
        qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.subs = [
            self.create_subscription(Image, '/camera/color/image_raw', self.on_rgb, qos_profile_sensor_data),
            self.create_subscription(Image, '/camera/aligned_depth_to_color/image_raw', self.on_depth,
                                     qos_profile_sensor_data),
            self.create_subscription(CameraInfo, '/camera/color/camera_info', self.on_info, qos_profile_sensor_data),
            self.create_subscription(Detection2DArray, '/vision/detections', self.on_detections, qos_profile_sensor_data),
            self.create_subscription(PointStamped, '/vision/target_raw', self.on_raw, 50),
            self.create_subscription(TrackedTarget, '/vision/tracked_target', self.on_track, 50),
            self.create_subscription(JointState, '/joint_states', self.on_joints, 50),
            self.create_subscription(String, '/architecture/startup', self.on_startup, qos),
            self.create_subscription(String, '/robot_description', self.on_model, qos),
            self.create_subscription(String, '/architecture/visual_tracking', self.on_tracking, 50),
            self.create_subscription(String, '/architecture/arm_command', self.on_command, 50),
            self.create_subscription(String, '/architecture/locomotion', self.on_legs, 10),
            self.create_subscription(String, '/vision/status', self.on_status, 50),
            self.create_subscription(String, '/vision/detector_status', self.on_status, 50),
            self.create_subscription(GoalStatusArray,
                '/arm_trajectory_controller/follow_joint_trajectory/_action/status', self.on_actions, qos),
            self.create_subscription(JointTrajectoryControllerState,
                '/arm_trajectory_controller/controller_state', self.on_reference, 50),
            self.create_subscription(TFMessage, '/tf', self.on_tf, 100),
            self.create_subscription(TFMessage, '/tf_static', self.on_tf, qos)]

    def on_rgb(self, message):
        self.counts['rgb'] += 1
        self.latest_images['rgb'] = message
        try:
            self.cache.add_rgb(message, 0)
        except ValueError:
            self.invalid['rgb_contract'] += 1

    def on_depth(self, message):
        self.counts['depth'] += 1
        self.latest_images['depth'] = message
        try:
            self.cache.add_depth(message, 0)
        except ValueError:
            self.invalid['depth_contract'] += 1

    def on_info(self, message):
        self.counts['info'] += 1
        self.latest_images['info'] = message
        try:
            self.cache.add_info(message, 0)
            self.calibrations[message.header.stamp.sec+message.header.stamp.nanosec/1e9] = message_to_ordereddict(message)
            while len(self.calibrations) > 20:
                del self.calibrations[next(iter(self.calibrations))]
        except ValueError:
            self.invalid['calibration_contract'] += 1

    def on_detections(self, message):
        self.counts['detection_frames'] += 1
        key = nanoseconds(message.header.stamp)
        boxes = []
        for detection in message.detections:
            if detection.results:
                best = max(detection.results, key=lambda v: v.hypothesis.score).hypothesis
                box = detection.bbox
                boxes.append(Box2D(box.center.position.x, box.center.position.y, box.size_x,
                                   box.size_y, best.class_id, best.score))
        self.boxes[key] = boxes
        while len(self.boxes) > 100:
            self.boxes.popitem(last=False)
        if self.collecting:
            self.detections.append(dict(wall=time.monotonic(), capture_ns=key,
                boxes=[dict(cx=v.cx, cy=v.cy, width=v.width, height=v.height,
                            class_id=v.class_id, score=v.score) for v in boxes]))

    def on_raw(self, message):
        self.counts['raw_targets'] += 1
        if self.collecting:
            self.pending.append(message)

    def on_track(self, message):
        self.counts['valid_tracks' if message.valid else 'invalid_tracks'] += 1
        if self.collecting:
            self.tracks.append(dict(wall=time.monotonic(), capture_ns=nanoseconds(message.header.stamp),
                valid=message.valid, status=message.status, track_id=message.track_id,
                class_id=message.class_id, score=message.score))

    def on_joints(self, message):
        arm = joint_snapshot(message.name, message.position, ARM_NAMES)
        legs = joint_snapshot(message.name, message.position, LEG_NAMES)
        if arm is not None and legs is not None:
            self.joints.append((nanoseconds(message.header.stamp), time.monotonic(), arm, legs))
            self.joint_velocities.append(joint_snapshot(message.name, message.velocity, ARM_NAMES))
            if len(self.joints) > 20000:
                del self.joints[:1000]
                del self.joint_velocities[:1000]

    def on_reference(self, message):
        point = getattr(message, 'reference', None)
        if point is None:
            point = getattr(message, 'desired', None)
        if point is not None:
            positions = joint_snapshot(message.joint_names, point.positions, ARM_NAMES)
            velocities = joint_snapshot(message.joint_names, point.velocities, ARM_NAMES)
            if positions is not None:
                self.references.append((nanoseconds(message.header.stamp), time.monotonic(), positions, velocities))

    def on_startup(self, message):
        self.startup = json.loads(message.data)

    def on_model(self, message):
        tree = ET.fromstring(message.data)
        parents = {}
        for joint in tree.findall('joint'):
            child, parent = joint.find('child').get('link'), joint.find('parent').get('link')
            if child in parents or child == 'base_footprint':
                raise ValueError('model root/child ownership conflict')
            parents[child] = parent
        parents['base_footprint'] = 'odom'  # only Ch13 native adapter source owns this edge
        self.model_parents = parents

    def on_tracking(self, message):
        self.tracking = json.loads(message.data)
        self.states.append(dict(wall=time.monotonic(), **self.tracking))

    def on_command(self, message):
        self.commands.append(dict(received_wall=time.monotonic(), **json.loads(message.data)))

    def on_legs(self, message):
        self.legs = json.loads(message.data)

    def on_status(self, message):
        self.invalid[json.loads(message.data).get('status', 'unknown')] += 1

    def on_actions(self, message):
        for value in message.status_list:
            self.actions.append(dict(wall=time.monotonic(), uuid=bytes(value.goal_info.goal_id.uuid).hex(),
                                     status=value.status, created_ns=nanoseconds(value.goal_info.stamp)))

    def on_tf(self, message, info):
        gid = info.get('publisher_gid') if isinstance(info, dict) else getattr(info, 'publisher_gid', None)
        if isinstance(info, dict):
            self.tf_metadata_fields.update(info)
        if gid is None and not (isinstance(info, dict) and
                {'source_timestamp', 'received_timestamp'} <= set(info)):
            raise ValueError('unrecognized TF metadata; cannot verify source contract')
        for value in message.transforms:
            self.tf_parents.setdefault(value.child_frame_id, set()).add(value.header.frame_id)
            if gid is not None:
                self.tf_owners.setdefault(value.child_frame_id, set()).add(bytes(gid).hex())

    def standing(self):
        if not self.joints:
            return False
        stamp, received, arm, legs = self.joints[-1]
        return (safe_arm(arm, time.monotonic()-received)
                and 0 <= time.monotonic()-received <= .3
                and 0 <= self.get_clock().now().nanoseconds-stamp <= .3e9
                and all(abs(a-b) <= .15 for a, b in zip(legs, STAND))
                and self.legs.get('active') is True and self.legs.get('ready') is True)

    def process_samples(self, *, fixture_y=0.):
        for _ in range(len(self.pending)):
            message = self.pending.popleft()
            key = nanoseconds(message.header.stamp)
            boxes = self.boxes.get(key)
            if boxes is None:
                if self.get_clock().now().nanoseconds-key <= .5e9:
                    self.pending.append(message)  # observer callback arrival can be reordered
                else:
                    self.invalid['observer_detection_missing'] += 1
                continue
            if len(boxes) != 1 or boxes[0].class_id != 'fixture_red':
                self.invalid['ground_truth_requires_one_fixture_detection'] += 1
                continue
            bundle = self.cache.match(message.header.stamp, 'camera_optical_frame', 0)
            if bundle is None:
                self.invalid['observer_rgbd_pair_missing'] += 1
                continue
            try:
                capture = matrix(self.buffer.lookup_transform('odom', 'camera_optical_frame',
                    Time.from_msg(message.header.stamp), timeout=Duration(seconds=0.)))
                box, k = boxes[0], bundle.intrinsics
                truth = visible_surface_point(box.cx, box.cy, (k.fx, k.fy, k.cx, k.cy), capture,
                                              fixture_y=fixture_y)
                if truth is None:
                    self.invalid['ray_outside_declared_front_surface'] += 1
                    continue
                observed = np.array([message.point.x, message.point.y, message.point.z])
                if message.header.frame_id != 'odom' or not np.isfinite(observed).all():
                    raise ValueError('raw point frame/numbers invalid')
                depth = bundle.depth
                array = decode_depth(bytes(depth.data), depth.encoding, depth.width, depth.height,
                                     depth.step, bool(depth.is_bigendian))
                d, _ = sample_depth(array, box)
                optical = deproject(box.cx, box.cy, d, k)
                latest = matrix(self.buffer.lookup_transform('odom', 'camera_optical_frame', Time(),
                                                              timeout=Duration(seconds=0.)))
                current_point = latest[:3, :3] @ optical + latest[:3, 3]
                self.samples.append(dict(capture_ns=key, wall=time.monotonic(), measured=observed.tolist(),
                    truth=truth.tolist(), error=(observed-truth).tolist(),
                    latest_tf_error=(current_point-truth).tolist(), pixel=[box.cx, box.cy],
                    pixel_error=float(np.hypot(box.cx-k.cx, box.cy-k.cy)),
                    capture_optical_pose=capture.tolist(),
                    arrival_age_s=(self.get_clock().now().nanoseconds-key)*1e-9))
                if not self.saved_frame:
                    self.save_frame(bundle, box)
            except TransformException:
                self.invalid['observer_tf_not_yet_available'] += 1
            except ValueError:
                self.invalid['observer_invalid_sample'] += 1

    def save_latest_frame(self):
        for image, _ in reversed(list(self.cache.rgb.values())):
            bundle = self.cache.match(image.header.stamp, image.header.frame_id, 0)
            if bundle is not None:
                self.save_frame(bundle, None, empty_label='No published inference result')
                return True
        return False

    def save_frame(self, bundle, box, *, empty_label='No detections'):
        rgb = self.bridge.imgmsg_to_cv2(bundle.rgb, 'bgr8')
        if not cv2.imwrite(str(self.output/'rgb.png'), rgb):
            raise RuntimeError('RGB artifact write failed')
        annotated = rgb.copy()
        if box is not None:
            a = (round(box.cx-box.width/2), round(box.cy-box.height/2))
            b = (round(box.cx+box.width/2), round(box.cy+box.height/2))
            cv2.rectangle(annotated, a, b, (0, 255, 0), 1)
        else:
            cv2.putText(annotated, empty_label, (10, 20), cv2.FONT_HERSHEY_SIMPLEX,
                        .4, (255, 255, 255), 1)
        if not cv2.imwrite(str(self.output/'annotated.png'), annotated):
            raise RuntimeError('annotated artifact write failed')
        image = bundle.depth
        np.save(self.output/'depth.npy', decode_depth(bytes(image.data), image.encoding,
            image.width, image.height, image.step, bool(image.is_bigendian)), allow_pickle=False)
        k = bundle.intrinsics
        (self.output/'camera.json').write_text(json.dumps(dict(
            capture_ns=nanoseconds(bundle.rgb.header.stamp), depth_ns=nanoseconds(bundle.depth.header.stamp),
            frame=k.frame_id, width=k.width, height=k.height, fx=k.fx, fy=k.fy, cx=k.cx, cy=k.cy,
            calibration_id=k.calibration_id, depth_encoding=image.encoding,
            camera_info=self.calibrations.get(bundle.info_stamp)), indent=2)+'\n', encoding='utf-8')
        self.saved_frame = True

    def save(self):
        payload = dict(counts=dict(self.counts), invalid=dict(self.invalid), samples=self.samples,
                       detections=self.detections, tracks=self.tracks, tracking=self.states,
                       actions=self.actions, commands=self.commands, references=self.references,
                       tf_owners={k: sorted(v) for k, v in self.tf_owners.items()},
                       tf_parents={k: sorted(v) for k, v in self.tf_parents.items()},
                       model_parents=self.model_parents, tf_metadata_fields=sorted(self.tf_metadata_fields),
                       tf_ownership_method=('graph+model-parent-contract inference; no per-message GID'
                                            if not self.tf_owners else 'observed message GIDs + graph'))
        (self.output/'observations.json').write_text(json.dumps(payload, separators=(',', ':'))+'\n',
                                                   encoding='utf-8')
        np.savez_compressed(self.output/'joints.npz',
            stamps_ns=np.array([v[0] for v in self.joints], dtype=np.int64),
            received_wall=np.array([v[1] for v in self.joints]),
            arm=np.array([v[2] for v in self.joints]), legs=np.array([v[3] for v in self.joints]),
            arm_velocity=np.array([v if v is not None else [np.nan]*6 for v in self.joint_velocities]))
        return payload
