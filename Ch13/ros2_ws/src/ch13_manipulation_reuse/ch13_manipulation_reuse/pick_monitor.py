"""Physics contact guard and write-only oracle evidence for the pick profile."""
import numpy as np
import mujoco
from .model import TCP_LINK6
from .pick_scene import TARGET,contact_allowed
from .pick_acceptance import assess_pick


class PickMonitor:
    def __init__(self,model):
        self.model=model;self.rows=[];self.established=set();self.next_sample=0.;self.forces={'link7':0.,'link8':0.}
        base=model.body('base').id;self.robot_bodies=set()
        for body in range(1,model.nbody):
            ancestor=body
            while ancestor not in (0,base):ancestor=int(model.body_parentid[ancestor])
            if ancestor==base:self.robot_bodies.add(body)
        self.target=model.body(TARGET).id;self.free=int(model.jnt_qposadr[model.joint('reuse_target_free').id])
        self.link6=model.body('link6').id

    def step(self,p,lease,stamp_ns):
        phase='WAITING' if lease.message is None else lease.message.get('task_phase','WAITING')
        live=lease.phase in ('READY','EXECUTING','CARRY_ARMED','CARRY')
        forces={'link7':0.,'link8':0.}
        self.support_N=0.
        for index,contact in enumerate(p.mjData.contact):
            a,b=map(int,contact.geom);ba,bb=int(self.model.geom_bodyid[a]),int(self.model.geom_bodyid[b])
            if ((ba==self.target and self.model.geom(b).name=='reuse_receiving_support')
                or (bb==self.target and self.model.geom(a).name=='reuse_receiving_support')):
                force=np.zeros(6);mujoco.mj_contactForce(self.model,p.mjData,index,force)
                self.support_N+=max(0.,float(force[0]))
            if self.model.geom_group[a]!=5 and self.model.geom_group[b]!=5:continue
            if ba in self.robot_bodies:robot,other=ba,bb
            elif bb in self.robot_bodies:robot,other=bb,ba
            else:continue  # target/pedestal are both environment, not a robot collision
            name=self.model.body(robot).name;other_name=self.model.body(other).name
            pair=(robot,other)
            allowed=contact_allowed(name,other_name,phase,live)
            # Retain an already established finger-target pair while braking or
            # holding after loss/revoke; never expand permission to a new object.
            if allowed:self.established.add(pair)
            elif live or pair not in self.established:raise RuntimeError('pick forbidden contact:'+name+':'+other_name+':'+phase)
            if other==self.target and name in forces:
                force=np.zeros(6);mujoco.mj_contactForce(self.model,p.mjData,index,force)
                forces[name]+=max(0.,float(force[0]))
        self.forces=forces
        sim=stamp_ns/1e9
        if sim<self.next_sample:return
        self.next_sample=sim+.019
        mujoco.mj_kinematics(self.model,p.mjData)
        target=p.mjData.qpos[self.free:self.free+3].copy()
        rotation=p.mjData.xmat[self.link6].reshape(3,3)
        tcp=p.mjData.xpos[self.link6]+rotation@np.array(TCP_LINK6)
        self.rows.append(dict(sim_s=sim,phase=phase,target=target.tolist(),tcp=tcp.tolist(),
                              relative_tcp=(rotation.T@(target-tcp)).tolist(),target_contact_N=forces,
                              gripper_qpos=p.mjData.qpos[25:27].tolist(),gripper_effort_N=float(p.mjData.actuator_force[18]),
                              internal_gripper_reference=float(p.desired_joint_pos_gripper),
                              target_support_N=self.support_N,
                              source='actual_engine_freejoint_and_contact_for_evaluation_only'))

    def summary(self):
        return dict(assessment=assess_pick(self.rows),rows=self.rows,
                    profile=dict(radius_m=.02,height_m=.08,mass_kg=.02,sliding_friction=.8,
                                 target_freejoint='reuse_target_free',no_weld=True))
