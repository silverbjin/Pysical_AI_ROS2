#!/usr/bin/env bash
set -e
cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
bash .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/inspect-test-numeric-threads.sh
source .superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/env-native.sh
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
python - <<'PY'
import json,hashlib,uuid,os,numpy as np
from pathlib import Path
from integrated_robot_navigation.model import compile_model
from integrated_robot_navigation.native_mass import NativeMassEvaluator
from integrated_robot_navigation.native_xyz import NativeXYZTransition
file=Path('Ch13/ros2_ws/src/integrated_robot_navigation/test/fixtures/native_76b_xyz_unload.json')
data=json.loads(file.read_text());model=compile_model(data['urdf']);args=data['args'];records={}
with NativeMassEvaluator(model) as core:
 for objective in ('rate_1_per_s','bounded_terminal_force'):
  kernel=NativeXYZTransition(model,data['limits'],terms_evaluator=core.contact_terms,force_objective=objective)
  try:
   kernel.prepare();delta=kernel.step(**args)
   records[objective]=dict(model=kernel.last_model,delta=delta,timing=kernel.last_attempt,
     optimizer=kernel._optimizer.provenance,
     maximum_requested_speed_mps=max(np.linalg.norm(v) for v in delta.values())/args['dt'])
  finally:kernel.close()
base=Path(os.environ['CH13_NAV_EVIDENCE']);out=base/f'task8-terminal-force-comparison-{uuid.uuid4()}.json'
result=dict(scope='one_closed_failure_input_no_engine_or_physical_success',fixture_sha256=hashlib.sha256(file.read_bytes()).hexdigest(),
 records=records,existing_force_n=args['forces_world'][args['foot']][2])
out.write_text(json.dumps(result,indent=2)+'\n');out.with_suffix('.method.sh').write_bytes(Path('.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/terminal-force-diagnostic.sh').read_bytes())
print(out)
print(json.dumps({k:dict(predicted_selected_normal_n=v['model']['predicted_forces_world'][args['foot']][2],
 selected_delta_z_m=v['delta'][args['foot']][2],maximum_requested_speed_mps=v['maximum_requested_speed_mps'],
 compute_wall_ns=v['model']['compute_wall_ns']) for k,v in records.items()},indent=2))
PY
