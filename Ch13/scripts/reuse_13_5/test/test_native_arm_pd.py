import importlib.util
from pathlib import Path
import unittest
import numpy as np
import mujoco
ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml'
spec=importlib.util.spec_from_file_location('reproduction',ROOT/'Ch13/scripts/reuse_13_5/reproduce_upstream.py')
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class NativeArmPDTests(unittest.TestCase):
    def setUp(self):
        self.m=mujoco.MjModel.from_xml_path(str(SOURCE))
        self.q=self.m.key_qpos[self.m.key('home').id].copy();self.q[2]=1
    def test_same_pd_force_at_frozen_state_including_saturation(self):
        caps=self.m.actuator_ctrlrange[12:18].copy()
        mod.configure_native_arm_pd(self.m,50.,4.)
        for target in ([.01,.1,-.1,.02,-.02,.03],[1,1,1,1,1,1],[-1,-1,-1,-1,-1,-1]):
            with self.subTest(target=target):
                d=mujoco.MjData(self.m);d.qpos[:]=self.q;d.qvel[18:24]=[.1,.2,-.1,.1,-.2,.3]
                d.ctrl[12:18]=target;mujoco.mj_forward(self.m,d)
                expected=np.clip(50*(np.array(target)-d.qpos[19:25])-4*d.qvel[18:24],caps[:,0],caps[:,1])
                np.testing.assert_allclose(d.actuator_force[12:18],expected,rtol=0,atol=1e-12)
    def test_local_wrist_velocity_perturbations_contract(self):
        mod.configure_native_arm_pd(self.m,50.,4.)
        def nextv(v):
            d=mujoco.MjData(self.m);d.qpos[:]=self.q;d.qvel[21:24]=v
            d.ctrl[12:18]=self.q[19:25];mujoco.mj_forward(self.m,d)
            np.testing.assert_allclose(d.actuator_force[15:18],-4*v,rtol=0,atol=1e-12)
            mujoco.mj_step(self.m,d)
            return d.qvel[21:24].copy()
        eps=1e-5;J=np.column_stack([(nextv(np.ones(3)*.1+np.eye(3)[j]*eps)-nextv(np.ones(3)*.1-np.eye(3)[j]*eps))/(2*eps) for j in range(3)])
        self.assertLess(max(abs(np.linalg.eigvals(J))),1.)
    def test_preserves_physical_parameters_and_leg_actuation(self):
        mass=self.m.body_mass.copy();inertia=self.m.body_inertia.copy();damping=self.m.dof_damping.copy();leg_caps=self.m.actuator_ctrlrange[:12].copy();dt=self.m.opt.timestep
        mod.configure_native_arm_pd(self.m,50.,4.)
        np.testing.assert_array_equal(self.m.body_mass,mass);np.testing.assert_array_equal(self.m.body_inertia,inertia);np.testing.assert_array_equal(self.m.dof_damping,damping)
        np.testing.assert_array_equal(self.m.actuator_ctrlrange[:12],leg_caps);self.assertEqual(self.m.opt.timestep,dt)
    def test_rejects_invalid_gain_before_mutating_model(self):
        before=self.m.actuator_gainprm.copy()
        with self.assertRaises(ValueError):mod.configure_native_arm_pd(self.m,float('nan'),4.)
        np.testing.assert_array_equal(self.m.actuator_gainprm,before)
if __name__=='__main__':unittest.main()
