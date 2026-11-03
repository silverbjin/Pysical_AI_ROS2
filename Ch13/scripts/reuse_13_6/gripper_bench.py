"""Isolated hand/load feasibility, NOT quadruped stability or integrated pick."""
import argparse
import fcntl
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import mujoco
from scipy.spatial.transform import Rotation
from ch13_manipulation_reuse.pick_scene import make_pick_model
from ch13_manipulation_reuse.model import TCP_LINK6


def numbers(values):return ' '.join(map(str,np.atleast_1d(values)))


def build(original,mass,contact_dim=3):
    root=ET.Element('mujoco');ET.SubElement(root,'compiler',angle='radian')
    ET.SubElement(root,'option',timestep='.002',gravity='0 0 -9.81',integrator='implicitfast')
    world=ET.SubElement(root,'worldbody')
    ET.SubElement(world,'geom',name='support',type='box',pos='.5 0 .25',size='.035 .035 .25',friction='.8 .005 .0001')
    R=np.column_stack(([0.,0.,-1.],[0.,1.,0.],[1.,0.,0.]))
    center=np.array([.5,0.,.54]);palm=center-R@TCP_LINK6
    carriage=ET.SubElement(world,'body',name='rig',pos=numbers(palm),quat=numbers(np.roll(Rotation.from_matrix(R).as_quat(),1)))
    ET.SubElement(carriage,'joint',name='rig_lift',type='slide',axis='-1 0 0',range='0 .15',limited='true')
    hand=ET.SubElement(carriage,'body',name='link6')
    for name in ('link6','link7','link8'):
        body=original.body(name).id
        child=hand if name=='link6' else ET.SubElement(hand,'body',name=name,pos=numbers(original.body_pos[body]),quat=numbers(original.body_quat[body]))
        ET.SubElement(child,'inertial',mass=str(original.body_mass[body]),pos=numbers(original.body_ipos[body]),
                      quat=numbers(original.body_iquat[body]),diaginertia=numbers(original.body_inertia[body]))
        if name!='link6':
            joint=original.joint('joint7' if name=='link7' else 'joint8').id;dof=original.jnt_dofadr[joint]
            ET.SubElement(child,'joint',name=original.joint(joint).name,type='slide',axis=numbers(original.jnt_axis[joint]),
                          pos=numbers(original.jnt_pos[joint]),range=numbers(original.jnt_range[joint]),limited='true',
                          damping=str(original.dof_damping[dof]),frictionloss=str(original.dof_frictionloss[dof]),armature=str(original.dof_armature[dof]))
        for geom in range(original.ngeom):
            if original.geom_bodyid[geom]!=body or not (original.geom_contype[geom] or original.geom_conaffinity[geom]):continue
            kind={int(mujoco.mjtGeom.mjGEOM_BOX):'box',int(mujoco.mjtGeom.mjGEOM_CAPSULE):'capsule'}[int(original.geom_type[geom])]
            ET.SubElement(child,'geom',type=kind,size=numbers(original.geom_size[geom]),pos=numbers(original.geom_pos[geom]),
                          quat=numbers(original.geom_quat[geom]),friction=numbers(original.geom_friction[geom]),
                          solref=numbers(original.geom_solref[geom]),solimp=numbers(original.geom_solimp[geom]),
                          margin=str(original.geom_margin[geom]),gap=str(original.geom_gap[geom]),
                          condim=str(original.geom_condim[geom]),priority=str(original.geom_priority[geom]))
    obj=ET.SubElement(world,'body',name='load',pos=numbers(center));ET.SubElement(obj,'freejoint',name='load_free')
    target=original.geom('reuse_target').id
    ET.SubElement(obj,'geom',name='load_geom',type='cylinder',size='.02 .04',mass=str(mass),friction='.8 .005 .0001',
                  margin=str(original.geom_margin[target]),gap=str(original.geom_gap[target]),condim=str(contact_dim),
                  solref=numbers(original.geom_solref[target]),solimp=numbers(original.geom_solimp[target]))
    equality=ET.SubElement(root,'equality')
    ET.SubElement(equality,'joint',joint1='joint7',joint2='joint8',polycoef='0 -1 0 0 0',
                  solref=numbers(original.eq_solref[0]),solimp=numbers(original.eq_solimp[0]))
    actuators=ET.SubElement(root,'actuator')
    ET.SubElement(actuators,'position',joint='rig_lift',kp='10000',kv='200',forcerange='-1000 1000')
    ET.SubElement(actuators,'motor',joint='joint7',ctrlrange='-.5 .5')
    return mujoco.MjModel.from_xml_string(ET.tostring(root,encoding='unicode'))


def run(mass,force_hold=False,contact_dim=3):
    root=Path(__file__).resolve().parents[3]
    original=make_pick_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml')
    model=build(original,mass,contact_dim);data=mujoco.MjData(model)
    q7=model.jnt_qposadr[model.joint('joint7').id];q8=model.jnt_qposadr[model.joint('joint8').id]
    v7=model.jnt_dofadr[model.joint('joint7').id];target=model.jnt_qposadr[model.joint('load_free').id]
    data.qpos[q7]=.03;data.qpos[q8]=-.03;mujoco.mj_forward(model,data);rows=[];contact_since=None;latched=None
    for index in range(5000):
        t=data.time;s=max(0.,min(1.,(t-3.)/5.));lift=.1*(10*s**3-15*s**4+6*s**5)
        data.ctrl[0]=lift
        position_target=.03 if t<1 else 0.
        if force_hold and latched is not None:
            scale=min(1.,(t-latched)/.5);effort=(1-scale)*.19+scale*.5
            position_target=float(data.qpos[q7])+(.8*data.qvel[v7]-effort)/10
        data.ctrl[1]=np.clip(10*(position_target-data.qpos[q7])-.8*data.qvel[v7],-.5,.5)
        mujoco.mj_step(model,data)
        if index%10==0:
            forces={'link7':0.,'link8':0.}
            for contact_id,contact in enumerate(data.contact):
                bodies=[int(model.geom_bodyid[g]) for g in contact.geom]
                if model.body('load').id not in bodies:continue
                for name in forces:
                    if model.body(name).id in bodies:
                        force=np.zeros(6);mujoco.mj_contactForce(model,data,contact_id,force);forces[name]+=max(0.,float(force[0]))
            if all(n>.005 for n in forces.values()):
                if contact_since is None:contact_since=data.time
                if data.time-contact_since>=.25 and latched is None:latched=data.time
            else:contact_since=None
            quat=data.qpos[target+3:target+7]
            tilt=float(np.arccos(np.clip(1-2*(quat[1]**2+quat[2]**2),-1.,1.)))
            rows.append(dict(sim_s=data.time,load_z=float(data.qpos[target+2]),load_tilt_rad=tilt,rig_lift=float(data.qpos[0]),
                             joint7=float(data.qpos[q7]),effort_N=float(data.actuator_force[1]),contacts=forces))
    hold=[r for r in rows if r['sim_s']>=8.]
    return dict(scope='isolated original hand on controlled bench carriage; NOT Go2 pick/stability',mass_kg=mass,
                force_hold=force_hold,target_contact_dim=contact_dim,force_hold_contact_time=latched,
                minimum_hold_lift_m=min(r['load_z']-.54 for r in hold),maximum_hold_tilt_rad=max(r['load_tilt_rad'] for r in hold),
                maximum_rig_lift_m=max(r['rig_lift'] for r in rows),rows=rows)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--mass',type=float,default=.02);parser.add_argument('--force-hold',action='store_true');parser.add_argument('--contact-dim',choices=[3,4],type=int,default=3);parser.add_argument('--output',required=True,type=Path);args=parser.parse_args()
    root=Path(__file__).resolve().parents[3]
    with (root.parent/'ch13_reuse_engine.lock').open('a+') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        result=run(args.mass,args.force_hold,args.contact_dim);args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
