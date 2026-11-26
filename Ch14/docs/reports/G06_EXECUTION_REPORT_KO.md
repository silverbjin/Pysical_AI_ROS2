# G06 개발·검수 보고서 — CPU Docker 배포 T14~T16
## 1. 실제 인수 범위
G04 ordered shutdown separately scoped PASS, Run45760289636 (GT3/3, four clean exits,601ms); original regression and generic simultaneous Ctrl+C HOLD. G06 actual Linux CI replay runtime independently tested. Source 9e1e867bd8ecd23a935af0fd291e0f7829a58119, Run45761633396 SUCCESS, job139712747805, artifact15089579800, ZIP SHA256 1685aa7385333ac812ad68558db47ef64e9f5e128f41ee63f6a23468fe7b7692, 34/34 internal exact hash coverage. No model/bag bytes uploaded, no hardware. G06 L0/L1 SCOPED_PASS; L2 Gazebo not claimed, L3/GPU NOT_RUN. Main untouched.
## 2. Implementation and dependency boundary
T14 Dockerfile.cpu pinned ROS base sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6, copy exact 45-wheel CPU lock, hash-verified wheelhouse, pip check, rosdep with explicit single ament_python virtual-key exception, actual setuptools/colcon tooling and normal install; multi-stage runner copies installed four packages (ch14_ai_common/interfaces/perception/performance_monitor) from same ABI base; no /opt/robot_ws/src or build, installed import and actual CPU inference. Gazebo package excluded intentionally from replay CPU MVP. Runtime tooling and model fetch/export scripts remain, no embedded external model/fixture. apt/rosdep online resolution can drift; same image ID within run, not bit-reproducibility across builds or registry release. Local image ID sha256:e7e9fe1f72bdde6000e3b5f03242bddba5127748178a54406d406fcdcf88591c, inspect size3423735909 bytes (3.424 decimal GB), colcon 7.57s and all rosdeps satisfied. Actual ONNX 7a0036fa3389769f62f48fae0b26e0acec937cee0e3c8d78e0bab31a7dbcfc4e from pinned original PT; bytes differ from prior e895... export, validated actual export and seed parity. Offline CPUExecutionProvider bus .923385500907898, bbox [0,1.4906005859375,408.3759765625,637.252685546875].
T15 run_docker.sh path-independent, actual host network/CycloneDDS/domain89, model SHA and mount preflight, owned container stop/inspect/log/rm. Wrong domain91 actual readiness timeout bag NOT_STARTED. T16 compose same image, domain90, readiness detector heartbeat with hash + monitor + input subscriptions and zero prior clock; actual single bag playback produces one clock. No privileges, host PID, devices; host UID/GID and CAP_DROP ALL plus no-new-privileges. Monitor real write probe before discovery. 
## 3. Actual bag and cross-container evidence
Pinned COCO 455085 RGB, 427x640, aligned synthetic 2m depth and static TF x=1m, actual rosbag2 SQLite 160 records, four topics x40 frames, duration7.8s, no stored clock; actual rosbag2 player --clock100. Bag db SHA 6c3ea9696bd1093833d2c1376f39d6f6aceb1ce94d86fb70f4c34fe9fa369f76; metadata 2d0b2fed7c65b90667cb8c00e46059ad35277c78c5fc43085726b43a92329cf7. Local evaluation bag only; no Gazebo sensor claim. Same bag/model used both runs in same CI.
| metric | standalone T15 | compose T16 |
|---|---:|---:|
| observed RGB / matched pairs | 40 / 40 | 40 / 40 |
| initial clock invalid guard | 1 | 1 |
| source accepted/published | 39/39 | 39/39 |
| independent detections / matched points | 39/39 | 39/39 |
| source-observer stamp overlap | 39 | 39 |
| source local oldest age max ms | 90.091712 | 130.088871 |
| independent receive age min/max ms | .099405/90.091712 | .079266/130.088871 |
| clock publishers observed / resets | 1/0 | 1/0 |
| diagnostics / heartbeat interval | 124/123 | 98/97 |
| inference latency / result age messages | 39/39 | 39/39 |
| worker join / container exits | true / 0,0,0 | true / 0,0,0 |
| monitor RTF | .99998146 | .99999420 |
All actual detected bus .9233855009; first stamp1.2s independent odom point [0.962751953125,-0.002513427734375,2.0]m. Initial frame rejected at clock=0, not silent dropped detection; no invalid age publish in local trace. All source and observer stamps match. Independent receive age is receiver latest clock snapshot, not independent source emission-time freshness or hard RT. Bag end clock freezes; do not infer wall freshness from last near-zero ROS age. No long-run benchmark repeat.
All six inspect image IDs identical, user1001:1001, cap-drop ALL, no-new-privileges, no privileged/host PID/device and model/bag mounts read-only. All six exit0; compose ps -aq empty after down, owned temporary asset cleanup passed. T15 standalone source/monitor removed. No full old G04/05 rerun.
## 4. Debug history
- 45760742831 FAIL build: virtual ament_python rosdep unresolved, 45 wheels and pip check PASS; fixed exact key only, actual build tool proof. Artifact15089987320 5/5.
- 45761089173 T14 actual PASS (image79d17b1d…, size3424591060), T15 DDS READY and detector39 targets max70.066499ms, sensor/detector exit0, monitor exit1 PermissionError writing evidence; root-owned asset cleanup also failed. Artifact15089563757 23/23. Fix host UID/GID for prep/runtime, HOME/ROS_LOG_DIR, actual write probe before discovery, keep no capabilities. No chmod777. Independent evidence missing in failed run, not counted as T15 acceptance.
- 45761633396 SUCCESS actual T14/T15/T16, independently verified source, observer, inspect, hashes. First image and failure artifacts preserved, new build due ephemeral CI runner. No main merge. 
## 5. Remaining limits
Linux CI only, WSL2 Docker Desktop vs native Engine and host network owner verification not performed. Optional GPU/TensorRT not run. Actual Gazebo native shutdown ordered runner separately verified once; generic simultaneous shutdown root cause not established. External asset rights/absolute semantic G01 failure/legacy PR sparse checkout and owner acceptance HOLD. G07 next: real Ch12 PPO bundle and 48→12 observation/ONNX; no training claims without checkpoint. See LAB_14_7_GUIDE_KO.md and G07_NEXT_WORK_PREVIEW_KO.md.
