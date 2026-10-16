import mujoco
import numpy as np

model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/my_robot_6D.xml")
data = mujoco.MjData(model)

mujoco.mj_forward(model, data)

# IDs
ee_site_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_SITE,
    "ee_site"
)

tool0_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_BODY,
    "tool0"
)

cube_id = mujoco.mj_name2id(
    model,
    mujoco.mjtObj.mjOBJ_BODY,
    "cube"
)

print("\n=== Frame Positions ===")
print("ee_site :", np.round(data.site_xpos[ee_site_id], 4))
print("tool0   :", np.round(data.xpos[tool0_id], 4))
print("cube    :", np.round(data.xpos[cube_id], 4))