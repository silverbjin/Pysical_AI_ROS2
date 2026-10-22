"""Isolated EGL cost attribution, not native tracking acceptance."""
import json
import time
import sys
from pathlib import Path
import mujoco
import numpy as np

source = Path('Ch13/ros2_ws/src/integrated_robot_description/mujoco/vision_fixture.xml')
results = []
for variant in ('default', 'no_msaa', 'shadow512'):
    model = mujoco.MjModel.from_xml_path(str(source.resolve()))
    original = dict(offsamples=model.vis.quality.offsamples,
                    shadowsize=model.vis.quality.shadowsize)
    if variant == 'no_msaa':
        model.vis.quality.offsamples = 0
    if variant == 'shadow512':
        model.vis.quality.shadowsize = 512
    data = mujoco.MjData(model)
    mujoco.mj_forward(model, data)
    camera = sys.argv[1] if len(sys.argv) > 1 else 'overview'
    with mujoco.Renderer(model, height=240, width=320) as renderer:
        samples = []
        for i in range(35):
            renderer.update_scene(data, camera=camera)
            start = time.monotonic_ns()
            rgb = renderer.render()
            if i >= 5:
                samples.append((time.monotonic_ns()-start)/1e6)
    results.append(dict(variant=variant, original=original, camera=camera,
                        shape=list(rgb.shape), p50_ms=float(np.median(samples)),
                        p95_ms=float(np.percentile(samples, 95)), maximum_ms=max(samples)))
print(json.dumps(results, indent=2))
