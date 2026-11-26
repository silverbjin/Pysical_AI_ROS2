"""Prepare an isolated Ch11 model; never edit the original ROS package."""
import subprocess
import xml.etree.ElementTree as ET


def prepare_description(xacro_path):
    xml=subprocess.check_output(['xacro',str(xacro_path),'lidar_3d:=false'],text=True)
    root=ET.fromstring(xml)
    count=0
    for plugin in root.findall('.//plugin'):
        if plugin.get('name')!='gz::sim::systems::JointPositionController':continue
        name=plugin.findtext('joint_name')
        joint=name.split('_')[-2]
        kp,kd,limit=(40.,2.,20.) if joint=='hip' else (100.,4.,30.)
        for field,value in dict(p_gain=kp,d_gain=kd,i_gain=0.,
                cmd_max=limit,cmd_min=-limit,
                initial_position={'hip':0.,'thigh':-.5,'calf':1.}[joint]).items():
            element=plugin.find(field)
            if element is None:element=ET.SubElement(plugin,field)
            element.text=str(value)
        count+=1
    if count!=12:raise ValueError('Expected exactly twelve Gazebo position controllers')
    return ET.tostring(root,encoding='unicode')
