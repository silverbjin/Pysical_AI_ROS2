#!/usr/bin/env python3
"""Ch08 §8.8 offline numeric action guard test. No ROS or robot actuation."""
import json
import math
import os
from pathlib import Path
import sys

import numpy as np

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/"Ch08/ros2_ws"))
from policy_safety_filter import PolicyActionGuard,PolicyActionBlocked


def blocked(guard, action, age, code, estop=False):
    before=guard.previous.copy()
    try:
        guard.apply(action,age,estop=estop)
    except PolicyActionBlocked as exc:
        if code not in str(exc):
            raise AssertionError(f"wrong gate {exc}, expected {code}")
        if not estop and not np.array_equal(guard.previous,before):
            raise AssertionError("rejected command changed previous output")
        return
    raise AssertionError("an unsafe action was accepted")


guard=PolicyActionGuard(dof=6,alpha=0.2,max_age_sec=0.25)
raw1=np.array([2.,-2.,0.5,0.,0.,0.])
a=guard.apply(raw1,0.01)
assert np.allclose(a.clipped,[1.,-1.,.5,0,0,0])
assert np.allclose(a.filtered,[.2,-.2,.1,0,0,0])
assert np.all(np.abs(a.filtered)<=1.)
assert a.normalized_only
print("CH08_88_ACTUAL_CLIP_AND_EMA_PASS",flush=True)

raw2=np.array([-2.,2.,0.,0.,0.,0.])
b=guard.apply(raw2,0.20)
assert np.allclose(b.filtered,[-.04,.04,.08,0,0,0])
assert np.all(np.abs(b.filtered)<=1.)
print("CH08_88_BOUNDED_SECOND_STEP_STATE_PASS",flush=True)

blocked(guard,[0]*5,0.01,"DIMENSION")
blocked(guard,[0]*7,0.01,"DIMENSION")
blocked(guard,np.array([np.nan,0,0,0,0,0]),0.01,"NAN_INF")
blocked(guard,np.array([np.inf,0,0,0,0,0]),0.01,"NAN_INF")
blocked(guard,np.ones(6),0.26,"STALE")
blocked(guard,np.ones(6),-0.01,"STALE")
blocked(guard,np.ones(6),float("nan"),"STALE")
blocked(guard,["x"]*6,.05,"NOT_NUMERIC")
print("CH08_88_EIGHT_INVALID_INPUTS_FAIL_CLOSED_PASS",flush=True)

blocked(guard,np.zeros(6),.01,"SOFTWARE_ESTOP",estop=True)
blocked(guard,np.zeros(6),.01,"ESTOP_STILL_LATCHED")
try:
    guard.reset()
except PolicyActionBlocked as exc:
    assert "EXPLICIT_CLEAR" in str(exc)
else:
    raise AssertionError("E-stop unlatched without explicit clear")
guard.reset(operator_cleared_estop=True)
assert np.array_equal(guard.previous,np.zeros(6))
assert np.allclose(guard.apply(np.ones(6),0.01).filtered,np.full(6,.2))
print("CH08_88_ESTOP_LATCH_AND_EXPLICIT_CLEAR_PASS",flush=True)

evidence={
    "chapter":"Ch08","section":"8.8","status":"SCOPED_PASS",
    "scope":"offline_normalized_policy_action_guard_only",
    "source_sha":os.environ.get("RUN_SOURCE_SHA","LOCAL_UNPINNED"),
    "action_dimension":6,"alpha":0.2,"max_age_sec":0.25,
    "first_filtered":a.filtered.tolist(),"second_filtered":b.filtered.tolist(),
    "invalid_input_cases":8,
    "estop_latched_and_cleared":True,
    "all_outputs_normalized":True,
    "ros_position_units_mapping":"NOT_RUN",
    "ros_topic_publish":"NOT_RUN",
    "mujoco_to_ros_interface":"NOT_RUN",
    "hardware_estop":"NOT_RUN","hardware":"NOT_RUN",
    "ch10":"HOLD",
}
path=root/"ci-results/ch08-88/result.json"
path.parent.mkdir(parents=True,exist_ok=True)
path.write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
print("CH08_88_INDEPENDENT_OFFLINE_ACTION_GUARD_SCOPED_PASS_NO_ROS",flush=True)
