import mujoco
import mujoco.viewer
import numpy as np
import time

model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/my_robot_6D.xml")
data = mujoco.MjData(model)

# Step 2. Joint axis 확인
print("************************** Joint list ***************************")
for i in range(model.njnt):
    print(
        model.joint(i).name,
        model.jnt_axis[i]
    )

# Step 3. Actuator 이름 확인
print("************************** Actuator list ***************************")
for i in range(model.nu):
    print(i, mujoco.mj_id2name(
        model,
        mujoco.mjtObj.mjOBJ_ACTUATOR,
        i
    ))

# Step 4. Sensor 이름 확인
print("************************** sensor list ***************************")
for i in range(model.nsensor):
    print(i, mujoco.mj_id2name(
        model, 
        mujoco.mjtObj.mjOBJ_SENSOR, 
        i
    ))

# Step 5. Read Sensor data: touch sensor
touch1_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_SENSOR,
    "finger1_touch"
)
touch2_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_SENSOR,
    "finger2_touch"
)
# contact query
for i in range(data.ncon):
    c = data.contact[i]

    geom1 = model.geom(c.geom1).name
    geom2 = model.geom(c.geom2).name

    print(geom1, geom2)


# mujoco.viewer.launch(model,data)
with mujoco.viewer.launch_passive(model, data) as viewer:

    last_print = time.time()

    # t=0
    while viewer.is_running():

    #     # joint test        
    #     for joint_id in range(6):
    #         target = np.zeros(model.nu)
    #         # target[joint_id] = np.deg2rad(45)
    #         target[joint_id] = 0.3*np.sin(t)
    #         t += 1
    #         for _ in range(1500):
    #             data.ctrl[:] = target
    #             mujoco.mj_step(model, data)
    #             viewer.sync()
            
        # default
        mujoco.mj_step(model, data)
        viewer.sync()
               
        
        
    