from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation
from ch13_manipulation_reuse.model import generate_description,urdf_fk,TCP_LINK6

ROOT=Path(__file__).resolve().parents[5]
SOURCE=ROOT.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'


def test_description_matches_integrated_limits_and_mimic():
    model=mujoco.MjModel.from_xml_path(str(SOURCE))
    urdf,srdf,manifest=generate_description(model)
    robot=ET.fromstring(urdf)
    for i in range(1,7):
        joint=robot.find("joint[@name='joint%d']"%i)
        limit=joint.find('limit')
        np.testing.assert_allclose([float(limit.attrib['lower']),float(limit.attrib['upper'])],model.jnt_range[model.joint('joint%d'%i).id])
    mimic=robot.find("joint[@name='joint8']/mimic")
    assert mimic.attrib['joint']=='joint7' and float(mimic.attrib['multiplier'])==-1.
    assert ET.fromstring(srdf).find("virtual_joint").attrib['type']=='floating'
    assert manifest['model_nq']==27 and manifest['robot_tf_owner']=='engine_only'


def test_fk_matches_mujoco_including_mount_axes_and_tcp():
    model=mujoco.MjModel.from_xml_path(str(SOURCE));data=mujoco.MjData(model)
    urdf,_,_=generate_description(model)
    rng=np.random.default_rng(136)
    for _ in range(20):
        data.qpos[:]=model.key_qpos[model.key('home').id]
        for i in range(1,7):
            joint=model.joint('joint%d'%i);lo,hi=model.jnt_range[joint.id]
            data.qpos[model.jnt_qposadr[joint.id]]=rng.uniform(lo*.8,hi*.8)
        data.qpos[25]=.03;data.qpos[26]=-.03;mujoco.mj_forward(model,data)
        positions={model.joint(i).name:float(data.qpos[model.jnt_qposadr[i]]) for i in range(1,model.njnt)}
        fk=urdf_fk(urdf,positions)
        base=model.body('base').id;root=np.eye(4)
        root[:3,:3]=data.xmat[base].reshape(3,3);root[:3,3]=data.xpos[base]
        for name in ['link1','link2','link3','link4','link5','link6','link7','link8']:
            actual=np.eye(4);body=model.body(name).id
            actual[:3,:3]=data.xmat[body].reshape(3,3);actual[:3,3]=data.xpos[body]
            np.testing.assert_allclose(root@fk['reuse/'+name],actual,atol=1e-8)
        link6=model.body('link6').id
        expected=data.xpos[link6]+data.xmat[link6].reshape(3,3)@np.array(TCP_LINK6)
        np.testing.assert_allclose((root@fk['reuse/tcp'])[:3,3],expected,atol=1e-8)


def test_all_robot_physical_geometries_have_collision_shapes():
    model=mujoco.MjModel.from_xml_path(str(SOURCE))
    urdf,_,manifest=generate_description(model)
    expected={g for g in range(model.ngeom) if model.geom_bodyid[g]>0 and (model.geom_contype[g] or model.geom_conaffinity[g])}
    assert set(manifest['collision_geom_ids'])==expected
    assert len(ET.fromstring(urdf).findall('.//collision'))>=len(expected)
    assert '0.05' not in ET.fromstring(urdf).find("joint[@name='joint1']/limit").attrib['effort']


def test_installed_moveit_robot_model_fk_matches_generated_description(tmp_path):
    from moveit.core.robot_model import RobotModel
    from moveit.core.robot_state import RobotState
    model=mujoco.MjModel.from_xml_path(str(SOURCE));urdf,srdf,_=generate_description(model)
    urdf_path=tmp_path/'robot.urdf';srdf_path=tmp_path/'robot.srdf'
    urdf_path.write_text(urdf);srdf_path.write_text(srdf)
    robot=RobotModel(str(urdf_path),str(srdf_path))
    assert robot.has_joint_model_group('manipulator_arm'),robot.get_model_info()
    state=RobotState(robot)
    state.set_to_default_values()
    q=np.array([.1,.4,-.7,.2,.1,-.2])
    positions=dict(zip(['joint%d'%i for i in range(1,7)],map(float,q)))
    # Avoid the installed binding's Eigen/NumPy input path in the NumPy2 venv.
    state.joint_positions=positions;state.update()
    expected=urdf_fk(urdf,positions)['reuse/tcp']
    actual=state.get_pose('reuse/tcp');matrix=np.eye(4)
    matrix[:3,3]=[actual.position.x,actual.position.y,actual.position.z]
    matrix[:3,:3]=Rotation.from_quat([actual.orientation.x,actual.orientation.y,actual.orientation.z,actual.orientation.w]).as_matrix()
    np.testing.assert_allclose(matrix,expected,atol=1e-8)
