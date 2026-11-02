"""Offline native collision checks and conservative interval geometry.

No runtime scene is stepped or modified. Original description assets remain
read-only; navigation MJCF is a new in-memory variant with URDF hip mounts.
"""
import hashlib
import itertools
import math
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
import yaml


def description_dir():
    local = Path(__file__).resolve().parents[2] / 'integrated_robot_description'
    if local.is_dir():
        return local
    from ament_index_python.packages import get_package_share_directory
    return Path(get_package_share_directory('integrated_robot_description'))


def navigation_mjcf(model):
    source = description_dir() / 'mujoco/robot_system.xml'
    tree = ET.fromstring(source.read_text())
    urdf = ET.fromstring(model.urdf)
    for prefix in ('fr', 'fl', 'rr', 'rl'):
        joint = urdf.find(f"joint[@name='{prefix}_hip_joint']")
        body = tree.find(f".//body[@name='{prefix}_hip_link']")
        body.set('pos', joint.find('origin').get('xyz'))
    # This candidate is specific to the combined navigation model. Legacy
    # description gains are untouched; native G1/G2 validation is still required.
    gains_file = Path(__file__).resolve().parents[1]/'config/mujoco_navigation_actuators.yaml'
    if not gains_file.is_file():
        from ament_index_python.packages import get_package_share_directory
        gains_file = Path(get_package_share_directory('integrated_robot_navigation'))/'config/mujoco_navigation_actuators.yaml'
    gains = yaml.safe_load(gains_file.read_text())
    expected = {'hip', 'thigh', 'calf'} | (set(model.limits)-set(model.joint_names))
    if not isinstance(gains, dict) or set(gains) != expected:
        raise ValueError('navigation actuator gain schema')
    for values in gains.values():
        if (not isinstance(values, dict) or set(values) != {'kp', 'kv'}
                or any(type(value) not in (int, float) or not math.isfinite(value) or value <= 0
                       for value in values.values())):
            raise ValueError('positive finite navigation actuator gains required')
    for name in model.limits:
        actuator = tree.find(f"actuator/position[@joint='{name}']")
        if actuator is None:
            raise ValueError('navigation position actuator missing: '+name)
        group = name.split('_')[1] if name in model.joint_names else name
        for key, value in gains[group].items():
            actuator.set(key, str(float(value)))
    return ET.tostring(tree, encoding='unicode')


def physics_digest(mjcf):
    source, contract = ET.fromstring(mjcf), ET.Element('physics')
    for name in ('compiler', 'option', 'default', 'actuator'):
        element = source.find(name)
        if element is not None:
            contract.append(element)
    contract.append(source.find("worldbody/body[@name='base_link']"))
    contract.append(source.find("worldbody/geom[@name='ground']"))
    return hashlib.sha256(ET.tostring(contract)).hexdigest()


def native_geometry(model, arm_q):
    """Return exact native geom frames; do not omit nonadjacent self pairs."""
    import mujoco
    urdf = ET.fromstring(model.urdf)
    extension = ET.SubElement(urdf, 'mujoco')
    ET.SubElement(extension, 'compiler', fusestatic='false', discardvisual='true')
    native_xml = navigation_mjcf(model)
    xml_models = (ET.tostring(urdf, encoding='unicode'), native_xml)
    records, statistics = [], []
    for xml in xml_models:
        native = mujoco.MjModel.from_xml_string(xml)
        data = mujoco.MjData(native)
        if native.nkey:
            mujoco.mj_resetDataKeyframe(native, data, 0)
        for prefix in ('fr', 'fl', 'rr', 'rl'):
            for part, q in zip(('hip', 'thigh', 'calf'), (0., -.5, 1.)):
                data.qpos[native.joint(prefix+'_'+part+'_joint').qposadr[0]] = q
        for i, q in enumerate(arm_q, 1):
            data.qpos[native.joint('arm_joint_'+str(i)).qposadr[0]] = q
        for name in ('gripper_left_joint', 'gripper_right_joint'):
            data.qpos[native.joint(name).qposadr[0]] = .015
        mujoco.mj_forward(native, data)
        checked = 0
        for i, j in itertools.combinations(range(native.ngeom), 2):
            if (native.geom_type[i] == mujoco.mjtGeom.mjGEOM_PLANE
                    or native.geom_type[j] == mujoco.mjtGeom.mjGEOM_PLANE):
                continue
            a, b = (int(native.body_weldid[native.geom_bodyid[g]]) for g in (i, j))
            pa, pb = (int(native.body_weldid[native.body_parentid[w]]) for w in (a, b))
            if a == b or a == pb or b == pa:
                continue  # welded assembly or immediate articulated neighbour only
            checked += 1
            distance = mujoco.mj_geomDistance(native, data, i, j, .01, None)
            if not math.isfinite(distance) or distance < .0001:
                links = [native.body(int(native.geom_bodyid[g])).name for g in (i, j)]
                raise ValueError(f'self collision: {links}, distance={distance}')
        statistics.append(dict(geom_count=native.ngeom, checked_pairs=checked))
        for i in range(native.ngeom):
            kind, size = native.geom_type[i], native.geom_size[i]
            if kind == mujoco.mjtGeom.mjGEOM_PLANE:
                continue
            if kind == mujoco.mjtGeom.mjGEOM_BOX:
                extent = size.copy()
            elif kind == mujoco.mjtGeom.mjGEOM_SPHERE:
                extent = np.full(3, size[0])
            elif kind == mujoco.mjtGeom.mjGEOM_CYLINDER:
                extent = np.array([size[0], size[0], size[1]])
            elif kind == mujoco.mjtGeom.mjGEOM_CAPSULE:
                extent = np.array([size[0], size[0], size[1]+size[0]])
            else:
                raise ValueError('unsupported collision primitive')
            local = np.eye(4)
            # The 3x3 view is non-contiguous: convert into an explicit 9-vector.
            rotation = np.empty(9)
            mujoco.mju_quat2Mat(rotation, native.geom_quat[i])
            local[:3, :3], local[:3, 3] = rotation.reshape(3, 3), native.geom_pos[i]
            link = native.body(int(native.geom_bodyid[i])).name
            records.append((link, local, extent))
    return records, statistics, physics_digest(native_xml)


def trig_bounds(kind, lo, hi):
    if kind not in ('sin', 'cos') or not all(math.isfinite(v) for v in (lo, hi)) or lo > hi:
        raise ValueError('finite ordered trig interval required')
    function = math.sin if kind == 'sin' else math.cos
    phase = math.pi/2 if kind == 'sin' else 0.
    values = [function(lo), function(hi)]
    if hi-lo >= math.tau:
        return -1., 1.
    for k in range(math.ceil((lo-phase)/math.pi), math.floor((hi-phase)/math.pi)+1):
        values.append(function(phase + k*math.pi))
    # Include endpoint argument/libm rounding (cos(pi/2) is not exactly zero).
    error = 8 * math.ulp(1.)
    return (math.nextafter(max(-1., min(values)-error), -math.inf),
            math.nextafter(min(1., max(values)+error), math.inf))


def interval_product(a, b):
    alo, ahi = a
    blo, bhi = b
    products = np.stack((alo[..., :, :, None]*blo[..., None, :, :],
                         alo[..., :, :, None]*bhi[..., None, :, :],
                         ahi[..., :, :, None]*blo[..., None, :, :],
                         ahi[..., :, :, None]*bhi[..., None, :, :]))
    return (np.nextafter(products.min(axis=0).sum(axis=-2), -np.inf),
            np.nextafter(products.max(axis=0).sum(axis=-2), np.inf))


def rotation_interval(axis, lo, hi):
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    skew = np.array([[0., -z, y], [z, 0., -x], [-y, x, 0.]])
    squared = skew @ skew
    sinlo, sinhi = trig_bounds('sin', lo, hi)
    coslo, coshi = trig_bounds('cos', lo, hi)
    lower, upper = np.eye(4), np.eye(4)
    for i in range(3):
        for j in range(3):
            terms = ((skew[i, j]*sinlo, skew[i, j]*sinhi),
                     (squared[i, j]*(1-coshi), squared[i, j]*(1-coslo)))
            lower[i, j] += sum(min(term) for term in terms)
            upper[i, j] += sum(max(term) for term in terms)
    return np.nextafter(lower, -np.inf), np.nextafter(upper, np.inf)


def footprint_bounds(model, arm_q, limits, records):
    arm = dict(zip(('arm_joint_'+str(i) for i in range(1, 7)), arm_q))
    bounds = {}
    for name, (lo, hi, _, _) in model.limits.items():
        if name in model.joint_names:
            part = name.split('_')[1]
            bounds[name] = tuple(limits['gait_joint_bounds'][part])
        elif name in arm:
            tolerance = limits['carry_error_rad']
            bounds[name] = (max(lo, arm[name]-tolerance), min(hi, arm[name]+tolerance))
        else:
            bounds[name] = (lo, hi)  # full allowed gripper travel
        if not lo <= bounds[name][0] <= bounds[name][1] <= hi:
            raise ValueError('gait bounds outside physical joint limits')
    angle = limits['max_roll_pitch']
    inverse_base = np.linalg.inv(model.chains['base_link'].forward({}))
    transforms = {}
    for link, chain in model.chains.items():
        # Partition whole intervals, not isolated poses. Their closed union covers
        # every allowed value while limiting repeated-variable overestimation.
        partitions = {}
        for name, axis, lo, hi, kind in (
                ('__roll', (1, 0, 0), -angle, angle, 'revolute'),
                ('__pitch', (0, 1, 0), -angle, angle, 'revolute'),
                *((name, axis, *bounds[name], kind)
                  for name, kind, _, axis, _, _, _ in chain.compiled if kind != 'fixed')):
            pieces = 1 if kind == 'prismatic' else max(1, math.ceil((hi-lo)/.10))
            edges = np.linspace(lo, hi, pieces+1)
            choices = []
            for left, right in zip(edges[:-1], edges[1:]):
                if kind == 'prismatic':
                    low, high = np.eye(4), np.eye(4)
                    low[:3, 3] = np.minimum(axis*left, axis*right)
                    high[:3, 3] = np.maximum(axis*left, axis*right)
                    choices.append((low, high))
                else:
                    choices.append(rotation_interval(axis, left, right))
            partitions[name] = choices
        sizes = tuple(len(v) for v in partitions.values())
        if math.prod(sizes) > 100_000:
            raise ValueError('swept bound partition budget exceeded')
        indices = np.indices(sizes).reshape(len(sizes), -1)
        selected = {}
        for row, (name, choices) in enumerate(partitions.items()):
            selected[name] = (np.stack([v[0] for v in choices])[indices[row]],
                              np.stack([v[1] for v in choices])[indices[row]])
        current = interval_product(selected['__pitch'], selected['__roll'])
        current = interval_product(current, (inverse_base, inverse_base))
        for name, kind, origin, axis, _, _, _ in chain.compiled:
            current = interval_product(current, (origin, origin))
            if kind == 'fixed':
                continue
            current = interval_product(current, selected[name])
        transforms[link] = current
    minimum, maximum = np.full(2, np.inf), np.full(2, -np.inf)
    for link, local, extent in records:
        transform = interval_product(transforms[link], (local, local))
        for signs in itertools.product((-1., 1.), repeat=3):
            vertex = np.array([*(extent*np.array(signs)), 1.]).reshape(4, 1)
            low, high = interval_product(transform, (vertex, vertex))
            minimum = np.minimum(minimum, low[..., :2, 0].min(axis=0))
            maximum = np.maximum(maximum, high[..., :2, 0].max(axis=0))
    margin = limits['footprint_margin_m']
    minimum, maximum = minimum-margin, maximum+margin
    return tuple((float(x), float(y), 0.) for x, y in (
        (minimum[0], minimum[1]), (maximum[0], minimum[1]),
        (maximum[0], maximum[1]), (minimum[0], maximum[1])))
