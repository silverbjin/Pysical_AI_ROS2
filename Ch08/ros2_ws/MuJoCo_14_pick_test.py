import time
import numpy as np
import mujoco
import mujoco.viewer

XML_PATH = "src/my_robot_description/urdf/my_robot_6D.xml"
EE_SITE = "ee_site"
CUBE_SITE = "cube_site"
JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
ACTUATOR_NAMES = ["joint1_ctrl", "joint2_ctrl", "joint3_ctrl", "joint4_ctrl", "joint5_ctrl", "joint6_ctrl", "finger1_ctrl", "finger2_ctrl"]
FINGER_OPEN = 0.025
FINGER_CLOSE = 0.0

model = mujoco.MjModel.from_xml_path(XML_PATH)
data = mujoco.MjData(model)
mujoco.mj_forward(model, data)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
cube_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, CUBE_SITE)
cube_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")
actuator_id = {name: mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, name) for name in ACTUATOR_NAMES}

initial_qpos = data.qpos.copy()
initial_qvel = data.qvel.copy()

def reset_world():
    data.qpos[:] = initial_qpos
    data.qvel[:] = 0.0
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)

def get_tcp():
    return data.site_xpos[ee_site_id].copy()

def get_cube_pos():
    return data.site_xpos[cube_site_id].copy()

def set_joint_ctrl(q_target):
    for i in range(6):
        data.ctrl[actuator_id[ACTUATOR_NAMES[i]]] = float(q_target[i])

def open_gripper():
    data.ctrl[actuator_id["finger1_ctrl"]] = FINGER_OPEN
    data.ctrl[actuator_id["finger2_ctrl"]] = FINGER_OPEN

def close_gripper():
    data.ctrl[actuator_id["finger1_ctrl"]] = FINGER_CLOSE
    data.ctrl[actuator_id["finger2_ctrl"]] = FINGER_CLOSE

def step_n(n):
    for _ in range(n):
        mujoco.mj_step(model, data)

def solve_ik(model, data, target_pos, site_name="ee_site", max_iter=300, damping=0.05, alpha=0.5, tol=1e-3):
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, site_name)
    q = data.qpos[:6].copy()
    q_min = model.jnt_range[:6, 0]
    q_max = model.jnt_range[:6, 1]
    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))
    for i in range(max_iter):
        data.qpos[:6] = q
        mujoco.mj_forward(model, data)
        current_pos = data.site_xpos[site_id].copy()
        error = target_pos - current_pos
        if np.linalg.norm(error) < tol:
            print(f"IK Converged in {i} iterations")
            return q
        mujoco.mj_jacSite(model, data, jacp, jacr, site_id)
        J = jacp[:, :6]
        dq = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(3)) @ error
        q += alpha * dq
        q = np.clip(q, q_min, q_max)
    print("IK Failed")
    return q

def move_to_joint_target(q_target, max_steps=15000, joint_tol=1e-3):
    set_joint_ctrl(q_target)
    for i in range(max_steps):
        mujoco.mj_step(model, data)
        joint_error = np.linalg.norm(q_target - data.qpos[:6])
        if joint_error < joint_tol:
            print(f"Joint Converged in {i} steps")
            break
    return data.qpos[:6].copy()

def print_state(tag):
    print(f"\n--- {tag} ---")
    print("tcp  :", np.round(get_tcp(), 6))
    print("cube :", np.round(get_cube_pos(), 6))
    print("jpos :", np.round(data.qpos[:6], 6))
    print("f1   :", float(data.qpos[6]))
    print("f2   :", float(data.qpos[7]))

def wait_seconds(sec, steps_per_sec=500):
    step_n(int(sec * steps_per_sec))

def pick_test():
    print("\n==============================")
    print("Pick Test Start")
    print("==============================")
    reset_world()
    open_gripper()
    wait_seconds(2.0)
    cube_pos = get_cube_pos().copy()
    print("\nCube Pos:", cube_pos)
    approach_pos = cube_pos + np.array([0.0, 0.0, 0.12])
    pick_pos = cube_pos + np.array([0.0, 0.0, 0.04])
    lift_pos = cube_pos + np.array([0.0, 0.0, 0.15])
    print("Approach Pos:", approach_pos)
    print("Pick Pos:", pick_pos)
    print("Lift Pos:", lift_pos)
    q_approach = solve_ik(model, data, approach_pos)
    print("\nApproach Joint Target:", np.round(q_approach, 3))
    reset_world()
    move_to_joint_target(q_approach)
    wait_seconds(1.0)
    print("\nTCP at Approach:", np.round(get_tcp(), 6))
    q_pick = solve_ik(model, data, pick_pos)
    print("\nPick Joint Target:", np.round(q_pick, 3))
    move_to_joint_target(q_pick)
    wait_seconds(0.8)
    print("\nTCP at Pick:", np.round(get_tcp(), 6))
    print_state("BEFORE CLOSE")
    close_gripper()
    wait_seconds(2.0)
    print_state("AFTER CLOSE")
    q_lift = solve_ik(model, data, lift_pos)
    print("\nLift Joint Target:", np.round(q_lift, 3))
    move_to_joint_target(q_lift)
    wait_seconds(1.0)
    print("\nTCP after Lift:", np.round(get_tcp(), 6))
    print("\n=== Pick Test Result ===")
    print("Target TCP :", pick_pos)
    print("Actual TCP :", get_tcp())
    print("TCP Error  :", np.linalg.norm(pick_pos - get_tcp()))
    print("Cube Pos   :", get_cube_pos())

with mujoco.viewer.launch_passive(model, data) as viewer:
    pick_test()
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(0.01)