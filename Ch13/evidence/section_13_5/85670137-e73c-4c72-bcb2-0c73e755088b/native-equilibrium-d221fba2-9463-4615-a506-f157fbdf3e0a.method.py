import json,hashlib,uuid
from pathlib import Path
import numpy as np
from integrated_robot_navigation.native_equilibrium import NativeEquilibrium
repo=Path('/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2')
n=repo/'Ch13/ros2_ws/src/integrated_robot_navigation';f=json.loads((n/'test/fixtures/discrete_equilibrium_baseline.json').read_bytes())
with NativeEquilibrium(f['urdf']) as core:
 r=core.evaluate(joints=f['joints'],body_pose=f['body_pose'],command_joints=f['command_joints'],forces=f['forces_world_flat'])
 out={k:float(v) for k,v in r.items() if not isinstance(v,np.ndarray)}
 out.update(scope='native full derivative vs independent oracle; not runtime or G1/C1',max_derivative_error=float(np.max(np.abs(r['force_derivative']-f['expected_force_derivative']))),provenance=core.provenance,method_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
b=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b';p=b/('native-equilibrium-'+str(uuid.uuid4())+'.json');p.write_text(json.dumps(out,indent=2));p.with_suffix('.method.py').write_bytes(Path(__file__).read_bytes());print(json.dumps(out,indent=2))
