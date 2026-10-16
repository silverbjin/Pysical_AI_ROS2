import time
import numpy as np
import mujoco
import mujoco.viewer

EE_SITE = "ee_site"

model = mujoco.MjModel.from_xml_path(
    "src/my_robot_description/urdf/my_robot_6D.xml"
)

data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_SITE,
    EE_SITE
)

def get_ee_pos(model, data):
    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)
    return data.site_xpos[site_id].copy()

def solve_ik(model, data, target_pos, max_iter=200, tol=0.01):

    site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, EE_SITE)

    jacp = np.zeros((3, model.nv))
    jacr = np.zeros((3, model.nv))

    q_backup = data.qpos.copy()

    for _ in range(max_iter):

        mujoco.mj_forward(model, data)

        current_pos = data.site_xpos[site_id].copy()

        error = target_pos - current_pos

        if np.linalg.norm(error) < tol:
            break

        mujoco.mj_jacSite(model, data, jacp, jacr, site_id)

        J = jacp[:, :6]

        damping = 1e-3

        dq = J.T @ np.linalg.inv(J @ J.T + damping * np.eye(3)) @ error

        data.qpos[:6] += 0.5 * dq

    q_solution = data.qpos[:6].copy()

    data.qpos[:] = q_backup

    mujoco.mj_forward(model, data)

    return q_solution

def move_to_target(model, data, viewer, target_q, duration=3.0):

    start_q = data.qpos[:6].copy()

    steps = int(duration / model.opt.timestep)

    for i in range(steps):

        alpha = (i + 1) / steps

        q = (1 - alpha) * start_q + alpha * target_q

        data.ctrl[:6] = q

        mujoco.mj_step(model, data)

        viewer.sync()
        


with mujoco.viewer.launch_passive(model, data) as viewer:

    print("\n============================")
    print(" IK 단독 및 결과 테스트 ")
    print("============================\n")
        
    # IK 단독 테스트        -1.0 0 0.015
    # target = np.array([0.6, 0.0, 0.3])
    target = np.array([-1.0, 0, 0.015])
    q_target = solve_ik(model, data, target)
    print("IK result =", np.round(q_target, 3))

    # IK 결과 확인
    data.ctrl[:6] = q_target
    for _ in range(3000):
        mujoco.mj_step(model, data)
        viewer.sync()

    ee = get_ee_pos(model, data)
    print("target =", target)
    print("actual =", ee)


    print("\n============================")
    print(" Pick 위치로 이동 테스트 ")
    print("============================\n")

    # Pick 위치로 이동 테스트
    # cube_pos = np.array([0.6, 0.0, 0.025])
    cube_pos = np.array([-1.0, 0, 0.015])

    pick_above = cube_pos + np.array([0.0, 0.0, 0.15])
    q_pick = solve_ik(model, data, pick_above)
    move_to_target(model, data, viewer, q_pick)
    
    
    print("\n============================")
    print(" Test Done")
    print("============================")

    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
    



# IK 단독 테스트        
target = np.array([0.6, 0.0, 0.3])
q_target = solve_ik(model, data, target)
print("IK result =", np.round(q_target, 3))


# IK 결과 확인
data.ctrl[:6] = q_target
for _ in range(3000):
    mujoco.mj_step(model, data)
    viewer.sync()

ee = get_ee_pos(model, data)
print("target =", target)
print("actual =", ee)


# Pick 위치로 이동 테스트
cube_pos = np.array([0.6, 0.0, 0.025])

pick_above = cube_pos + np.array([0.0, 0.0, 0.15])
q_pick = solve_ik(model, data, pick_above)
move_to_target(model, data, viewer, q_pick)