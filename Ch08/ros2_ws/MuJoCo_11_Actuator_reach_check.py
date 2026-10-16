import numpy as np
import mujoco

EE_SITE = "ee_site"

model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/my_robot_6D.xml")
data = mujoco.MjData(model)

site_id = mujoco.mj_name2id(
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


def reset_home(model, data):
    data.qpos[:] = 0.0
    data.qvel[:] = 0.0
    data.ctrl[:] = 0.0
    mujoco.mj_forward(model, data)


def move_to_joint_target(model, data, q_target, max_steps=15000, joint_tol=1e-3):
    data.ctrl[:6] = q_target
    for i in range(max_steps):
        mujoco.mj_step(model, data)
        joint_error = np.linalg.norm(q_target - data.qpos[:6])

        if joint_error < joint_tol:
            print(f"Joint Converged in {i} steps")
            break

    return data.qpos[:6].copy()


def reach_test(model, data, target_pos):
    print("\n==============================")
    print("Reach Test Start")
    print("==============================")

    # ----------------------------------
    # 1. Home Pose
    # ----------------------------------

    reset_home(model, data)

    home_pos = data.site_xpos[site_id].copy()

    print("\nHome TCP")
    print(home_pos)

    # ----------------------------------
    # 2. IK 계산
    # ----------------------------------

    q_target = solve_ik(model, data, target_pos)

    print("\nIK Solution")
    print(np.round(q_target, 3))

    # ----------------------------------
    # 3. 다시 Home 복귀
    # ----------------------------------

    reset_home(model, data)

    # ----------------------------------
    # 4. 실제 Actuator 이동
    # ----------------------------------

    q_actual = move_to_joint_target(model, data, q_target)

    # ----------------------------------
    # 5. 결과 측정
    # ----------------------------------

    actual_tcp = data.site_xpos[site_id].copy()
    tcp_error = np.linalg.norm(target_pos - actual_tcp)
    joint_error = np.linalg.norm(q_target - q_actual)

    print("\n=== Reach Test Result ===")

    print("\nTarget TCP")
    print(target_pos)

    print("\nActual TCP")
    print(actual_tcp)

    print("\nTCP Error")
    print(tcp_error)

    print("\nTarget Joint")
    print(np.round(q_target, 3))

    print("\nActual Joint")
    print(np.round(q_actual, 3))

    print("\nJoint Error")
    print(joint_error)

    return tcp_error


# ============================
# TEST
# ============================

target = np.array([-1.0, 0.0, 0.15])
error = reach_test(model, data, target)
print("\nFinal TCP Error =", error)