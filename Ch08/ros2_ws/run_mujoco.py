"""8.2: MuJoCo hello-world 데모 (CWD 독립, GUI/헤드리스 분리)."""
import argparse
import time
from pathlib import Path

import mujoco


MODEL_PATH = Path(__file__).resolve().parent / "src/my_robot_description/urdf/hello_mujoco.xml"


def run(steps=500, headless=False):
    if steps < 1:
        raise ValueError("steps must be positive")
    if not MODEL_PATH.is_file():
        raise FileNotFoundError(f"MuJoCo MJCF 파일 없음: {MODEL_PATH}")
    model = mujoco.MjModel.from_xml_path(str(MODEL_PATH))
    data = mujoco.MjData(model)
    if headless:
        for _ in range(steps):
            mujoco.mj_step(model, data)
        print(f"headless steps={steps}, sim_time={data.time:.4f}s, nq={model.nq}")
        return

    import mujoco.viewer
    with mujoco.viewer.launch_passive(model, data) as viewer:
        for _ in range(steps):
            if not viewer.is_running():
                break
            start = time.monotonic()
            mujoco.mj_step(model, data)
            viewer.sync()
            time.sleep(max(0.0, float(model.opt.timestep) - (time.monotonic() - start)))
    print(f"finished sim_time={data.time:.4f}s")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=500)
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()
    run(args.steps, args.headless)
