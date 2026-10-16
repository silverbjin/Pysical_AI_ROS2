import time
import numpy as np
import mujoco
import mujoco.viewer

XML_PATH = "src/my_robot_description/urdf/my_robot_6D.xml"

EE_SITE = "grasp_site"
CUBE_SITE = "cube_site"

# LOCK_JOINT = 4
# LOCK_VALUE = -np.pi / 2.0

model = mujoco.MjModel.from_xml_path(XML_PATH)
data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
cube_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, CUBE_SITE)

def get_tcp():
    return data.site_xpos[ee_site_id].copy()

def get_cube():
    return data.site_xpos[cube_site_id].copy()

def step_sim(n=500, viewer=None):
    for _ in range(n):
        mujoco.mj_step(model, data)
        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

def open_gripper(viewer=None):
    # data.ctrl[6] = 0.0225
    # data.ctrl[7] = 0.0225
    data.ctrl[6] = 0.0
    data.ctrl[7] = 0.0

    step_sim(2000, viewer)

def close_gripper(viewer=None):
    # data.ctrl[6] = 0.0
    # data.ctrl[7] = 0.0
    data.ctrl[6] = 0.0225
    data.ctrl[7] = 0.0225

    step_sim(3000, viewer)
    
def solve_ik(target_pos,max_iter=300,damping=0.05,alpha=0.5,pos_tol=1e-3,rot_tol=1e-2):
    q=data.qpos[:6].copy()
    q_min=model.jnt_range[:6,0].copy()
    q_max=model.jnt_range[:6,1].copy()
    free_idx=[0,1,2,3,4,5]
    jacp=np.zeros((3,model.nv))
    jacr=np.zeros((3,model.nv))
    desired_z=np.array([0.0,0.0,-1.0])

    for i in range(max_iter):
        data.qpos[:6]=q
        mujoco.mj_forward(model,data)
        current_pos=get_tcp()
        pos_error=target_pos-current_pos
        R=data.site_xmat[ee_site_id].reshape(3,3)
        current_z=R[:,2]
        rot_error=np.cross(current_z,desired_z)

        if np.linalg.norm(pos_error)<pos_tol and np.linalg.norm(rot_error)<rot_tol:
            print(f"IK Converged in {i} iterations")
            return q

        mujoco.mj_jacSite(model,data,jacp,jacr,ee_site_id)
        J_pos=jacp[:,free_idx]
        J_rot=jacr[:,free_idx]
        J=np.vstack((J_pos,J_rot))
        # error=np.concatenate((pos_error,0.5*rot_error))
        error=np.concatenate((pos_error,1.0*rot_error))
        dq=J.T@np.linalg.inv(J@J.T+damping*np.eye(6))@error
        q+=alpha*dq
        q=np.clip(q,q_min,q_max)

    print("IK Failed")
    return q
    
def move_to_joint_target(q_target, viewer=None, max_steps=15000, joint_tol=1e-3):
    q_target = q_target.copy()
    # q_target[LOCK_JOINT] = LOCK_VALUE
    data.ctrl[:6] = q_target
    for i in range(max_steps):
        # data.ctrl[LOCK_JOINT] = LOCK_VALUE
        mujoco.mj_step(model, data)
        if viewer is not None:
            viewer.sync()
            time.sleep(0.001)

        err = np.linalg.norm(q_target - data.qpos[:6])
        if err < joint_tol:
            print(f"Joint Converged in {i} steps")
            break
                
def print_pick_frame_info():
    tool0_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "tool0")
    gripper_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "gripper_base")
    finger1_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger1")
    finger2_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "finger2")

    print("\n==============================")
    print("Pick Pose Frame Info")
    print("==============================")

    print("ee_site      =", np.round(get_tcp(), 6))
    print("tool0        =", np.round(data.xpos[tool0_id], 6))
    print("gripper_base =", np.round(data.xpos[gripper_id], 6))
    print("finger1      =", np.round(data.xpos[finger1_id], 6))
    print("finger2      =", np.round(data.xpos[finger2_id], 6))
    print("\nCube")

    print("cube         =", np.round(get_cube(), 6))
    print("cube-ee_site =", np.round(get_cube() - get_tcp(), 6))

def print_ee_orientation():
    R=data.site_xmat[ee_site_id].reshape(3,3)
    print("\nEE Orientation")
    print("X =",np.round(R[:,0],3))
    print("Y =",np.round(R[:,1],3))
    print("Z =",np.round(R[:,2],3))

    
mujoco.mj_forward(model, data)
cube_pos = get_cube()
approach_pos = (cube_pos + np.array([0.0, 0.0, 0.18]))
# pick_pos = (cube_pos + np.array([0.0, 0.0, 0.05]))
pick_pos = (cube_pos + np.array([0.0, 0.0, 0.02]))
lift_pos = (cube_pos + np.array([0.0, 0.0, 0.20]))

print("\n==============================")
print("Pick Test Start")
print("==============================")

print("Cube Pos:", cube_pos)
print("Approach Pos:", approach_pos)
print("Pick Pos:", pick_pos)
print("Lift Pos:", lift_pos)

with mujoco.viewer.launch_passive(model, data) as viewer:
    viewer.sync()
    input( "\nENTER : Initial State")

    open_gripper(viewer)
    
    print("f1 =", data.qpos[6])
    print("f2 =", data.qpos[7])

    input("\nENTER : Open 확인")

    q_approach = solve_ik(approach_pos)

    move_to_joint_target(q_approach, viewer)
    viewer.sync()

    print("\nTCP at Approach:", np.round(get_tcp(), 6))
    input("\nENTER : Approach 확인")

    q_pick = solve_ik(pick_pos)

    move_to_joint_target(q_pick, viewer)
    viewer.sync()
    print_pick_frame_info()

    # while viewer.is_running():
    #     viewer.sync()
    #     time.sleep(0.01)
    
    print_ee_orientation()
    
    print("\nTCP at Pick:", np.round(get_tcp(), 6))
    print_pick_frame_info()

    input("\nENTER : Pick 자세 확인")
    
    close_gripper(viewer)
    viewer.sync()

    input("\nENTER : Close 결과 확인")

    q_lift = solve_ik(lift_pos)

    move_to_joint_target(q_lift, viewer)
    viewer.sync()

    input("\nENTER : Lift 결과 확인")
           
