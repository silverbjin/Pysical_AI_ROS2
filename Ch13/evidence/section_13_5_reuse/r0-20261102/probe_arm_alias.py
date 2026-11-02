import ast,json,sys
from pathlib import Path
from types import SimpleNamespace
import mujoco,numpy as np
here=Path(__file__).resolve().parent
root=here.parents[3];up=root.parent/'upstream-iit-locomanipulation-d010212'
parsed=ast.parse((up/'deploy/play_mujoco.py').read_text())
node=next(n for n in ast.walk(parsed) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Attribute) and t.attr=='desired_joint_pos_arm' for t in n.targets))
model=mujoco.MjModel.from_xml_path(str(up/'robot_model/scene_rough.xml'))
data=mujoco.MjData(model);data.qpos[:]=model.key_qpos[0]
platform=SimpleNamespace(mjData=data)
exec(compile(ast.Module(body=[node],type_ignores=[]),'original_arm_assignment','exec'),{'self':platform})
before=float(platform.desired_joint_pos_arm[0]);shares=np.shares_memory(platform.desired_joint_pos_arm,data.qpos)
data.qpos[19]=0.125
after=float(platform.desired_joint_pos_arm[0])
sys.path.insert(0,str(root/'Ch13/scripts/reuse_13_5'))
from reproduce_upstream import freeze_arm_reference
freeze_arm_reference(platform);data.qpos[19]=0.25
proof={'original_source_line':node.lineno,'original_shares_qpos':bool(shares),'target_before':before,'target_after_engine_state_write':after,'snapshot_target_after_second_state_write':float(platform.desired_joint_pos_arm[0]),'engine_state_after_second_write':float(data.qpos[19])}
(here/'arm_alias_proof.json').write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps(proof,indent=2))
assert shares and before==0 and after==0.125 and platform.desired_joint_pos_arm[0]==.125 and data.qpos[19]==.25
