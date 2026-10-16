import mujoco
import numpy as np

model = mujoco.MjModel.from_xml_path("src/my_robot_description/urdf/my_robot_6D.xml")
data = mujoco.MjData(model)

ee_site_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_SITE, "ee_site")

cube_pos = np.array([0.6, 0.0, 0.025])

workspace = []

joint1_range = np.linspace(-1.57, 1.57, 11)
joint2_range = np.linspace(-1.57, 1.57, 11)
joint3_range = np.linspace(-2.09, 2.09, 11)

sample_count = 0

for q1 in joint1_range:
    for q2 in joint2_range:
        for q3 in joint3_range:

            data.qpos[:] = 0

            data.qpos[0] = q1
            data.qpos[1] = q2
            data.qpos[2] = q3

            mujoco.mj_forward(model, data)

            p = data.site_xpos[ee_site_id].copy()

            workspace.append(p)

            sample_count += 1

workspace = np.array(workspace)

xmin = workspace[:,0].min()
xmax = workspace[:,0].max()

ymin = workspace[:,1].min()
ymax = workspace[:,1].max()

zmin = workspace[:,2].min()
zmax = workspace[:,2].max()

center = workspace.mean(axis=0)

dist = np.linalg.norm(workspace - cube_pos, axis=1)

nearest_idx = np.argmin(dist)

nearest = workspace[nearest_idx]

error = dist[nearest_idx]

reachable = error < 0.05

print()
print("==================================================")
print(" TCP WORKSPACE REPORT")
print("==================================================")
print()
print("Samples :", sample_count)
print()
print(f"X range : {xmin:.3f} ~ {xmax:.3f}")
print(f"Y range : {ymin:.3f} ~ {ymax:.3f}")
print(f"Z range : {zmin:.3f} ~ {zmax:.3f}")
print()
print("Workspace center")
print(f"x = {center[0]:.3f}")
print(f"y = {center[1]:.3f}")
print(f"z = {center[2]:.3f}")
print()
print("Cube position")
print(f"x = {cube_pos[0]:.3f}")
print(f"y = {cube_pos[1]:.3f}")
print(f"z = {cube_pos[2]:.3f}")
print()
print("Nearest reachable TCP")
print(f"x = {nearest[0]:.3f}")
print(f"y = {nearest[1]:.3f}")
print(f"z = {nearest[2]:.3f}")
print()
print(f"Distance = {error:.4f} m")
print()
print("Cube reachable =", reachable)
print()
print("==================================================")