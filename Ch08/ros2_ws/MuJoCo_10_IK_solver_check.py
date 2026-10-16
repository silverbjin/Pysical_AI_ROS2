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


def solve_ik(
        model,
        data,
        target_pos,
        site_name="ee_site",
        max_iter=300,
        damping=0.05,
        alpha=0.5,
        tol=1e-3):

    site_id = mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_SITE,
        site_name
    )

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

        mujoco.mj_jacSite(
            model,
            data,
            jacp,
            jacr,
            site_id
        )

        J = jacp[:, :6]

        JT = J.T

        dq = JT @ np.linalg.inv(
            J @ JT +
            damping * np.eye(3)
        ) @ error

        q += alpha * dq

        q = np.clip(
            q,
            q_min,
            q_max
        )

    print("IK Failed")
    return q

target = np.array([-1.0, 0.0, 0.15])

q_sol = solve_ik(
    model,
    data,
    target
)


# IK 검증
data.qpos[:6] = q_sol
mujoco.mj_forward(model, data)

actual = data.site_xpos[
    mujoco.mj_name2id(
        model,
        mujoco.mjtObj.mjOBJ_SITE,
        "ee_site"
    )
]

print("\n=== IK Result ===")
print("target :", target)
print("actual :", actual)
print("error :", np.linalg.norm(target - actual))
print("joint :", np.round(q_sol, 3))


# 이동
def move_to_target(model, data, target_pos, steps=15000):
    q_target = solve_ik(model, data, target_pos)
    data.ctrl[:6] = q_target
    for i in range(steps):
        mujoco.mj_step(model, data)
        
        err = np.linalg.norm(q_target - data.qpos[:6])

        if err < 1e-4:
            print("Converged:", i)
            break
            
    return q_target

# Reach Test
target = np.array([-1.0, 0.0, 0.15])
q_target = move_to_target(model, data, target)

# 결과 출력
site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "ee_site")
actual = data.site_xpos[site_id]

print("\n=== Reach Test ===")
print("target :", target)
print("actual :", actual)
print("distance :", np.linalg.norm(target - actual))
print("tcp error  :", np.linalg.norm(target - actual))

print("target joint :", np.round(q_target, 3))
print("actual joint :", np.round(data.qpos[:6], 3))
print("joint error  :", np.round(q_target - data.qpos[:6], 4))

for i in range(10000):

    mujoco.mj_step(model, data)

    joint_error = np.linalg.norm(
        q_target - data.qpos[:6]
    )

    if joint_error < 1e-3:
        print(f"Reached in {i} steps")
        break
    
actual = data.site_xpos[site_id]
