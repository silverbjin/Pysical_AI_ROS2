"""Name-based URDF forward kinematics; no simulator or ROS import."""
import math
import xml.etree.ElementTree as ET

import numpy as np

from .contracts import finite


def rotation(axis, angle):
    axis = np.asarray(axis, dtype=float)
    if axis.shape != (3,) or not np.isfinite(axis).all() or np.linalg.norm(axis) < 1e-12:
        raise ValueError('finite nonzero joint axis required')
    x, y, z = axis / np.linalg.norm(axis)
    skew = np.array([[0, -z, y], [z, 0, -x], [-y, x, 0]])
    return np.eye(3) + math.sin(angle)*skew + (1-math.cos(angle))*(skew @ skew)


def origin_matrix(origin):
    transform = np.eye(4)
    if origin is None:
        return transform
    xyz = [float(v) for v in origin.get('xyz', '0 0 0').split()]
    rpy = [float(v) for v in origin.get('rpy', '0 0 0').split()]
    if len(xyz) != 3 or len(rpy) != 3:
        raise ValueError('three origin coordinates required')
    finite(*xyz, *rpy)
    transform[:3, 3] = xyz
    r, p, y = rpy
    transform[:3, :3] = rotation([0, 0, 1], y) @ rotation([0, 1, 0], p) @ rotation([1, 0, 0], r)
    return transform


class KinematicChain:
    def __init__(self, joints):
        self.joints = joints
        self.joint_names = tuple(j.get('name') for j in joints if j.get('type') != 'fixed')
        self.compiled = []
        for joint in joints:
            name, kind = joint.get('name'), joint.get('type')
            origin = origin_matrix(joint.find('origin'))
            if kind == 'fixed':
                self.compiled.append((name, kind, origin, None, None, None, None))
                continue
            tag = joint.find('axis')
            axis = np.array([float(v) for v in (tag.get('xyz') if tag is not None else '1 0 0').split()])
            if axis.shape != (3,) or not np.isfinite(axis).all() or np.linalg.norm(axis) < 1e-12:
                raise ValueError('finite nonzero joint axis required')
            axis /= np.linalg.norm(axis)
            x,y,z = axis
            skew = np.array([[0.,-z,y],[z,0.,-x],[-y,x,0.]])
            limit = joint.find('limit')
            if kind != 'continuous' and limit is None:
                raise ValueError('joint limits required')
            bounds = None if kind == 'continuous' else (float(limit.get('lower')),float(limit.get('upper')))
            self.compiled.append((name,kind,origin,axis,skew,skew @ skew,bounds))
        self.compiled = tuple(self.compiled)

    @classmethod
    def from_urdf(cls, xml_text: str, root: str = 'base_link',
                  tip: str = 'camera_optical_frame'):
        tree = ET.fromstring(xml_text)
        links = [v.get('name') for v in tree.findall('link')]
        if root not in links or tip not in links or len(links) != len(set(links)):
            raise ValueError('unique links and connected endpoints required')
        parents, names = {}, set()
        for joint in tree.findall('joint'):
            name, kind = joint.get('name'), joint.get('type')
            child, parent = joint.find('child'), joint.find('parent')
            if (not name or name in names or child is None or parent is None
                    or kind not in ('fixed', 'revolute', 'continuous', 'prismatic')
                    or child.get('link') in parents):
                raise ValueError('invalid/duplicate joint or multiple parents')
            names.add(name)
            parents[child.get('link')] = joint
        path, visited, current = [], set(), tip
        while current != root:
            if current in visited or current not in parents:
                raise ValueError('disconnected/cyclic kinematic chain')
            visited.add(current)
            joint = parents[current]
            path.append(joint)
            current = joint.find('parent').get('link')
        return cls(tuple(reversed(path)))

    def forward(self, positions: dict[str, float]) -> np.ndarray:
        return self._evaluate(positions, collect_axes=False)[0]

    def camera_kinematics(self, positions):
        """One compiled FK pass, plus base-frame joint screws at that same pose."""
        return self._evaluate(positions, collect_axes=True)

    def _evaluate(self, positions, *, collect_axes):
        if not all(name in positions for name in self.joint_names):
            raise ValueError('missing named joint position')
        transform = np.eye(4)
        axes = {}
        for name,kind,origin,axis,skew,squared,bounds in self.compiled:
            transform = transform @ origin
            if kind == 'fixed':
                continue
            value = positions[name]
            finite(value)
            if bounds is not None and not bounds[0] <= value <= bounds[1]:
                raise ValueError('joint position outside limits')
            if collect_axes:
                axes[name] = (transform[:3,:3] @ axis, transform[:3,3].copy(), kind)
            change = np.eye(4)
            if kind == 'prismatic':
                change[:3, 3] = axis * value
            else:
                change[:3,:3] += math.sin(value)*skew + (1-math.cos(value))*squared
            transform = transform @ change
        return transform, axes
