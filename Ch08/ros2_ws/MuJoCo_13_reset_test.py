import time
import numpy as np
import mujoco
import mujoco.viewer

XML_PATH = "src/my_robot_description/urdf/my_robot_6D.xml"
EE_SITE = "ee_site"
CUBE_SITE = "cube_site"

JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
ACTUATOR_NAMES = ["joint1_ctrl", "joint2_ctrl", "joint3_ctrl", "joint4_ctrl", "joint5_ctrl", "joint6_ctrl", "finger1_ctrl", "finger2_ctrl"]
FINGER_ACTUATOR_NAMES = ["finger1_ctrl", "finger2_ctrl"]
FINGER_JOINT_NAMES = ["joint_finger1", "joint_finger2"]

model = mujoco.MjModel.from_xml_path(XML_PATH)
data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
cube_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, CUBE_SITE)

#추가
cube_body_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "cube")

joint_qposadr = {}
for jn in JOINT_NAMES + FINGER_JOINT_NAMES:
    jid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_JOINT, jn)
    joint_qposadr[jn] = model.jnt_qposadr[jid]

actuator_id = {}
for an in ACTUATOR_NAMES:
    aid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, an)
    actuator_id[an] = aid

sensor_id = {}
for sn in ["finger1_touch", "finger2_touch"]:
    try:
        sid = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SENSOR, sn)
        sensor_id[sn] = sid
    except Exception:
        sensor_id[sn] = None

def get_sensor_scalar(model, data, name):
    sid = sensor_id.get(name, None)
    if sid is None or sid < 0:
        return None
    adr = model.sensor_adr[sid]
    dim = model.sensor_dim[sid]
    if dim == 1:
        return float(data.sensordata[adr])
    return np.array(data.sensordata[adr:adr + dim]).copy()

def set_ctrl(name, value):
    data.ctrl[actuator_id[name]] = float(value)

def set_joint_ctrl(q_target):
    for i, an in enumerate(JOINT_NAMES):
        data.ctrl[actuator_id[ACTUATOR_NAMES[i]]] = float(q_target[i])

def reset_home():
    data.qpos[:] = 0.0
    data.qvel[:] = 0.0
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)

def open_gripper():
    set_ctrl("finger1_ctrl", 0.025)
    set_ctrl("finger2_ctrl", 0.025)

def close_gripper():
    set_ctrl("finger1_ctrl", 0.0)
    set_ctrl("finger2_ctrl", 0.0)

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
    data.ctrl[:6] = q_target
    for i in range(max_steps):
        mujoco.mj_step(model, data)
        joint_error = np.linalg.norm(q_target - data.qpos[:6])
        if joint_error < joint_tol:
            print(f"Joint Converged in {i} steps")
            break
    return data.qpos[:6].copy()

def get_tcp():
    return data.site_xpos[ee_site_id].copy()

def get_cube_pos():
    return data.site_xpos[cube_site_id].copy()

def print_gripper_state(tag=""):
    f1 = data.qpos[joint_qposadr["joint_finger1"]]
    f2 = data.qpos[joint_qposadr["joint_finger2"]]
    t1 = get_sensor_scalar(model, data, "finger1_touch")
    t2 = get_sensor_scalar(model, data, "finger2_touch")
    print(f"\n--- {tag} ---")
    print("finger1 qpos :", f1)
    print("finger2 qpos :", f2)
    print("finger1 touch:", t1)
    print("finger2 touch:", t2)

def validate_gripper(viewer_sync=False):
    print("\n==============================")
    print("Gripper Validation Start")
    print("==============================")
    reset_home()
    open_gripper()
    step_n(3000)
    print_gripper_state("GRIPPER OPEN")
    if viewer_sync:
        pass
    close_gripper()
    step_n(3000)
    print_gripper_state("GRIPPER CLOSE")
    open_gripper()
    step_n(2000)
    print_gripper_state("GRIPPER RE-OPEN")

def first_pick_test():
    print("\n==============================")
    print("First Pick Test Start")
    print("==============================")
    reset_home()
    open_gripper()
    step_n(2000)
    cube_pos = get_cube_pos()
    print("\nCube Pos:", cube_pos)
    approach_pos = cube_pos + np.array([0.0, 0.0, 0.15])
    pick_pos = cube_pos + np.array([0.0, 0.0, 0.04])
    print("Approach Pos:", approach_pos)
    print("Pick Pos:", pick_pos)
    q_approach = solve_ik(model, data, approach_pos)
    print("\nApproach Joint Target:", np.round(q_approach, 3))
    reset_home()
    move_to_joint_target(q_approach)
    step_n(2000)
    print("\nTCP at Approach:", get_tcp())
    q_pick = solve_ik(model, data, pick_pos)
    print("\nPick Joint Target:", np.round(q_pick, 3))
    move_to_joint_target(q_pick)
    step_n(1000)
    print("\nTCP at Pick:", get_tcp())
    print_gripper_state("BEFORE CLOSE")
    close_gripper()
    step_n(3000)
    print_gripper_state("AFTER CLOSE")
    lifted_pos = cube_pos + np.array([0.0, 0.0, 0.15])
    q_lift = solve_ik(model, data, lifted_pos)
    print("\nLift Joint Target:", np.round(q_lift, 3))
    move_to_joint_target(q_lift)
    step_n(2000)
    print("\nTCP after Lift:", get_tcp())
    print("Cube after Lift:", get_cube_pos())
    print("\n=== Pick Test Result ===")
    print("Target TCP :", pick_pos)
    print("Actual TCP :", get_tcp())
    print("TCP Error  :", np.linalg.norm(pick_pos - get_tcp()))
    print("Cube Z     :", get_cube_pos()[2])

with mujoco.viewer.launch_passive(model, data) as viewer:
    # validate_gripper()
    # first_pick_test()
    
    mujoco.mj_forward(model, data)

    cube_body_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_BODY,
        "cube"
    )

    cube_site_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_SITE,
        "cube_site"
    )

    print("cube_body_id =", cube_body_id)
    print("cube_site_id =", cube_site_id)

    print("cube body =", data.xpos[cube_body_id])
    print("cube site =", data.site_xpos[cube_site_id])

    print("cube qpos =", data.qpos[-7:])
    
    
        
    cube_pos = data.site_xpos[cube_site_id].copy()
    target = cube_pos + np.array([0,0,0.12])
    q = solve_ik(
        model,
        data,
        target
    )

    data.qpos[:6] = q
    mujoco.mj_forward(model,data)
    actual = data.site_xpos[ee_site_id]

    print("target =", target)
    print("actual =", actual)
    print("error  =", np.linalg.norm(target-actual))
    print("q =", np.round(q,3))
    
    
    while viewer.is_running():
        
        mujoco.mj_step(model, data)
        
        
        
        viewer.sync()
        time.sleep(0.01)