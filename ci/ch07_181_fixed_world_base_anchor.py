#!/usr/bin/env python3
"""G04B-only TEST fixture: one world -> base_link fixed SDF joint.

Never physically attach, teleport or modify the dynamic grasped rod.
Original controller, robot joints, collision geometry and MoveIt URDF
remain unchanged. Gazebo receives only this extra world-fixed base joint.
"""
import argparse, hashlib, json
from copy import deepcopy
from pathlib import Path
import xml.etree.ElementTree as ET
ANCHOR_NAME = 'g04b_test_only_world_to_base_fixed'

def anchored_world_base_model(source: str):
    root=ET.fromstring(source)
    if root.tag != 'sdf':
        raise ValueError('G04B_181_SDF_ROOT_REQUIRED')
    models=root.findall('./model')
    if len(models)!=1 or models[0].get('name')!='my_robot':
        raise ValueError('G04B_181_ONLY_ORIGINAL_ROBOT_MODEL_ALLOWED')
    model=models[0]
    if model.findtext('static',default='false').strip().lower()!='false':
        raise ValueError('G04B_181_ROBOT_MUST_REMAIN_DYNAMIC')
    links=[l.get('name') for l in model.findall('link')]
    if 'base_link' not in links or 'world' in links:
        raise ValueError('G04B_181_ORIGINAL_BASE_LINK_NOT_FOUND_OR_RESERVED')
    joints=model.findall('joint')
    if len(joints)!=7 or len(set(j.get('name') for j in joints))!=7:
        raise ValueError('G04B_181_ORIGINAL_7_JOINT_CONTRACT_CHANGED')
    if any(j.findtext('parent',default='')=='world' for j in joints):
        raise ValueError('G04B_181_ALREADY_ANCHORED_DO_NOT_STACK')
    before=ET.tostring(root)
    anchor=ET.SubElement(model,'joint',{'name':ANCHOR_NAME,'type':'fixed'})
    ET.SubElement(anchor,'parent').text='world'
    ET.SubElement(anchor,'child').text='base_link'
    check=deepcopy(root)
    check.find('./model').remove(check.find("./model/joint[@name='"+ANCHOR_NAME+"']"))
    if ET.tostring(check)!=before:
        raise ValueError('G04B_181_MULTI_FACTOR_SDF_CHANGE')
    receipt={
      'source_sdf_sha256':hashlib.sha256(source.encode()).hexdigest(),
      'factor':'SINGLE_GAZEBO_WORLD_TO_ROBOT_BASE_FIXED_JOINT',
      'anchor':{'name':ANCHOR_NAME,'type':'fixed','parent':'world','child':'base_link'},
      'original_robot_links_preserved':True,
      'original_arm_and_finger_joints_preserved':True,
      'original_7_joint_count':len(joints),
      'rod_and_world_physics_changed':False,'object_attach_or_teleport':False,
      'G00_G04A':'NOT_RERUN','G04B':'BLOCKED_PENDING_REAL_GAZEBO',
      'G05':'NOT_RUN','Ch10':'HOLD'}
    return ET.tostring(root,encoding='unicode'),receipt

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--input',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--receipt',required=True)
    a=parser.parse_args()
    output,receipt=anchored_world_base_model(Path(a.input).read_text())
    Path(a.output).write_text(output)
    Path(a.receipt).write_text(json.dumps(receipt,indent=2)+'\n')
    print('CH07_181_TEST_ONLY_WORLD_BASE_FIXED_SINGLE_FACTOR_DEFINED')
if __name__=='__main__':main()
