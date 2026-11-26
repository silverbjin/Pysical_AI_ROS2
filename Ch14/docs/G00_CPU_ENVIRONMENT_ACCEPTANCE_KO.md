# G00 CPU 환경 인수 — CI SCOPED_PASS
Run [45742206902](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45742206902), source 1228072c5679b608756bfbd578b2c56cbcfe32e8, jobs 139649687838 / 139649751858, conclusion success. [원본 artifact 15081503468](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45742206902/artifacts/15081503468), ZIP SHA256 a274b61874b797d2a72524e564d7ff02d451296679d981f19a5867fdc5898da1, 내부 25/25 SHA 검증. G00 result stage complete exit0. 기존 FAIL 45739828134 artifact 9/9 검증 및 보존.

| 계약 | 실측 |
|---|---|
| L0 metadata/graph/asset regression | 4+6+5 = 15/15 |
| 45 wheel exact hash lock | PASS, sha256 73a9ca05ed6d36893faf575a06398dd6420e609dfca80753b1f3bb7c9ea1ada3 |
| preinstall graph | 197 distributions / 182 edges / 0 errors |
| pip check | No broken requirements found |
| installed graph | 197 version matches / 182 edges / 0 errors |
| colcon | ch14_ai_common 1 package, 0.80s summary |
| cv_bridge | bgr8, 16UC1, 32FC1 roundtrip |
| rclpy | Detection2DArray publisher creation (not DDS E2E) |
| ONNX smoke | CPUExecutionProvider, abs error 2.9802322387695312e-08 |
| independent T03 | 100 samples allclose, max abs 2.384185791015625e-07, 12/12 foundation |
| owner WSL2/GPU/actual YOLO/PPO/physical | NOT_RUN |

Pin `requirements/cpu.lock.txt` is the exact 45-wheel CPU+export overlay from verified candidate, not full system-image or release approval. SHA matches artifact and candidate; historical 46 lock retained. Inherited setuptools 68.1.2, colcon-core 0.21.3; source base image ros@sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6. apt snapshot SHA256 2ee4e030303e5c730777fe59705f74ae800bbaa138c151490fbf28924cd86a45 matches previous run; future apt updates can drift so actual system graph and import/build check required. Separate minimal inference/export/GPU/OpenVINO/RL lock split remains unverified. G00 CPU profile PASS only; overall G00 BLOCKED: legal rights, actual fixture/model, remaining profiles and reuse closure. L3 not accepted. No unnecessary rerun.
