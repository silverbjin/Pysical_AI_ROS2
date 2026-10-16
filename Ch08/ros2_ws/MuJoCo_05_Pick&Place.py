import mujoco
import mujoco.viewer
import numpy as np

XML_PATH = "src/my_robot_description/urdf/my_robot_6D.xml"
CONTROL_PERIOD = 0.05

ARM_JOINTS = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
FINGER_JOINTS = ["joint_finger1", "joint_finger2"]
EE_SITE = "ee_site"
CUBE_SITE = "cube_site"
CUBE_GEOM = "cube_geom"

def get_joint_maps(model, joint_names):
    qadr, dadr, low, high = [], [], [], []
    for name in joint_names:
        jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, name)
        qadr.append(model.jnt_qposadr[jid])
        dadr.append(model.jnt_dofadr[jid])
        low.append(model.jnt_range[jid, 0])
        high.append(model.jnt_range[jid, 1])
    return np.array(qadr), np.array(dadr), np.array(low), np.array(high)

def cube_in_contact(model, data):
    for i in range(data.ncon):
        c = data.contact[i]
        g1 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom1)
        g2 = mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_GEOM, c.geom2)
        pair = {g1, g2}
        if CUBE_GEOM in pair and ("finger1_collision" in pair or "finger2_collision" in pair):
            return True
    return False

def ik_step_pos(model, data, site_id, target_pos, arm_qadr, arm_dadr, q_low, q_high, gain=0.35, damping=1e-3):
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    mujoco.mj_jacSite(model, data, jacp, jacr, site_id)
    J = jacp[:, arm_dadr]
    err = target_pos - data.site(site_id).xpos
    dq = J.T @ np.linalg.solve(J @ J.T + (damping ** 2) * np.eye(3), err)
    q_target = data.qpos[arm_qadr] + gain * dq
    return np.clip(q_target, q_low, q_high)

model = mujoco.MjModel.from_xml_path(XML_PATH)
data = mujoco.MjData(model)

arm_qadr, arm_dadr, arm_low, arm_high = get_joint_maps(model, ARM_JOINTS)
finger_qadr, _, finger_low, finger_high = get_joint_maps(model, FINGER_JOINTS)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
cube_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, CUBE_SITE)
touch1_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "finger1_touch")
touch2_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, "finger2_touch")

steps_per_control = max(1, int(round(CONTROL_PERIOD / model.opt.timestep)))
step_count = 0

phase = "move_above_pick"
phase_start_step = 0
arm_target = data.qpos[arm_qadr].copy()
grip_target = 0.0

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        if step_count % steps_per_control == 0:
            mujoco.mj_forward(model, data)

            cube_pos = data.site(cube_site_id).xpos.copy()
            ee_pos = data.site(ee_site_id).xpos.copy()

            pick_above = cube_pos + np.array([0.0, 0.0, 0.12])
            pick_down = cube_pos + np.array([0.0, 0.0, 0.03])
            lift_pos = cube_pos + np.array([0.0, 0.0, 0.18])
            place_above = cube_pos + np.array([0.25, 0.0, 0.12])
            place_down = cube_pos + np.array([0.25, 0.0, 0.05])

            if phase == "move_above_pick":
                arm_target = ik_step_pos(model, data, ee_site_id, pick_above, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.0
                if np.linalg.norm(ee_pos - pick_above) < 0.02:
                    phase = "descend_pick"
                    phase_start_step = step_count

            elif phase == "descend_pick":
                arm_target = ik_step_pos(model, data, ee_site_id, pick_down, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.0
                if np.linalg.norm(ee_pos - pick_down) < 0.015:
                    phase = "close_gripper"
                    phase_start_step = step_count

            elif phase == "close_gripper":
                arm_target = ik_step_pos(model, data, ee_site_id, pick_down, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.025
                touch1 = float(data.sensor("finger1_touch").data[0])
                touch2 = float(data.sensor("finger2_touch").data[0])
                if cube_in_contact(model, data) or (touch1 + touch2) > 1e-3 or (step_count - phase_start_step) > int(1.0 / model.opt.timestep):
                    phase = "lift"
                    phase_start_step = step_count

            elif phase == "lift":
                arm_target = ik_step_pos(model, data, ee_site_id, lift_pos, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.025
                if np.linalg.norm(ee_pos - lift_pos) < 0.02:
                    phase = "move_above_place"
                    phase_start_step = step_count

            elif phase == "move_above_place":
                arm_target = ik_step_pos(model, data, ee_site_id, place_above, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.025
                if np.linalg.norm(ee_pos - place_above) < 0.02:
                    phase = "descend_place"
                    phase_start_step = step_count

            elif phase == "descend_place":
                arm_target = ik_step_pos(model, data, ee_site_id, place_down, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.025
                if np.linalg.norm(ee_pos - place_down) < 0.015:
                    phase = "open_gripper"
                    phase_start_step = step_count

            elif phase == "open_gripper":
                arm_target = ik_step_pos(model, data, ee_site_id, place_down, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.0
                if (step_count - phase_start_step) > int(0.5 / model.opt.timestep):
                    phase = "retreat"
                    phase_start_step = step_count

            elif phase == "retreat":
                arm_target = ik_step_pos(model, data, ee_site_id, place_above, arm_qadr, arm_dadr, arm_low, arm_high)
                grip_target = 0.0
                if np.linalg.norm(ee_pos - place_above) < 0.02:
                    phase = "done"
                    phase_start_step = step_count

            if phase == "done":
                arm_target = arm_target.copy()
                grip_target = 0.0

            data.ctrl[0:6] = arm_target
            data.ctrl[6] = np.clip(grip_target, finger_low[0], finger_high[0])
            data.ctrl[7] = np.clip(grip_target, finger_low[1], finger_high[1])

            touch1 = float(data.sensor("finger1_touch").data[0])
            touch2 = float(data.sensor("finger2_touch").data[0])
            grasped = cube_in_contact(model, data)

            print(
                f"[step={step_count:6d}] phase={phase:16s} "
                f"ee=({ee_pos[0]:.3f},{ee_pos[1]:.3f},{ee_pos[2]:.3f}) "
                f"cube=({cube_pos[0]:.3f},{cube_pos[1]:.3f},{cube_pos[2]:.3f}) "
                f"grip={grip_target:.4f} touch=({touch1:.3f},{touch2:.3f}) "
                f"contact={grasped} qpos={np.round(data.qpos[arm_qadr], 3)}"
            )

        mujoco.mj_step(model, data)
        viewer.sync()
        step_count += 1