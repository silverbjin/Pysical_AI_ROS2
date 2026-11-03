"""Read-only local dynamics diagnosis; no stepping, engine or model changes."""
import json
import sys
from pathlib import Path
import numpy as np
import mujoco
from ch13_navigation_reuse.scene import make_model

root=Path(__file__).resolve().parents[3]
model=make_model(root.parent/'upstream-iit-locomanipulation-d010212/robot_model/scene_rough.xml','vision')
data=mujoco.MjData(model)
record=json.loads(Path(sys.argv[1]).read_text())
rows=record['engine']['manipulation']['arm_observations']
last=record['engine']['actual_pose']
data.qpos[:]=model.key_qpos[model.key('home').id]
data.qpos[:7]=last
data.qpos[19:25]=rows[0]['q']
mujoco.mj_forward(model,data)
report=dict(q=rows[0]['q'],bias_Nm=data.qfrc_bias[18:24].tolist(),
            friction_Nm=model.dof_frictionloss[18:24].tolist(),
            predicted_uncompensated_bias_rad=(data.qfrc_bias[18:24]/50).tolist(),
            actual_excursion_rad=(np.ptp([r['q'] for r in rows],axis=0)).tolist(),
            actual_peak_tracking_error_rad=max(r['error'] for r in rows))
print(json.dumps(report,indent=2))
