#!/usr/bin/env python3
"""Independent Ch08 §8.6 CI artifact auditor: do not repeat training."""
import hashlib
import json
import math
from pathlib import Path
import sys

assert len(sys.argv)==2, "usage: verify.py <isolated-run-directory>"
run=Path(sys.argv[1])
d=json.loads((run/"receipt.json").read_text(encoding="utf-8"))
assert d["chapter"]=="Ch08" and d["section"]=="8.6"
assert d["status"]=="SCOPED_PASS" and d["mode"]=="smoke"
assert d["timesteps_requested"]==256 and d["timesteps_observed"]>=256
assert 0<d["max_policy_weight_delta"]<100 and math.isfinite(d["max_policy_weight_delta"])
assert d["environment_observation_shape"]==[18]
assert d["environment_action_shape"]==[6]
archive=Path(d["model_zip"])
assert archive.parent.resolve()==run.resolve()
assert archive.is_file() and archive.stat().st_size==d["model_zip_bytes"]
assert archive.stat().st_size>1024
h=hashlib.sha256(archive.read_bytes()).hexdigest()
assert h==d["model_zip_sha256"]
assert len(d["xml_sha256"])==64
events=list((run/"tb").rglob("events.out.tfevents.*"))
assert events and len(events)==d["tensorboard_event_files"]
assert any(e.stat().st_size>128 for e in events)
assert d["policy_quality_and_convergence"]==d["long_training_goal_success"]=="NOT_RUN"
assert d["rgb_video"]==d["real_robot"]=="NOT_RUN"
assert d["ch10"]=="HOLD"
print("CH08_86_INDEPENDENT_SHA_AND_PPO_MODEL_GRADIENT_EVENT_RECEIPT_PASS",flush=True)
