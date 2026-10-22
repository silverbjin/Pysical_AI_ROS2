#!/usr/bin/env python3
import argparse
import json
import math
from pathlib import Path

import mujoco
import numpy as np


def joint_names(model):
    return [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_JOINT, index) for index in range(model.njnt)]


def actuator_names(model):
    return [mujoco.mj_id2name(model, mujoco.mjtObj.mjOBJ_ACTUATOR, index) for index in range(model.nu)]


def run(model_path, steps=2000):
    model = mujoco.MjModel.from_xml_path(str(model_path))
    data = mujoco.MjData(model)
    mujoco.mj_resetDataKeyframe(model, data, 0)
    data.ctrl[:] = model.key_ctrl[0]
    heights = []
    for index in range(steps):
        if index == steps // 2:
            actuator = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_ACTUATOR, "arm_joint_2_motor")
            data.ctrl[actuator] = 0.08
        mujoco.mj_step(model, data)
        heights.append(float(data.qpos[2]))
    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "base_link")
    rotation = data.xmat[body].reshape(3, 3)
    tilt = math.acos(float(np.clip(rotation[2, 2], -1, 1)))
    finite = bool(np.isfinite(data.qpos).all() and np.isfinite(data.qvel).all())
    status = "PASS" if model.nu == 20 and finite and min(heights[-500:]) > 0.35 and tilt < 0.15 else "FAIL"
    return {
        "engine": "mujoco",
        "mode": "native_mj_step",
        "status": status,
        "mujoco_version": mujoco.__version__,
        "actuator_count": int(model.nu),
        "joint_names": [name for name in joint_names(model) if name != "root"],
        "actuator_names": actuator_names(model),
        "steps": steps,
        "sim_time": float(data.time),
        "height_min_last_500": min(heights[-500:]),
        "height_max_last_500": max(heights[-500:]),
        "base_tilt_rad": tilt,
        "finite_state": finite,
        "arm_joint_2_target": 0.08,
    }


def write_result(path, result):
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = run(Path(args.model))
    write_result(args.output, result)
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
