#!/usr/bin/env python3
"""Independent Ch08 8.7 evidence audit; no model retraining or extra evaluation."""
import hashlib
import json
import math
from pathlib import Path
import sys

assert len(sys.argv)==3
receipt=Path(sys.argv[1])
model=Path(sys.argv[2])
d=json.loads(receipt.read_text(encoding="utf-8"))
assert d["chapter"]=="Ch08" and d["section"]=="8.7"
assert d["scope"]=="deterministic_existing_policy_true_distance_metrics"
assert d["status"]=="SCOPED_PASS"
assert model.is_file()
assert hashlib.sha256(model.read_bytes()).hexdigest()==d["model_zip_sha256"]
m=d["metrics"];e=m["individual_episodes"]
assert m["episode_count"]==10 and len(e)==10
assert m["seed_start"]==1000 and m["max_steps"]==300
assert m["success_count"]==sum(bool(x["success"]) for x in e)
assert abs(m["success_rate_pct"]-m["success_count"]*10.0)<1e-9
assert abs(m["mean_final_distance_m"]-sum(x["final_distance_m"] for x in e)/10)<1e-8
for x in e:
    assert 1<=x["steps"]<=300
    assert x["reason"] in ("SUCCESS","STEP_LIMIT","TRUNCATED","TERMINATED")
    assert x["success"]==(x["reason"]=="SUCCESS")
    assert all(math.isfinite(float(x[key])) for key in
               ("final_distance_m","episode_return","mean_action_delta"))
    assert x["final_distance_m"]>=0
    assert (not x["success"]) or x["final_distance_m"]<0.05
assert d["training_history_claim"]==d["real_robot"]==d["rgb_video"]=="NOT_RUN"
assert d["ch10"]=="HOLD"
print("CH08_87_INDEPENDENT_ACTUAL_10_EPISODE_TRUE_DISTANCE_RECEIPT_PASS",flush=True)
