import time
import numpy as np
import mujoco
import mujoco.viewer

XML_PATH = "src/my_robot_description/urdf/my_robot_6D.xml"

# EE_SITE = "ee_site"
EE_SITE = "grasp_site"

CUBE_SITE = "cube_site"

LOCK_JOINT = 4
LOCK_VALUE = -np.pi / 2.0

model = mujoco.MjModel.from_xml_path(XML_PATH)
data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
cube_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, CUBE_SITE)

def get_tcp():
    return data.site_xpos[ee_site_id].copy()

def get_cube():
    return data.site_xpos[cube_site_id].copy()

def step_sim(n=500):
    for _ in range(n):
        mujoco.mj_step(model, data)
def step_sim(n=500,viewer=None):

    for _ in range(n):

        mujoco.mj_step(model,data)

        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

def open_gripper(viewer=None):
    data.ctrl[6] = 0.0225
    data.ctrl[7] = 0.0225
    step_sim(2000, viewer)

def close_gripper(viewer=None):
    data.ctrl[6] = 0.0
    data.ctrl[7] = 0.0
    step_sim(3000, viewer)

def solve_ik(target_pos,max_iter=300,damping=0.05,alpha=0.5,tol=1e-3):

    q = data.qpos[:6].copy()

    q_min = model.jnt_range[:6,0].copy()
    q_max = model.jnt_range[:6,1].copy()

    q[LOCK_JOINT] = LOCK_VALUE
    q_min[LOCK_JOINT] = LOCK_VALUE
    q_max[LOCK_JOINT] = LOCK_VALUE

    free_idx = [0,1,2,3,5]

    jacp = np.zeros((3,model.nv))
    jacr = np.zeros((3,model.nv))

    for i in range(max_iter):

        data.qpos[:6] = q
        data.qpos[LOCK_JOINT] = LOCK_VALUE

        mujoco.mj_forward(model,data)

        current = get_tcp()

        error = target_pos - current

        if np.linalg.norm(error) < tol:
            print(f"IK Converged in {i} iterations")
            return q

        mujoco.mj_jacSite(model,data,jacp,jacr,ee_site_id)

        J = jacp[:,free_idx]

        dq = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(3)) @ error

        q[free_idx] += alpha * dq

        q = np.clip(q,q_min,q_max)

        q[LOCK_JOINT] = LOCK_VALUE

    print("IK Failed")
    return q

def move_to_joint_target(q_target,max_steps=15000,joint_tol=1e-3):

    q_target = q_target.copy()

    q_target[LOCK_JOINT] = LOCK_VALUE

    data.ctrl[:6] = q_target

    for i in range(max_steps):

        data.ctrl[LOCK_JOINT] = LOCK_VALUE

        mujoco.mj_step(model,data)

        err = np.linalg.norm(q_target - data.qpos[:6])

        if err < joint_tol:
            print(f"Joint Converged in {i} steps")
            break

    return data.qpos[:6].copy()
def move_to_joint_target(q_target,max_steps=15000,joint_tol=1e-3,viewer=None):

    q_target = q_target.copy()

    q_target[LOCK_JOINT] = LOCK_VALUE

    data.ctrl[:6] = q_target

    for i in range(max_steps):

        data.ctrl[LOCK_JOINT] = LOCK_VALUE

        mujoco.mj_step(model,data)

        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

        err = np.linalg.norm(q_target-data.qpos[:6])

        if err < joint_tol:
            print(f"Joint Converged in {i} steps")
            break

# for grapping dubugging
def print_pick_frame_info():

    tool0_id = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"tool0")
    gripper_base_id = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"gripper_base")
    finger1_id = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"finger1")
    finger2_id = mujoco.mj_name2id(model,mujoco.mjtObj.mjOBJ_BODY,"finger2")

    print("\n==============================")
    print("Pick Pose Frame Info")
    print("==============================")

    print("ee_site      =",np.round(get_tcp(),6))
    print("tool0        =",np.round(data.xpos[tool0_id],6))
    print("gripper_base =",np.round(data.xpos[gripper_base_id],6))
    print("finger1      =",np.round(data.xpos[finger1_id],6))
    print("finger2      =",np.round(data.xpos[finger2_id],6))

    print("\nOffsets From ee_site")

    print(
        "tool0        =",
        np.round(
            data.xpos[tool0_id] - get_tcp(),
            6
        )
    )

    print(
        "gripper_base =",
        np.round(
            data.xpos[gripper_base_id] - get_tcp(),
            6
        )
    )

    print(
        "finger1      =",
        np.round(
            data.xpos[finger1_id] - get_tcp(),
            6
        )
    )

    print(
        "finger2      =",
        np.round(
            data.xpos[finger2_id] - get_tcp(),
            6
        )
    )

    print("\nCube")

    print(
        "cube         =",
        np.round(
            get_cube(),
            6
        )
    )

    print(
        "cube-ee_site =",
        np.round(
            get_cube() - get_tcp(),
            6
        )
    )



# Cube 좌표 check
mujoco.mj_forward(model,data)

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

print("cube body =", data.xpos[cube_body_id])
print("cube site =", data.site_xpos[cube_site_id])
print("cube qpos =", data.qpos[-7:])


# TCP와 집게 중심 사이 차이
tool_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_BODY,
    "tool0"
)

finger1_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_BODY,
    "finger1"
)

finger2_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_BODY,
    "finger2"
)

print("tool0   =", data.xpos[tool_id])
print("finger1 =", data.xpos[finger1_id])
print("finger2 =", data.xpos[finger2_id])



# finger info
finger1_geom_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_GEOM,
    "finger1_collision"
)
finger2_geom_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_GEOM,
    "finger2_collision"
)
print(
    "finger1_geom =",
    np.round(data.geom_xpos[finger1_geom_id],6)
)
print(
    "finger2_geom =",
    np.round(data.geom_xpos[finger2_geom_id],6)
)



with mujoco.viewer.launch_passive(model,data) as viewer:
    open_gripper()
    q_approach = solve_ik(approach_pos)
    move_to_joint_target(q_approach, viewer=viewer)
    print("\nTCP at Approach:",np.round(get_tcp(),6))
    input("\nENTER : Approach 확인")
    q_pick = solve_ik(pick_pos)
    move_to_joint_target(q_pick, viewer=viewer)
    print("\nTCP at Pick:",np.round(get_tcp(),6))
    print_pick_frame_info()
    input("\nENTER : Pick 자세 확인")
    close_gripper()
    input("\nENTER : Close 결과 확인")
    q_lift = solve_ik(lift_pos)
    move_to_joint_target(q_lift, viewer=viewer)
    input("\nENTER : Lift 결과 확인")


print("\n==============================")
print("Pick Test Start")
print("==============================")

cube_pos = get_cube()

approach_pos = cube_pos + np.array([0.0,0.0,0.18])
pick_pos = cube_pos + np.array([0.0,0.0,0.05])
# pick_pos = cube_pos + np.array([0.0,0.0,0.12])
lift_pos = cube_pos + np.array([0.0,0.0,0.20])

print("\nCube Pos:",cube_pos)
print("Approach Pos:",approach_pos)
print("Pick Pos:",pick_pos)
print("Lift Pos:",lift_pos)

open_gripper()

q_approach = solve_ik(approach_pos)

print("\nApproach Joint Target:",np.round(q_approach,3))

move_to_joint_target(q_approach)

print("\nTCP at Approach:",np.round(get_tcp(),6))

q_pick = solve_ik(pick_pos)

print("\nPick Joint Target:",np.round(q_pick,3))

move_to_joint_target(q_pick)

print("\nTCP at Pick:",np.round(get_tcp(),6))
# for grapping debug
print_pick_frame_info()



print("\n--- BEFORE CLOSE ---")
print("tcp :",np.round(get_tcp(),6))
print("cube :",np.round(get_cube(),6))
print("jpos :",np.round(data.qpos[:6],6))
print("f1 :",data.qpos[6])
print("f2 :",data.qpos[7])

close_gripper()

print("\n--- AFTER CLOSE ---")
print("tcp :",np.round(get_tcp(),6))
print("cube :",np.round(get_cube(),6))
print("jpos :",np.round(data.qpos[:6],6))
print("f1 :",data.qpos[6])
print("f2 :",data.qpos[7])

q_lift = solve_ik(lift_pos)

print("\nLift Joint Target:",np.round(q_lift,3))

move_to_joint_target(q_lift)

print("\nTCP after Lift:",np.round(get_tcp(),6))

final_tcp = get_tcp()
final_cube = get_cube()

print("\n=== Pick Test Result ===")
print("Target TCP :",pick_pos)
print("Actual TCP :",final_tcp)
print("TCP Error  :",np.linalg.norm(pick_pos-final_tcp))
print("Cube Pos   :",final_cube)
print("Cube Lift  :",final_cube[2])
print("Joint5     :",data.qpos[4])

if final_cube[2] > 0.03:
    print("\nPICK SUCCESS")
else:
    print("\nPICK FAILED")