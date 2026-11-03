"""Opt-in, provenance-recorded corrections for the pinned IIT MuJoCo deployment."""

def freeze_arm_reference(platform):
    """Detach an upstream qpos view; preserve target values and engine state."""
    platform.desired_joint_pos_arm = platform.desired_joint_pos_arm.copy()


def configure_native_arm_pd(model, kp, kd):
    """Represent the original arm PD law natively with its original force caps.

    After this call ctrl[12:18] carries arm joint position targets (radians),
    not torques. Callers must overwrite the upstream arm torque inputs before
    EVERY mj_step. This is a simulator-specific correction, not a new gait.
    Physical masses, damping, geometry, timestep and leg actuators are kept.
    The integrator becomes implicitfast so it can see arm velocity feedback.
    """
    import math
    import mujoco
    import numpy as np

    if not (math.isfinite(kp) and math.isfinite(kd) and kp > 0 and kd >= 0):
        raise ValueError('finite positive Kp and nonnegative Kd required')
    if model.nu != 19 or model.nq != 27 or model.nv != 26:
        raise ValueError('requires the pinned Go2/Piper model layout')
    arm = slice(12, 18)
    expected = np.array([model.joint('joint'+str(i)).id for i in range(1, 7)])
    unit_gear = np.zeros((6, 6)); unit_gear[:, 0] = 1
    if (not np.array_equal(model.actuator_trnid[arm, 0], expected)
            or not np.array_equal(model.actuator_gear[arm], unit_gear)
            or not np.all(model.actuator_gaintype[arm] == mujoco.mjtGain.mjGAIN_FIXED)
            or not np.all(model.actuator_biastype[arm] == mujoco.mjtBias.mjBIAS_NONE)
            or not np.all(model.actuator_gainprm[arm, 0] == 1)
            or not np.all(model.actuator_ctrllimited[arm])):
        raise ValueError('expected original unit-gear bounded arm torque motors')
    caps = model.actuator_ctrlrange[arm].copy()
    if not np.isfinite(caps).all() or not np.all(caps[:, 0] < caps[:, 1]):
        raise ValueError('invalid original motor force caps')
    model.actuator_forcerange[arm] = caps
    model.actuator_forcelimited[arm] = True
    model.actuator_ctrllimited[arm] = False
    model.actuator_gainprm[arm, 0] = kp
    model.actuator_biastype[arm] = mujoco.mjtBias.mjBIAS_AFFINE
    model.actuator_biasprm[arm] = 0
    model.actuator_biasprm[arm, 1] = -kp
    model.actuator_biasprm[arm, 2] = -kd
    model.opt.integrator = mujoco.mjtIntegrator.mjINT_IMPLICITFAST

def consistent_walking_run_source(source):
    """Correct only the non-policy-tick gain selection in pinned upstream run."""
    replacements = {}
    for letter in ("p", "d"):
        left = "self.K" + letter + "_legs"
        prefix = "self.locomotion_policy.K" + letter
        old = left + " = " + prefix + "_stand_up_and_down"
        new = (left + " = (" + prefix + "_walking if self.console.isRLActivated "
               "else " + prefix + "_stand_up_and_down)")
        if source.count(old) != 1:
            raise ValueError("pinned upstream gain-selection assignment not found exactly once")
        replacements[old] = new
    for old, new in replacements.items():
        source = source.replace(old, new)
    return source
