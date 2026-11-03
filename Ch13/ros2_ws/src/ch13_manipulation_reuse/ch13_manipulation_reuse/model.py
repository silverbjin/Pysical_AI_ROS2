"""Planning description derived from the pinned integrated MuJoCo model.

No mesh redistribution: visuals show the same primitive collision proxies used
by the engine's educational camera. Capsule unions preserve physical coverage.
"""
import xml.etree.ElementTree as ET
import warnings
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation

TCP_LINK6=(0.,0.,.11003)


def numbers(values):return ' '.join(format(float(x),'.14g') for x in values)


def origin(element,pos,rotation):
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore',message='Gimbal lock detected.*',category=UserWarning)
        rpy=rotation.as_euler('xyz')
    ET.SubElement(element,'origin',xyz=numbers(pos),rpy=numbers(rpy))


def generate_description(model):
    robot=ET.Element('robot',name='ch13_go2_piper_reuse')
    base=model.body('base').id
    bodies=[]
    for body in range(1,model.nbody):
        ancestor=body
        while ancestor not in (0,base):ancestor=int(model.body_parentid[ancestor])
        if ancestor==base:bodies.append(body)
    collision_ids=[]
    def rotation(quat):return Rotation.from_quat(np.roll(quat,-1))
    for body in bodies:
        name='reuse/'+model.body(body).name
        link=ET.SubElement(robot,'link',name=name)
        if model.body_mass[body]>0:
            inertial=ET.SubElement(link,'inertial')
            origin(inertial,model.body_ipos[body],rotation(model.body_iquat[body]))
            ET.SubElement(inertial,'mass',value=str(float(model.body_mass[body])))
            diag=model.body_inertia[body]
            ET.SubElement(inertial,'inertia',ixx=str(diag[0]),iyy=str(diag[1]),izz=str(diag[2]),ixy='0',ixz='0',iyz='0')
        for g in range(model.body_geomadr[body],model.body_geomadr[body]+model.body_geomnum[body]):
            if not (model.geom_contype[g] or model.geom_conaffinity[g]):continue
            collision_ids.append(g)
            kind,size=int(model.geom_type[g]),model.geom_size[g]
            local_rotation=rotation(model.geom_quat[g]);position=model.geom_pos[g].copy()
            shapes=[]
            if kind==mujoco.mjtGeom.mjGEOM_BOX:
                shapes=[('box',dict(size=numbers(2*size)),np.zeros(3))]
            elif kind==mujoco.mjtGeom.mjGEOM_SPHERE:
                shapes=[('sphere',dict(radius=str(size[0])),np.zeros(3))]
            elif kind in (mujoco.mjtGeom.mjGEOM_CAPSULE,mujoco.mjtGeom.mjGEOM_CYLINDER):
                shapes=[('cylinder',dict(radius=str(size[0]),length=str(2*size[1])),np.zeros(3))]
                if kind==mujoco.mjtGeom.mjGEOM_CAPSULE:
                    shapes += [('sphere',dict(radius=str(size[0])),np.array([0.,0.,z])) for z in (-size[1],size[1])]
            else:
                # AABB is a conservative enclosure in the geom's local frame.
                center,half=model.geom_aabb[g,:3],model.geom_aabb[g,3:]
                shapes=[('box',dict(size=numbers(2*half)),center)]
            for k,(shape,attributes,offset) in enumerate(shapes):
                for tag in ('collision','visual'):
                    part=ET.SubElement(link,tag,name='geom_%d_%d'%(g,k))
                    origin(part,position+local_rotation.apply(offset),local_rotation)
                    geometry=ET.SubElement(part,'geometry');ET.SubElement(geometry,shape,**attributes)
                    if tag=='visual':
                        material=ET.SubElement(part,'material',name='collision_proxy')
                        ET.SubElement(material,'color',rgba='.5 .6 .7 1')
        if body==base:continue
        count=int(model.body_jntnum[body])
        joint_id=int(model.body_jntadr[body])
        if count>1:raise ValueError('one joint per robot body required')
        if count:
            if np.linalg.norm(model.jnt_pos[joint_id])>1e-10:raise ValueError('nonzero joint anchor requires explicit conversion')
            kind=int(model.jnt_type[joint_id])
            if kind not in (mujoco.mjtJoint.mjJNT_HINGE,mujoco.mjtJoint.mjJNT_SLIDE):
                raise ValueError(('unsupported robot joint',model.body(body).name,joint_id,int(kind)))
            joint_name=model.joint(joint_id).name
            joint=ET.SubElement(robot,'joint',name=joint_name,type='revolute' if kind==3 else 'prismatic')
            ET.SubElement(joint,'axis',xyz=numbers(model.jnt_axis[joint_id]))
            lo,hi=model.jnt_range[joint_id]
            actuator=[a for a in range(model.nu) if model.actuator_trnid[a,0]==joint_id]
            effort=float(model.actuator_ctrlrange[actuator[0],1]) if actuator else .5
            ET.SubElement(joint,'limit',lower=str(lo),upper=str(hi),effort=str(effort),velocity='.5' if kind==3 else '.04')
            if joint_name=='joint8':ET.SubElement(joint,'mimic',joint='joint7',multiplier='-1',offset='0')
        else:joint=ET.SubElement(robot,'joint',name='fixed_'+model.body(body).name,type='fixed')
        ET.SubElement(joint,'parent',link='reuse/'+model.body(int(model.body_parentid[body])).name)
        ET.SubElement(joint,'child',link=name)
        origin(joint,model.body_pos[body],rotation(model.body_quat[body]))
    ET.SubElement(robot,'link',name='reuse/tcp')
    joint=ET.SubElement(robot,'joint',name='tcp_fixed',type='fixed')
    ET.SubElement(joint,'parent',link='reuse/link6');ET.SubElement(joint,'child',link='reuse/tcp')
    origin(joint,TCP_LINK6,Rotation.identity())
    semantic=ET.Element('robot',name='ch13_go2_piper_reuse')
    ET.SubElement(semantic,'virtual_joint',name='world_joint',type='floating',parent_frame='reuse/odom',child_link='reuse/base')
    group=ET.SubElement(semantic,'group',name='manipulator_arm')
    ET.SubElement(group,'chain',base_link='reuse/base',tip_link='reuse/tcp')
    gripper=ET.SubElement(semantic,'group',name='gripper')
    ET.SubElement(gripper,'joint',name='joint7');ET.SubElement(gripper,'joint',name='joint8')
    ET.SubElement(semantic,'end_effector',name='piper_gripper',parent_link='reuse/tcp',group='gripper',parent_group='manipulator_arm')
    for name,value in [('open',.03),('close',0.)]:
        state=ET.SubElement(semantic,'group_state',name=name,group='gripper')
        ET.SubElement(state,'joint',name='joint7',value=str(value))
    for body in bodies:
        parent=int(model.body_parentid[body])
        if parent in bodies:
            ET.SubElement(semantic,'disable_collisions',link1='reuse/'+model.body(parent).name,
                          link2='reuse/'+model.body(body).name,reason='Adjacent')
    ET.SubElement(semantic,'disable_collisions',link1='reuse/link7',link2='reuse/link8',reason='Finger closure')
    for finger in ('link6','link7','link8'):
        ET.SubElement(semantic,'disable_collisions',link1='reuse/tcp',link2='reuse/'+finger,reason='Empty fixed TCP')
    ET.indent(robot);ET.indent(semantic)
    return ET.tostring(robot,encoding='unicode'),ET.tostring(semantic,encoding='unicode'),dict(
        model_nq=model.nq,model_nv=model.nv,robot_tf_owner='engine_only',collision_geom_ids=collision_ids,
        tcp_link6=list(TCP_LINK6),visuals='physical collision proxies; no redistributed mesh',
        velocity_limits='educational .5rad/s arm ceiling; apply scaling<=.1; not hardware datasheet')


def urdf_fk(description,positions):
    robot=ET.fromstring(description);transforms={'reuse/base':np.eye(4)}
    remaining=list(robot.findall('joint'))
    while remaining:
        advanced=False
        for joint in list(remaining):
            parent=joint.find('parent').attrib['link'];child=joint.find('child').attrib['link']
            if parent not in transforms:continue
            local=np.eye(4);pose=joint.find('origin')
            local[:3,3]=np.fromstring(pose.attrib['xyz'],sep=' ')
            local[:3,:3]=Rotation.from_euler('xyz',np.fromstring(pose.attrib['rpy'],sep=' ')).as_matrix()
            motion=np.eye(4);value=positions.get(joint.attrib['name'],0.)
            mimic=joint.find('mimic')
            if mimic is not None:value=positions.get(mimic.attrib['joint'],0.)*float(mimic.attrib['multiplier'])
            if joint.attrib['type']!='fixed':
                axis=np.fromstring(joint.find('axis').attrib['xyz'],sep=' ')
                if joint.attrib['type']=='revolute':motion[:3,:3]=Rotation.from_rotvec(axis*value).as_matrix()
                else:motion[:3,3]=axis*value
            transforms[child]=transforms[parent]@local@motion
            remaining.remove(joint);advanced=True
        if not advanced:raise ValueError('disconnected planning model')
    return transforms
