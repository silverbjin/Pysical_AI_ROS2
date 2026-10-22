"""New flat benchmark scenes; immutable originals, no synthetic robot motion.

Cup geometry adapted from Ch13/scripts/semantic_fixture_13_4.py at 8e07b05.
Fixed table is narrowed to a pedestal; all changes are real scene geometry.
"""
import hashlib
import json
import math
from pathlib import Path
import subprocess
import tempfile
import xml.etree.ElementTree as ET

import xacro
import yaml

from .geometry import description_dir, navigation_mjcf
from .model import compile_model


def _numbers(values):
    return ' '.join(str(float(v)) for v in values)


def cup_parts(x, y):
    parts = [dict(name='cup_bottom', kind='cylinder', pos=(x, y, .622),
                  size=(.11, .008), rgba=(.9, .9, .88, 1.)),
             dict(name='coffee', kind='cylinder', pos=(x, y, .798),
                  size=(.103, .002), rgba=(.08, .035, .01, 1.)),
             dict(name='table', kind='box', pos=(x, y, .3),
                  size=(.14, .18, .3), rgba=(.35, .3, .25, 1.))]
    for i in range(48):
        a = math.tau*i/48
        parts.append(dict(name=f'cup_wall_{i}', kind='box',
            pos=(x+.11*math.cos(a), y+.11*math.sin(a), .73),
            size=(.005, .008, .1), yaw=a, rgba=(.9, .9, .88, 1.)))
    for i in range(40):
        a = math.tau*i/40
        parts.append(dict(name=f'cup_handle_{i}', kind='sphere',
            pos=(x, y+.14+.065*math.cos(a), .73+.065*math.sin(a)),
            size=(.013,), rgba=(.9, .9, .88, 1.)))
    return parts


def _sdf_parts(world, parts):
    for part in parts:
        model = ET.SubElement(world, 'model', name=part['name'])
        ET.SubElement(model, 'static').text = 'true'
        link = ET.SubElement(model, 'link', name='link')
        for tag in ('visual', 'collision'):
            element = ET.SubElement(link, tag, name=part['name'])
            ET.SubElement(element, 'pose').text = _numbers((*part['pos'], 0, 0, part.get('yaw', 0)))
            shape = ET.SubElement(ET.SubElement(element, 'geometry'), part['kind'])
            if part['kind'] == 'box':
                ET.SubElement(shape, 'size').text = _numbers(2*v for v in part['size'])
            else:
                ET.SubElement(shape, 'radius').text = str(part['size'][0])
                if part['kind'] == 'cylinder':
                    ET.SubElement(shape, 'length').text = str(2*part['size'][1])
            if tag == 'visual':
                ET.SubElement(element, 'visibility_flags').text = '1'
                material = ET.SubElement(element, 'material')
                for key in ('ambient', 'diffuse'):
                    ET.SubElement(material, key).text = _numbers(part['rgba'])


def _map(output, boxes):
    resolution, side, origin = .05, 200, -5.
    pixels = bytearray()
    for row in range(side):
        y = origin + (side-row-.5)*resolution
        for col in range(side):
            x = origin + (col+.5)*resolution
            occupied = any(abs(x-p[0]) <= h[0]+resolution/2 and
                           abs(y-p[1]) <= h[1]+resolution/2 for p, h in boxes)
            pixels.append(0 if occupied else 254)
    image = output/'map.pgm'
    image.write_bytes(f'P5\n{side} {side}\n255\n'.encode()+pixels)
    path = output/'map.yaml'
    path.write_text(yaml.safe_dump(dict(image='map.pgm', resolution=resolution,
        origin=[origin, origin, 0.], negate=0, occupied_thresh=.65, free_thresh=.25)), encoding='utf-8')
    return path


def materialize_scene(engine: str, scenario: str, output: Path, *, controllers_file=None) -> dict:
    scenarios = {'g1', 'g2', 'front', 'diagonal', 'detour', 'blocked', 'cancel', 'intrusion'}
    if engine not in ('mujoco', 'gazebo') or scenario not in scenarios:
        raise ValueError('unknown engine or flat benchmark scenario')
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    share = description_dir()
    controllers = yaml.safe_load(Path(controllers_file or share/'config/controllers.yaml').read_text())
    controllers['controller_manager']['ros__parameters']['arm_trajectory_controller']['type'] = (
        'integrated_robot_controller/JointTrajectoryController')
    controller_data = yaml.safe_dump(controllers, sort_keys=False).encode()
    (output/'controllers.yaml').write_bytes(controller_data)
    controller_hash = hashlib.sha256(controller_data).hexdigest()
    short_controller = Path(tempfile.gettempdir())/f'ch13_5_controllers_{controller_hash[:16]}.yaml'
    if short_controller.exists():
        if short_controller.read_bytes() != controller_data:
            raise ValueError('short native controller path hash collision')
    else:
        with short_controller.open('xb') as stream:
            stream.write(controller_data)
    target = (2.2, 0.) if scenario in ('detour', 'blocked') else (
        (1.6, .6) if scenario == 'diagonal' else (1.6, 0.))
    parts = cup_parts(*target) if scenario not in ('g1', 'g2') else []
    obstacles = []
    if scenario == 'detour':
        obstacles.append(dict(name='detour_obstacle', kind='box', pos=(.70, -.50, .45),
                              size=(.04, .25, .45), rgba=(.2, .3, .6, 1.)))
    if scenario == 'blocked':
        obstacles.append(dict(name='blocking_wall', kind='box', pos=(.75, 0., .8),
                              size=(.05, 4.7, .8), rgba=(.2, .3, .6, 1.)))
    # A shared closed map boundary matches actual engine geometry.
    for name, p, size in (
        ('north', (0, 4.7, .6), (4.7, .05, .6)),
        ('south', (0, -4.7, .6), (4.7, .05, .6)),
        ('east', (4.7, 0, .6), (.05, 4.7, .6)),
        ('west', (-4.7, 0, .6), (.05, 4.7, .6))):
        obstacles.append(dict(name=name, kind='box', pos=p, size=size, rgba=(.6, .6, .6, 1.)))
    model_path = output/'world.xml'
    robot = output/'robot.urdf'
    urdf = xacro.process_file(str(share/'urdf/robot_system.urdf.xacro'), mappings={
        'control_backend': engine, 'hip_mount_y': '.13', 'navigation_enabled': 'true',
        'vision_enabled': 'true', 'mujoco_headless': 'true',
        'mujoco_auto_register_cameras': 'false', 'mujoco_model_path': str(model_path),
        'controllers_file': str(short_controller)}).toxml()
    # Explicit source collision labels survive fixed-joint reduction; the final
    # lookup still comes from converted SDF, never guessed mangled link names.
    urdf_tree = ET.fromstring(urdf)
    for link in urdf_tree.findall('link'):
        for i, collision in enumerate(link.findall('collision')):
            collision.set('name', f"navcol__{link.get('name')}__{i}")
    urdf = ET.tostring(urdf_tree, encoding='unicode')
    robot.write_text(urdf, encoding='utf-8')
    if engine == 'mujoco':
        tree = ET.fromstring(navigation_mjcf(compile_model(urdf)))
        tree.set('model', 'section_13_5')
        ET.SubElement(tree, 'statistic', extent='1')
        visual = ET.SubElement(tree, 'visual')
        ET.SubElement(visual, 'global', offwidth='320', offheight='240')
        ET.SubElement(visual, 'map', znear='.1', zfar='5')
        ET.SubElement(visual, 'quality', shadowsize='512')
        world = tree.find('worldbody')
        base = world.find("body[@name='base_link']")
        for geom in base.iter('geom'):
            geom.set('group', '1')
        for geom in world.findall('geom'):
            geom.set('group', '0')
        ET.SubElement(base, 'site', name='navigation_imu_site', size='.001', rgba='0 0 0 0')
        sensor = ET.SubElement(tree, 'sensor')
        ET.SubElement(sensor, 'accelerometer', name='navigation_accelerometer', site='navigation_imu_site')
        ET.SubElement(sensor, 'gyro', name='navigation_gyro', site='navigation_imu_site')
        for part in parts + obstacles:
            a = part.get('yaw', 0.)
            ET.SubElement(world, 'geom', name=part['name'], type=part['kind'],
                pos=_numbers(part['pos']), size=_numbers(part['size']), rgba=_numbers(part['rgba']),
                quat=_numbers((math.cos(a/2), 0, 0, math.sin(a/2))), group='0')
        ET.ElementTree(tree).write(model_path, encoding='utf-8', xml_declaration=True)
    else:
        tree = ET.parse(share/'worlds/vision_fixture.sdf')
        world = tree.find('world')
        world.set('name', 'section_13_5')
        world.remove(world.find("model[@name='vision_fixture']"))
        ET.SubElement(world, 'plugin', filename='gz-sim-imu-system', name='gz::sim::systems::Imu')
        _sdf_parts(world, parts + obstacles)
        model_path = output/'world.sdf'
        tree.write(model_path, encoding='utf-8', xml_declaration=True)
    boxes = [(p['pos'], p['size']) for p in parts+obstacles if p['kind'] == 'box'
             and (p['name'] == 'table' or p in obstacles)]
    map_path = _map(output, boxes)
    def bound(path):
        return dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    record = dict(schema=1, engine=engine, scenario=scenario, target=target,
        localization='native_ground_truth', world=bound(model_path), robot=bound(robot),
        map=bound(map_path), map_image=bound(output/'map.pgm'),
        controllers=bound(output/'controllers.yaml'), native_controllers=bound(short_controller))
    if engine == 'gazebo':
        converted = subprocess.run(['gz', 'sdf', '-p', str(robot)], check=True,
                                   text=True, capture_output=True, timeout=30)
        sdf = ET.fromstring(converted.stdout)
        for visual in sdf.findall('.//visual'):
            flags = visual.find('visibility_flags')
            if flags is None:
                flags = ET.SubElement(visual, 'visibility_flags')
            flags.text = '2'  # Camera sees all; lidar mask1 excludes robot only.
        robot_sdf = output/'robot.sdf'
        ET.ElementTree(sdf).write(robot_sdf, encoding='utf-8', xml_declaration=True)
        record['robot_sdf'] = bound(robot_sdf)
        mapping = {}
        for prefix in ('fr', 'fl', 'rr', 'rl'):
            token = f'navcol__{prefix}_foot__0'
            matches = [f"integrated_robot::{link.get('name')}::{collision.get('name')}"
                       for link in sdf.findall('.//model/link') for collision in link.findall('collision')
                       if token in collision.get('name', '')]
            if len(matches) != 1:
                raise ValueError('fixed-joint conversion did not resolve one foot collision')
            mapping[matches[0]] = f'{prefix}_foot'
        record['foot_collision_map'] = mapping
        record['ground_collision'] = 'ground_plane::link::collision'
        (output/'sdf_conversion.log').write_text(converted.stderr, encoding='utf-8')
    (output/'scene.json').write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
    return record


def load_scene(engine, directory):
    directory = Path(directory).resolve()
    record = json.loads((directory/'scene.json').read_text())
    if record.get('schema') != 1 or record.get('engine') != engine:
        raise ValueError('scene engine/schema mismatch')
    keys = ['world', 'robot', 'map', 'map_image', 'controllers', 'native_controllers']
    if engine == 'gazebo':
        keys.append('robot_sdf')
    for key in keys:
        entry = record[key]
        path = Path(entry['path']).resolve()
        if key != 'native_controllers' and not path.is_relative_to(directory):
            raise ValueError('scene path outside bundle')
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('scene bound file hash mismatch: '+key)
    if record['controllers']['sha256'] != record['native_controllers']['sha256']:
        raise ValueError('scene native controller hash mismatch')
    return record
