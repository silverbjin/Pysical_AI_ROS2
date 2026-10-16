import mujoco
import mujoco.viewer
import numpy as np

model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/my_robot_6D.xml")
data = mujoco.MjData(model)

for i in range(model.nsensor):
    print(i, mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_SENSOR, i))

# control_period = 0.05        # 50 ms
control_period = 0.005        # 5 ms
physics_dt = model.opt.timestep

steps_per_control = int(control_period / physics_dt)

sim_time = 0.0
control_count = 0

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        # 50ms마다 새로운 목표 생성
        if control_count % steps_per_control == 0:
            target = np.zeros(model.nu)

            target[0] = 0.5 * np.sin(0.2 * sim_time)
            target[1] = 0.5 * np.sin(0.3 * sim_time)
            target[2] = 0.5 * np.sin(0.4 * sim_time)
            target[3] = 0.3 * np.sin(0.5 * sim_time)
            target[4] = 0.3 * np.sin(0.6 * sim_time)
            target[5] = 0.3 * np.sin(0.7 * sim_time)

            data.ctrl[:] = target

            # print(
            #     f"[t={sim_time:6.2f}] "
            #     f"ctrl={np.round(data.ctrl[:6],3)} "
            #     f"qpos={np.round(data.qpos[:6],3)}"
            # )

        mujoco.mj_step(model, data)

        viewer.sync()

        sim_time += physics_dt
        control_count += 1