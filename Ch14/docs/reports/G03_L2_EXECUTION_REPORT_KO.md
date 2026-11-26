# G03 L2 실제 Gazebo RGB-D 실행 결과 — SCOPED_PASS
- 2026-11-26, [Run 45751598173](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45751598173), source `24305b1c4daa0e68522e8bc20317b33a672c2c71`, job 139680433197, artifact 15086325815. Workflow SUCCESS; result.json PASS, stage complete, exit0. ZIP SHA256 b8080406dcaeb671c5b388f2fe1c3172a9b72d8484b4e4a112cf78ede06598c7; internal manifest 21/21, exact coverage independently checked.
- Existing Gazebo image reused: ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f. CPU lock hash 73a9ca05ed6d36893faf575a06398dd6420e609dfca80753b1f3bb7c9ea1ada3; pip check PASS; 3 packages installed (2.40 s). Actual headless Gazebo Harmonic, ORT CPU, no robot hardware. Direct owned process runner; launch --show-args checked, full ros2 launch route and WSL2 GUI NOT_RUN.
- Actual exported n ONNX 7a0036fa3389769f62f48fae0b26e0acec937cee0e3c8d78e0bab31a7dbcfc4e (seed max abs .000701904296875, same bytes as G02 n; differs from L1 e895...); no redundant G01/G02 tests.
- Isolated mesh person at world x=2.5 m; camera [0,0,1], 640×480, 10Hz nominal, depth silhouette independent of YOLO. Model person_standing by Marina Kollmitz, created with MakeHuman; source https://github.com/osrf/gazebo_models/tree/8163eb4b5e7e21985c6591d1c0bfb56468c0093f/person_standing; repository CC BY 3.0 Unported, Copyright 2012 Nathan Koenig. 14 asset files and root license pinned, downloaded and verified; no source asset bytes committed. Asset-specific release review remains pending. Rendered annotation is derived diagnostic evidence, not source asset redistribution approval.
- Native /ch14/rgbd/image, depth_image, camera_info and /clock via actual ros_gz_bridge; optical frame override, static optical→odom TF. SDF gz_frame_id warning observed, nonfatal; actual headers and coordinate witness validated. World SHA cc45e70e6bf6199190fe4c826a9f10579d4f2e4b9d892f5f8b876f30b4ac6c2f.

## Actual witness and independently recomputed log evidence
| Criterion | Actual | Verdict |
|---|---|---|
| First 10 evaluable normal + 3 resumed frames | 13/13 class person; required target miss 0 within evaluated set | PASS |
| GT bbox / confidence / IoU | [306,66,367,438], .8309201598, .9217677548 (all 13; threshold .5) | PASS |
| RGB-depth mask alignment | .9934474458 (threshold .7); 14956 valid silhouette pixels | PASS |
| 3D point in odom | [2.2531597614,-.0858800172,.9408941837] m; 13/13 analytic checks | PASS |
| Source accepted pair/output | 27/27; max pair skew 0 ns; all labels person | PASS |
| Source publish Age | 27 records; min 50, mean 66.96296, max 86 ms; oldest max 86 ms (limit 300) | PASS |
| Wall heartbeat | 196 samples, max interval 101.157316 ms | PASS |
| Pause/resume | clock constant; no new valid output; pause guard; resume 3/3 | PASS |
| Shutdown | detector/TF/bridge/Gazebo exit0, forced=0; worker joined | PASS |

Witness received RGB68/depth69/info158/det24/point26/ann13, clock samples16805. Counts are distinct DDS subscriptions, not same-frame correspondence counts. Only 13 fully evaluable frames independently GT-checked; 27 source emits are not 27 independent GT passes. Static scene, partial DDS reception, no 60s continuous end-to-end acceptance or hard real-time claim. No blanket latest-HEAD full suite claim: L1 evidence from distinct exact source revisions. G03 CPU L0/L1/L2 SCOPED_PASS; G01 absolute semantic fail, legacy PR check, release rights, WSL2 L3, optional GPU and ROS OpenVINO integration remain unresolved. G04 independent development may start after review; preserve guards and all accepted evidence. No main merge.
