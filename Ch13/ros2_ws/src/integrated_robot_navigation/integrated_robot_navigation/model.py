"""Compile the actual URDF once; no simulator or earlier chapter imports."""
from dataclasses import dataclass
import hashlib
import math
import xml.etree.ElementTree as ET

from integrated_robot_vision.kinematics import KinematicChain, origin_matrix


@dataclass(frozen=True)
class ModelContract:
    model_sha256: str
    joint_names: tuple[str, ...]
    feet: tuple[str, ...]
    chains: dict
    masses: dict
    limits: dict
    root: str
    urdf: str


def compile_model(urdf: str) -> ModelContract:
    tree = ET.fromstring(urdf)
    links = [element.get('name') for element in tree.findall('link')]
    if not links or any(not name for name in links) or len(set(links)) != len(links):
        raise ValueError('unique named links required')
    parents, names, limits = {}, set(), {}
    for joint in tree.findall('joint'):
        name = joint.get('name')
        parent, child = joint.find('parent'), joint.find('child')
        if (not name or name in names or parent is None or child is None
                or parent.get('link') not in links or child.get('link') not in links
                or child.get('link') in parents):
            raise ValueError('invalid joint names or topology')
        names.add(name)
        parents[child.get('link')] = parent.get('link')
        if joint.get('type') != 'fixed':
            tag = joint.find('limit')
            if tag is None:
                raise ValueError('bounded joint limits required')
            bounds = tuple(float(tag.get(key, 'nan')) for key in
                           ('lower', 'upper', 'velocity', 'effort'))
            if (not all(math.isfinite(v) for v in bounds)
                    or bounds[0] >= bounds[1] or min(bounds[2:]) <= 0):
                raise ValueError('invalid joint limits')
            limits[name] = bounds
    roots = set(links) - set(parents)
    if len(roots) != 1:
        raise ValueError('one connected root required')
    root = roots.pop()
    chains = {link: KinematicChain.from_urdf(urdf, root=root, tip=link) for link in links}
    feet = tuple(prefix + '_foot' for prefix in ('fr', 'fl', 'rr', 'rl'))
    joint_names = tuple(prefix + '_' + part + '_joint' for prefix in
                        ('fr', 'fl', 'rr', 'rl') for part in ('hip', 'thigh', 'calf'))
    if any(foot not in chains for foot in feet) or any(j not in limits for j in joint_names):
        raise ValueError('missing quadruped foot or joint')
    masses = {}
    for link in tree.findall('link'):
        inertial = link.find('inertial')
        if inertial is None:
            continue
        tag = inertial.find('mass')
        mass = float(tag.get('value', 'nan')) if tag is not None else float('nan')
        if not math.isfinite(mass) or mass <= 0:
            raise ValueError('positive finite mass required')
        masses[link.get('name')] = (mass, tuple(origin_matrix(inertial.find('origin'))[:3, 3]))
    return ModelContract(hashlib.sha256(urdf.encode()).hexdigest(), joint_names, feet,
                         chains, masses, limits, root, urdf)
