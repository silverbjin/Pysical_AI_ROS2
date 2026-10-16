import mujoco
import mujoco.viewer
import numpy as np

model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/my_robot_6D.xml")
data = mujoco.MjData(model)

control_period = 0.05
steps_per_control = int(control_period / model.opt.timestep)

sim_time = 0.0
control_count = 0

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        if control_count % steps_per_control == 0:
            target = np.zeros(model.nu)

            # arm 고정
            target[:6] = 0.0

            # gripper open ↔ close 반복
            # grip = 0.0125 + 0.0125*np.sin(0.5*sim_time)
            
            # RL용 더 테스트: Arm = Action[0:6] + Gripper = Action[6] 구조
            gripper_action = np.sin(0.5*sim_time)
            grip = 0.0125*(gripper_action + 1.0)

            target[6] = grip
            target[7] = grip

            data.ctrl[:] = target

            ee_pos = data.sensor("ee_pos").data.copy()
            ee_vel = data.sensor("ee_linvel").data.copy()

            touch1 = float(data.sensor("finger1_touch").data[0])
            touch2 = float(data.sensor("finger2_touch").data[0])

            print(
                f"[t={sim_time:6.2f}] "
                f"grip={grip:.4f} "
                f"f1={data.qpos[6]:.4f} "
                f"f2={data.qpos[7]:.4f} "
                f"touch=({touch1:.3f},{touch2:.3f}) "
                f"ee=({ee_pos[0]:.3f},{ee_pos[1]:.3f},{ee_pos[2]:.3f})"
            )

        mujoco.mj_step(model, data)

        viewer.sync()

        sim_time += model.opt.timestep
        control_count += 1