"""Read-only model audit and freeze measured footprint before Nav2 runs."""
from pathlib import Path
import json,sys,unittest
root=Path(__file__).resolve().parents[3];sys.path.insert(0,str(root/'Ch13/ros2_ws/src/ch13_navigation_reuse'))
import mujoco,numpy as np
from ch13_navigation_reuse.scene import make_model,footprint
suite=unittest.defaultTestLoader.discover(str(root/'Ch13/ros2_ws/src/ch13_navigation_reuse/test'),pattern='test_scene_sensor.py');result=unittest.TextTestRunner(verbosity=2).run(suite);assert result.wasSuccessful()
m=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','free')
source=root/'Ch13/evidence/section_13_5_reuse/b5c33be2-25f1-4c2b-8f74-2ad1706840ec/engine_observations.jsonl';rows=[json.loads(x) for x in source.read_text().splitlines()];fp=footprint(m,[x['qpos'] for x in rows[::10]])
p=root/'Ch13/ros2_ws/src/ch13_navigation_reuse/config/footprint.json';p.write_text(json.dumps({'source':str(source.relative_to(root)),'samples':len(rows[::10]),'margin_m':.04,'footprint':fp,'profile':'measured R2 walking/turning/home-hold; not arbitrary arm motion'},indent=2)+'\n')
print('FROZEN_FOOTPRINT',fp)
