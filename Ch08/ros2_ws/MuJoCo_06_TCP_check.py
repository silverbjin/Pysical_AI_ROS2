import time
import numpy as np
import mujoco
import mujoco.viewer

model = mujoco.MjModel.from_xml_path(
    "src/my_robot_description/urdf/my_robot_6D.xml"
)

data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_SITE,
    "ee_site"
)


def print_state(joint_id):

    ee_pos = data.site_xpos[ee_site_id]

    # qpos = np.array(data.qpos[:6])

    # print(
    #     f"joint={joint_id+1} "
    #     f"ee=({ee_pos[0]:.3f}, {ee_pos[1]:.3f}, {ee_pos[2]:.3f}) "
    #     f"qpos={np.round(qpos,3)}"
    # )
    
    print(
        f"joint={joint_id+1} "
        f"x={ee_pos[0]:.3f} "
        f"y={ee_pos[1]:.3f} "
        f"z={ee_pos[2]:.3f}"
    )


def run_for_seconds(viewer,
                    target,
                    duration_sec=3.0,
                    log_period=0.05,
                    joint_id=0):

    next_log = time.time()

    start_time = time.time()

    while viewer.is_running():

        now = time.time()

        if now - start_time >= duration_sec:
            break

        data.ctrl[:] = target

        mujoco.mj_step(model, data)

        if now >= next_log:

            print_state(joint_id)

            next_log += log_period

        viewer.sync()


with mujoco.viewer.launch_passive(model, data) as viewer:

    print("\n============================")
    print(" Joint Sweep Test Start")
    print("============================\n")

    for joint_id in range(6):

        print(f"\n######## Joint {joint_id+1} ########")

        # +0.5 rad
        target = np.zeros(model.nu)
        target[joint_id] = 0.5
        print("Move -> +0.5 rad")
        run_for_seconds(
            viewer,
            target,
            duration_sec=3.0,
            joint_id=joint_id
        )

        # -0.5 rad
        target = np.zeros(model.nu)
        target[joint_id] = -0.5
        print("Move -> -0.5 rad")
        run_for_seconds(
            viewer,
            target,
            duration_sec=3.0,
            joint_id=joint_id
        )

        # return zero
        target = np.zeros(model.nu)
        print("Return -> 0 rad")
        run_for_seconds(
            viewer,
            target,
            duration_sec=2.0,
            joint_id=joint_id
        )

    print("\n============================")
    print(" Joint Sweep Test Done")
    print("============================")

    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()