bash Ch13/scripts/reuse_13_5/env_r2.sh - <<'PY_IK'
from pathlib import Path
import mujoco
from ch13_navigation_reuse.scene import make_model
from ch13_navigation_reuse.approach_geometry import arm_reach, tcp, position_ik
root = Path.cwd()
m = make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml', 'vision')
q = m.key_qpos[m.key('home').id].copy()
d = mujoco.MjData(m); d.qpos[:] = q; mujoco.mj_forward(m, d)
length = arm_reach(m, q)
answer = position_ik(m, q, tcp(m, d))
print('chain length m:', length)
print('distance candidates m:', [length-x for x in [.15, .25, .35]])
print('FK target IK:', answer)
assert answer is not None and answer['collision_free']
PY_IK
bash Ch13/scripts/reuse_13_5/env_r2.sh -m unittest discover \
  -s "$REUSE_PKG/test" -p test_approach_geometry.py -v
