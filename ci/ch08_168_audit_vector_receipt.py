#!/usr/bin/env python3
"""Independent OFFLINE audit: new real 3D EE vector receipts, no MuJoCo replay."""
import hashlib
import json
import math
from pathlib import Path
import sys

import numpy as np

if len(sys.argv) != 5:
    raise SystemExit("usage: audit RECEIPT ORIGINAL_PPO_ZIP ORIGINAL_XML ORIGINAL_ENV")
receipt_file, model, xml, env = map(Path, sys.argv[1:])
r = json.loads(receipt_file.read_text())
assert r["chapter"] == "Ch08" and r["section"] == "8.7"
assert r["status"] == "DIAGNOSTIC_SCOPED_PASS"
assert r["seeds"] == [1000, 1001]
assert r["horizon_max_steps_per_seed"] == 120
assert r["frozen_PPO_unchanged"] is True
assert r["original_PPO_performance"] == "0_OF_10_FAILURE_PRESERVED"
assert r["original_10x300_evaluation"] == r["test_only_PD_success"] == "NOT_RERUN"
assert r["training"] == r["gui"] == r["real_hardware"] == "NOT_RUN"
assert r["ch10"] == "HOLD"

ROOT = Path(__file__).resolve().parents[1]
expected = {
    "Ch08/ros2_ws/models/ppo_reach_final.zip": "78f85cc0d8cee868b66fe6b538fcf7b7a64b2d65632bd8036c01d8afeaceda92",
    "Ch08/ros2_ws/src/my_robot_description/assets/simple_arm_6dof.xml": "ffa277c1eda287e76279153c5c48075c0f8f03676ff6cde4fa0e7802e84daa99",
    "Ch08/ros2_ws/rl_env.py": "c89a8bd1b2cac0ca230b98aa01f765a517af9e6ca6dff064a879531c9f83439f",
}
for p in (model, xml, env):
    rel = str(p.resolve().relative_to(ROOT))
    digest = hashlib.sha256(p.read_bytes()).hexdigest()
    assert digest == r["assets_sha256"][rel], "unexpected frozen asset " + rel
    assert digest == expected[rel], "original 2026-11-13 asset changed " + rel

for summary in r["summaries"]:
    seed = summary["seed"]
    rows = json.loads((receipt_file.parent / f"vector_trace_seed_{seed}.json").read_text())
    assert len(rows) == summary["actual_steps"] and 1 <= len(rows) <= 120
    assert [s["step"] for s in rows] == list(range(1, len(rows)+1))
    target = np.array(summary["target_xyz_m"], dtype=float)
    prev_time = 0.0
    for i, row in enumerate(rows):
        t = float(row["sim_time_sec"])
        dt = float(row["dt_sec"])
        before = np.array(row["ee_prev_xyz_m"], dtype=float)
        after = np.array(row["ee_xyz_m"], dtype=float)
        goal = np.array(row["target_xyz_m"], dtype=float)
        velocity = np.array(row["ee_velocity_xyz_m_s"], dtype=float)
        action = np.array(row["actual_action"], dtype=float)
        assert np.isfinite(before).all() and np.isfinite(after).all()
        assert np.isfinite(goal).all() and np.isfinite(velocity).all()
        assert np.allclose(goal, target, atol=1e-6)
        assert action.shape == (6,) and np.isfinite(action).all()
        assert (abs(action) <= 1.00001).all()
        assert math.isclose(t-prev_time,dt,abs_tol=1e-8)
        assert 0 < dt < 0.1
        assert np.allclose((after-before)/dt,velocity,atol=1e-8)
        d0 = float(np.linalg.norm(goal-before))
        d1 = float(np.linalg.norm(goal-after))
        assert math.isclose(d0,row["distance_prev_m"],abs_tol=1e-6)
        assert math.isclose(d1,row["distance_m"],abs_tol=1e-6)
        projection = float(np.dot(velocity,(goal-before)/max(d0,1e-12)))
        assert math.isclose(projection,row["projected_approach_speed_m_s"],abs_tol=1e-8)
        assert math.isclose((d1-d0)/dt,row["distance_derivative_m_s"],abs_tol=1e-8)
        if i:
            assert np.allclose(before, rows[i-1]["ee_xyz_m"],atol=1e-8)
        prev_time = t
    distances = np.array([x["distance_m"] for x in rows])
    k = int(np.argmin(distances))
    assert k+1 == summary["closest_approach_step"]
    assert math.isclose(float(distances[k]),summary["closest_approach_m"],abs_tol=1e-8)
    assert math.isclose(float(distances[-1]),summary["final_distance_m"],abs_tol=1e-8)
    assert math.isclose(float(distances[-1]-distances[k]),summary["post_min_distance_increase_m"],abs_tol=1e-8)
    before = rows[:k+1]
    after = rows[k+1:]
    assert math.isclose(np.mean([s["projected_approach_speed_m_s"] for s in before]),
                        summary["pre_min_mean_projected_speed_m_s"],abs_tol=1e-8)
    if after:
        assert math.isclose(np.mean([s["projected_approach_speed_m_s"] for s in after]),
                            summary["post_min_mean_projected_speed_m_s"],abs_tol=1e-8)
        assert math.isclose(np.mean([s["projected_approach_speed_m_s"] < 0 for s in after]),
                            summary["post_min_receding_step_fraction"],abs_tol=1e-8)
    assert not any(x["distance_m"] < 0.05 for x in rows)
    assert not summary["goal_radius_0p05_reached"]
print("CH08_168_INDEPENDENT_EE_TARGET_VECTOR_PROJECTION_RECEIPT_PASS seeds=2 max_steps_each=120")
print("CH08_168_FROZEN_PPO_0_OF_10_PERFORMANCE_FAIL_UNCHANGED")
