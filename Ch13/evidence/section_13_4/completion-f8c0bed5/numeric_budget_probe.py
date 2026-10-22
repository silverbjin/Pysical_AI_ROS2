"""Paired CPU/latency probe of the actual fixture detector and servo math."""
import json
from pathlib import Path
import subprocess
import os
import sys
import time
from types import SimpleNamespace

import cv2
import numpy as np
from integrated_robot_vision.detectors import ColorFixtureBackend
from integrated_robot_vision.kinematics import KinematicChain
from integrated_robot_vision.servo import servo_target

xml = subprocess.check_output(['xacro', 'Ch13/ros2_ws/src/integrated_robot_description/urdf/robot_system.urdf.xacro',
                               'vision_enabled:=true'], text=True)
chain = KinematicChain.from_urdf(xml)
q = dict.fromkeys(chain.joint_names, 0.)
camera = chain.forward(q)
target = camera[:3, :3] @ np.array([.02,.02,.4]) + camera[:3,3]
k = SimpleNamespace(width=320, height=240, fx=277., fy=277., cx=160., cy=120.)
image = np.zeros((240,320,3), np.uint8)
image[100:130,150:180,2] = 255
detector = ColorFixtureBackend()
rows = []
for mode in [sys.argv[1]]:
    row = dict(mode=mode, opencv_threads=cv2.getNumThreads(),
               environment={key:os.environ.get(key) for key in
                   ('OPENCV_FOR_THREADS_NUM','OPENBLAS_NUM_THREADS','OMP_NUM_THREADS')})
    for name, function in [('fixture', lambda: detector.detect(image)),
                           ('servo', lambda: servo_target(chain,q,target,k,.2))]:
        for _ in range(10):
            assert function() is not None
        costs=[]
        cpu=time.process_time()
        for _ in range(300):
            start=time.monotonic()
            function()
            costs.append(time.monotonic()-start)
        row[name]=dict(cpu_s=time.process_time()-cpu, median_s=float(np.median(costs)),
                       p95_s=float(np.quantile(costs,.95)), maximum_s=max(costs))
    row['process_threads'] = [line for line in Path('/proc/self/status').read_text().splitlines()
                              if line.startswith('Threads:')]
    rows.append(row)
print(json.dumps(rows,indent=2))
