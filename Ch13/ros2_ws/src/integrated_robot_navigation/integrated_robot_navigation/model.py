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


def initial_leg_targets(model: ModelContract) -> dict[str, float]:
    """Cold hardware hold only, never an estimate from loaded encoders."""
    tree = ET.fromstring(model.urdf)
    controls = tree.findall('ros2_control')
    result = {}
    if len(controls) != 1:
        raise ValueError('one initial leg command source required')
    for joint in controls[0].findall('joint'):
        name = joint.get('name')
        if name not in model.joint_names:
            continue
        initial = joint.findall("state_interface[@name='position']/param[@name='initial_value']")
        interfaces = joint.findall('command_interface')
        try:
            value = float(initial[0].text) if len(initial) == 1 else float('nan')
        except (TypeError, ValueError):
            value = float('nan')
        if (name in result or not math.isfinite(value)
                or not model.limits[name][0] <= value <= model.limits[name][1]
                or len(interfaces) != 1 or interfaces[0].get('name') != 'position'):
            raise ValueError('invalid initial leg command: '+name)
        result[name] = value
    if set(result) != set(model.joint_names):
        raise ValueError('missing initial leg command')
    return result


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
