"""Opt-in dynamic cylinder; explicit contact permissions and original robot."""
from pathlib import Path
import numpy as np
import mujoco
from ch13_navigation_reuse.scene import make_model

TARGET='reuse_pick_target'
GRASP_PHASES={'GRASP_APPROACH','CLOSE','LIFT','HOLD','POST_SETTLE'}


def add_target(spec):
    spec.delete(spec.geom('reuse_target'))
    body=spec.worldbody.add_body(name=TARGET,pos=[1.8,0.,.54])
    body.add_freejoint(name='reuse_target_free')
    body.add_geom(name='reuse_target',type=mujoco.mjtGeom.mjGEOM_CYLINDER,size=[.02,.04,0.],
                  mass=.02,friction=[.8,.005,.0001],group=5,rgba=[.9,.02,.02,1.])
    for key in spec.keys:
        key.qpos=np.concatenate((key.qpos,[1.8,0.,.54,1.,0.,0.,0.]))
        if len(key.qvel):key.qvel=np.concatenate((key.qvel,np.zeros(6)))


def make_pick_model(source):return make_model(source,'vision',spec_hook=add_target)


def configure_extended_pd(model,source,correction,kp,kd):
    canonical=make_model(source,'vision')
    assert (model.nq,model.nv,model.nu)==(34,32,19)
    assert model.jnt_qposadr[model.joint('reuse_target_free').id]==27
    np.testing.assert_array_equal(model.actuator_ctrlrange,canonical.actuator_ctrlrange)
    np.testing.assert_array_equal(model.actuator_trnid,canonical.actuator_trnid)
    for body in range(1,canonical.nbody):
        name=canonical.body(body).name;actual=model.body(name).id
        for attribute in ('body_mass','body_inertia','body_ipos','body_iquat'):
            np.testing.assert_array_equal(getattr(model,attribute)[actual],getattr(canonical,attribute)[body])
    correction.configure_native_arm_pd(canonical,kp,kd)
    for attribute in ('actuator_forcerange','actuator_forcelimited','actuator_ctrllimited',
                      'actuator_gainprm','actuator_biastype','actuator_biasprm'):
        getattr(model,attribute)[12:18]=getattr(canonical,attribute)[12:18]
    model.opt.integrator=canonical.opt.integrator


def contact_allowed(robot_body,other_body,phase,live):
    return bool(live and robot_body in ('link7','link8') and other_body==TARGET and phase in GRASP_PHASES)
