"""Authored hollow mug geometry for COCO cup trials; no textures or injected data."""
import math
from pathlib import Path
import xml.etree.ElementTree as ET


def cup_parts():
    parts = [dict(name='cup_bottom', kind='cylinder', pos=(1., 0., .622),
                  size=(.11, .008), rgba=(.9, .9, .88, 1.)),
             dict(name='coffee', kind='cylinder', pos=(1., 0., .798),
                  size=(.103, .002), rgba=(.08, .035, .01, 1.)),
             dict(name='table', kind='box', pos=(1., 0., .3),
                  size=(.35, .4, .3), rgba=(.35, .3, .25, 1.))]
    for i in range(48):
        angle = 2*math.pi*i/48
        parts.append(dict(name=f'cup_wall_{i}', kind='box',
            pos=(1.+.11*math.cos(angle), .11*math.sin(angle), .73),
            size=(.005, .008, .1), yaw=angle, rgba=(.9, .9, .88, 1.)))
    for i in range(40):
        angle = 2*math.pi*i/40
        parts.append(dict(name=f'cup_handle_{i}', kind='sphere',
            pos=(1., .14+.065*math.cos(angle), .73+.065*math.sin(angle)),
            size=(.013,), rgba=(.9, .9, .88, 1.)))
    return parts


def numbers(values):
    return ' '.join(str(v) for v in values)


def make_cup_fixture(engine, share, output):
    share, output = Path(share).resolve(), Path(output).resolve()
    if engine == 'mujoco':
        tree = ET.parse(share/'mujoco/vision_fixture.xml')
        tree.find('include').set('file', str(share/'mujoco/robot_system.xml'))
        world = tree.find('worldbody')
        world.remove(world.find('geom[@name="vision_fixture"]'))
        for part in cup_parts():
            angle = part.get('yaw', 0.)
            ET.SubElement(world, 'geom', name=part['name'], type=part['kind'],
                pos=numbers(part['pos']), size=numbers(part['size']), rgba=numbers(part['rgba']),
                quat=numbers((math.cos(angle/2), 0., 0., math.sin(angle/2))))
        target = output/'semantic_cup.xml'
    elif engine == 'gazebo':
        tree = ET.parse(share/'worlds/vision_fixture.sdf')
        world = tree.find('world')
        world.remove(world.find('model[@name="vision_fixture"]'))
        model = ET.SubElement(world, 'model', name='semantic_cup')
        ET.SubElement(model, 'static').text = 'true'
        link = ET.SubElement(model, 'link', name='link')
        for part in cup_parts():
            for tag in ('visual', 'collision'):
                element = ET.SubElement(link, tag, name=part['name'])
                ET.SubElement(element, 'pose').text = numbers((*part['pos'], 0., 0., part.get('yaw', 0.)))
                geometry = ET.SubElement(element, 'geometry')
                shape = ET.SubElement(geometry, part['kind'])
                if part['kind'] == 'box':
                    ET.SubElement(shape, 'size').text = numbers(2*v for v in part['size'])
                else:
                    ET.SubElement(shape, 'radius').text = str(part['size'][0])
                    if part['kind'] == 'cylinder':
                        ET.SubElement(shape, 'length').text = str(2*part['size'][1])
                if tag == 'visual':
                    material = ET.SubElement(element, 'material')
                    for key in ('ambient', 'diffuse'):
                        ET.SubElement(material, key).text = numbers(part['rgba'])
        target = output/'semantic_cup.sdf'
    else:
        raise ValueError('unknown physical engine')
    tree.write(target, encoding='utf-8', xml_declaration=True)
    return target
