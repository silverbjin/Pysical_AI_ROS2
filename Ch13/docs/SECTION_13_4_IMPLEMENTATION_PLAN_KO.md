# 13.4 통합 시각 정보 처리 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. 사용자가 네이티브 모드를 선택했으므로 구현과 최종 리뷰 모두 원 세션에서 직접 수행한다. 서브에이전트를 호출하지 않는다.

**Goal:** 13.3 기반 통합 로봇의 실제 RGB-D·YOLO·촬영 시각 TF·대상별 필터와 제한적 시선 추적을 구현하고, 실제 Gazebo/MuJoCo에서 범위별 성공·실패를 기록한다.

**Architecture:** 새 integrated_robot_vision이 ROS 독립 수학/입력 계약과 탐지·융합 프로세스를 소유한다. description은 실제 센서와 카메라 외부 변환, interfaces는 TrackedTarget 메시지, 기존 runtime의 manipulation_node는 팔 trajectory의 단일 소유권을 유지한다. 엔진·제어·탐지는 프로세스를 분리한다.

**Tech Stack:** Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic/MuJoCo 3.3.7, Python 3.12, NumPy 1.26.4, pytest 8.4.2, cv_bridge, vision_msgs, tf2, Ultralytics 8.3.221의 YOLOv8n, CPU PyTorch 2.5.1/torchvision 0.20.1, OpenCV Python 4.10.0.84.

**Spec:** `Ch13/docs/SECTION_13_4_DESIGN_KO.md` — 사용자 승인 문서, 설계 커밋 `1366236f62ac674eedfbd0ae901f3f40e044d568`.

## Global Constraints

- 기반은 `df993e86d9b6ad446c058bc3b5a61c59c15495db`; 작업은 `feat/ch13-section-13-4`에서 한다. 13.1을 임의 병합하지 않는다.
- Ch05~Ch12 및 sources/는 수정하지 않는다. 이전 장의 import/overlay/build/install/log를 실행 경로로 사용하지 않는다.
- 새 build13_4/install13_4/log13_4와 전용 Python 환경을 사용한다. 남아 있는 13.1 산출물을 삭제하거나 새 소스로 커밋하지 않는다.
- RGB-D 320×240, 목표 15Hz; 추론 상한 10Hz; 제어용 추적 명령 상한 5Hz. hard realtime을 주장하지 않는다.
- RGB-depth skew≤0.030s, 입력 최대 ROS age 0.300s, CameraInfo 최대 age 1.0s, TF 대기≤0.100s.
- depth는 32FC1 m 또는 16UC1 mm→m; 유효 범위 [0.10,5.0]m; bbox 내부 5×5 패치에 최소 5개 유효 표본.
- optical 좌표는 X 우측/Y 아래/Z 전방; 원본 촬영 시각을 유지하고 odom에서 필터링한다. 실패 시 latest TF로 대체하지 않는다.
- confidence≥0.5, association 거리≤0.20m, TTL 0.300s, LPF tau=0.20s, 선택적 고정 alpha는 0<alpha≤1.
- 시선 추적 기본 OFF; arm_joint_1/arm_joint_5만 영점 대비 ±0.04rad, 속도≤0.10rad/s. 팔 outstanding trajectory는 하나뿐이다.
- 물리 엔진·clock·odom 동적 TF는 실행별 한 소유자뿐이다. 가짜 이동 TF나 두 번째 물리 엔진으로 RGB-D를 대체하지 않는다.
- 실제 YOLO와 color_fixture를 별도 기록한다. 의도한 실패, 실행 실패, 미실행, PARTIAL을 PASS로 바꾸지 않는다.
- Nav2/자동 보행 접근/PPO 학습/MoveIt/일반 IK/물리 파지는 제외한다. 13.5는 13.4 인계 후 재개한다.

## Review Focus

1. capture 뒤 calibration/clock epoch가 바뀌거나 역순 추론 결과가 도착하면 예전 상태를 덮어쓰지 않아야 한다 — Task 3/5의 epoch·calibration 회귀로 고정한다.
2. 16UC1 row padding·big-endian, ROI 경계·비정합 depth에서 잘못된 거리가 유효 목표가 되면 안 된다 — Task 1/3의 byte fixture로 고정한다.
3. 처리 도중 target/TF/joint가 만료되거나 disable과 trajectory 결과가 경합하면 추적이 다시 시작되면 안 된다 — Task 6의 generation token·취소 회귀로 고정한다.
4. 모델/영상 부재 또는 YOLO 오검출을 fixture 성공으로 대체하면 안 된다 — Task 4/7의 missing asset·backend 구분 및 필수 검사 집합으로 고정한다.
5. constructor/worker/finish/shutdown 중 예외나 이전 PASS 파일이 새 실행을 성공처럼 보이게 하면 안 된다 — Task 7의 실제 실패 실행·결과 schema 시험으로 고정한다.

## 파일 경계와 타입

새 패키지 루트는 `Ch13/ros2_ws/src/integrated_robot_vision/`, Python 모듈은 그 아래 `integrated_robot_vision/`이다. 이후 V는 이 모듈 경로, R은 `Ch13/ros2_ws/src/integrated_robot_runtime/integrated_robot_runtime/`, D는 `Ch13/ros2_ws/src/integrated_robot_description/`의 약칭이다. Files 항목에는 실제 경로를 명시한다.

| 파일/모듈 | 책임 |
|---|---|
| contracts.py, geometry.py | 불변 입력·결과 dataclass, depth decode/역투영/공분산 |
| kinematics.py | URDF chain FK, optical/render basis, 국소 projection Jacobian |
| freshness.py, cache.py | epoch/monotonic freshness, 최신 작업 한 개, RGB-D/Info 매칭 |
| detectors.py, object_detector.py | 로컬 가중치/fixture backend와 Detection2DArray 발행 |
| tracker.py, vision_processor.py | 대상 association/LPF, 역사 TF 조회·최종 발행 |
| servo.py, runtime/visual_tracking.py | 제한적 목표 생성과 기존 팔 소유권·취소 상태기계 |
| scripts/run_vision_13_4.py, verify_vision_13_4.py | 실제 프로세스 관리·ROS 관측·음성 시험·판정 |

runtime은 vision의 순수 수학 모듈을 의존할 수 있으나 vision은 runtime을 import하지 않는다. 통합 launch는 runtime에 두어 순환 의존성을 만들지 않는다. vision의 __init__은 torch/ultralytics를 import하지 않는다.

공유 dataclass는 Task 1에서 정의한다.

- `Intrinsics(width:int,height:int,fx:float,fy:float,cx:float,cy:float,frame_id:str,calibration_id:str)`.
- `Box2D(cx:float,cy:float,width:float,height:float,class_id:str,score:float)`; 좌표는 원본 이미지 픽셀이다.
- `Observation(stamp:float,epoch:int,calibration_id:str,frame_id:str,box:Box2D,point:np.ndarray,covariance:np.ndarray)`; point(3), covariance(3,3), frame_id=odom.
- `TrackEstimate(track_id:str,class_id:str,stamp:float,point:np.ndarray,covariance:np.ndarray,valid:bool,status:str)`.

---

### Task 1: 설치 가능한 입력 계약·depth 수학·메시지

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/{package.xml,setup.py,setup.cfg,resource/integrated_robot_vision,integrated_robot_vision/__init__.py,integrated_robot_vision/contracts.py,integrated_robot_vision/geometry.py}`; Create `Ch13/ros2_ws/src/integrated_robot_interfaces/msg/TrackedTarget.msg`; Modify `Ch13/ros2_ws/src/integrated_robot_interfaces/{CMakeLists.txt,package.xml}`; Create `Ch13/tests/{conftest.py,test_section_13_4_geometry.py}`.

**Interfaces:** Produces the four dataclasses above; `decode_depth(data:bytes,encoding:str,width:int,height:int,step:int,big_endian:bool)->np.ndarray`; `sample_depth(depth:np.ndarray,box:Box2D,min_valid:int=5)->tuple[float,float]` returns median m and MAD m; `deproject(u:float,v:float,depth_m:float,k:Intrinsics)->np.ndarray`; `transform_point(point:np.ndarray,matrix:np.ndarray)->np.ndarray`.

- [ ] **1. Write failing tests.** `test_mm_and_float_depth_project_same_point`: K=(fx=100,fy=100,cx=50,cy=50), u=60/v=50, 16UC1=1000 and 32FC1=1 must both yield `[0.1,0,1]`. `test_padded_big_endian_depth` uses literal two rows with one padding uint16 per row; decoded active pixels must equal `[[1,2],[3,4]]`m. `test_invalid_depth_and_intrinsics_rejected` covers 0/negative/NaN/Inf, unsupported encoding, truncated byte array, wrong step, fx=0, nonfinite calibration, outside pixels. `test_patch_minimum_and_background_rejection` requires minimum5, clips inside bbox and rejects a 5×5 patch with MAD>0.03m.
- [ ] **2. Verify RED.** `python -m pytest Ch13/tests/test_section_13_4_geometry.py -q`; Expected: missing vision modules/functions, not a ROS dependency error. conftest adds only Ch13 source package paths.
- [ ] **3. Implement minimum package and math.** Reject malformed dimensions/duplicate or empty IDs/nonfinite values. Decode using explicit dtype/strides and copy results; require len(data)==height×step. Median patch uses only finite in-range values; reject MAD>0.03m. Intrinsics parser in Task 3 validates rectification. No ROS/torch imports in math modules.
- [ ] **4. Add TrackedTarget.** Fields: `std_msgs/Header header`, `std_msgs/Header source_header`, `builtin_interfaces/Time processed_at`, `string track_id`, `string class_id`, `float32 score`, `geometry_msgs/Point position`, `float64[9] covariance`, `bool valid`, `string status`. Add std_msgs/builtin_interfaces dependencies and rosidl generation. status vocabulary is TRACKED/LOST/INVALID/TF_UNAVAILABLE/RESET. No fabricated orientation.
- [ ] **5. Verify GREEN and build.** Run the geometry tests, then in a clean ROS/13.4 Python environment `cd Ch13/ros2_ws && python /usr/bin/colcon --log-base log13_4 build --build-base build13_4 --install-base install13_4 --symlink-install`. Expected: 4 packages build; installed TrackedTarget imports and reports the listed fields. Run all existing Ch13 tests; record exact results, including pre-existing failures.
- [ ] **6. Commit.** Stage only these paths; commit `feat(ch13): define section 13.4 vision and RGB-D contracts`.

### Task 2: 동등한 optical 모델·실제 RGB-D·엔진 pose

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/kinematics.py`; Create `Ch13/ros2_ws/src/integrated_robot_description/{urdf/vision_sensors.xacro,config/vision_bridge.yaml,config/mujoco_vision_plugins.yaml,worlds/vision_fixture.sdf,mujoco/vision_fixture.xml,launch/vision_sensors.launch.py}`; Modify `Ch13/ros2_ws/src/integrated_robot_description/{urdf/robot_system.urdf.xacro,mujoco/robot_system.xml,launch/gazebo.launch.py,launch/mujoco.launch.py}`; Create `Ch13/tests/test_section_13_4_camera_model.py`.

**Interfaces:** `KinematicChain.from_urdf(xml_text:str,root:str='base_link',tip:str='camera_optical_frame')->KinematicChain`; `forward(positions:dict[str,float])->np.ndarray` returns homogeneous root→tip. Engine launch adds `vision_enabled` default false so 13.2/13.3 defaults remain unchanged; when true, selects vision fixture/config. Installed resources never require repository cwd.

- [ ] **1. Write failing model tests.** `test_zero_pose_optical_principal_ray` requires camera optical +Z expressed in base `[sqrt(3)/2,0,-0.5]` within1e-8. `test_left_up_pixel_signs_and_gl_basis` requires optical+X→sensor−Y, optical+Y→sensor−Z and MuJoCo camera−Z→optical+Z. `test_camera_extrinsic_parity` compares URDF/MJCF fixed transforms, keeps20 movable joints and existing masses/mount translation. `test_vision_off_preserves_legacy_launch` checks expanded resource behavior with vision off/on, not source-text grep.
- [ ] **2. Verify RED.** Run `python -m pytest Ch13/tests/test_section_13_4_camera_model.py -q`. Expected: missing optical chain/resources.
- [ ] **3. Implement exact transforms.** Normalize old camera_mount nominal pitch from rounded −1.5708 to −π/2 in both declarations, documenting the ~3.7e-6rad rounding correction. Add camera_link→camera_sensor_frame rpy=(0,2π/3,0), then sensor→optical rpy=(−π/2,0,−π/2), all new translations zero. Keep virtual frames massless/no collision. MuJoCo camera under optical frame uses local quaternion wxyz=(0,1,0,0), i.e. GL/optical X half-turn. FK resolves joints by name and validates limits/axis/rigid transforms.
- [ ] **4. Implement native sensors.** Gazebo rgbd_camera is attached in sensor frame with optical header, width320/height240, horizontalFOV π/3, near0.10/far5, update15Hz, Sensors/Ogre2 system. Native CameraInfo is authoritative. MuJoCo named camera `eye_in_hand` uses fovy=46.82644889274108degrees, same resolution, and fixed CameraPlugin streaming rate15Hz/topic names from spec. Configure only eye_in_hand, not overview. Use fixed upstream commit c261f55 and do not modify that external checkout.
- [ ] **5. Add observed pose once per backend.** Gazebo odometry system or MuJoCo FreeJointStatePublisher reads native base pose, then one small adapter publishes odom→base_footprint and Odometry. Verify baseline base_footprint→base_link fixed transform when converting native body pose. If upstream already emits the chosen TF, remap/disable its TF and keep only one owner. No integration of /cmd_vel into artificial odometry.
- [ ] **6. Verify GREEN and sensor smoke.** Rebuild only Ch13; expand/check_urdf; load MJCF with real MuJoCo. Run each actual engine individually with vision enabled and observe ≥10 RGB/depth/info samples, matching frame/resolution, advancing stamps, observed base pose and one clock/TF owner. Persist `evidence/section_13_4/sensors/{engine}/result.json` plus RGB/depth frames. Missing rendering/context causes FAIL, not synthesized replacement. Then rerun camera and all legacy tests.
- [ ] **7. Commit.** `feat(ch13): add native eye-in-hand RGB-D and optical frames`.

### Task 3: bounded RGB-D 캐시·historical TF 융합

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/{freshness.py,cache.py,vision_processor.py}`; Create `Ch13/ros2_ws/src/integrated_robot_vision/test/{conftest.py,test_rgbd_cache.py,test_historical_tf.py}`; Create `Ch13/tests/test_section_13_4_freshness.py`.

**Interfaces:** `ClockGate.observe(ros_now:float,wall_now:float)->int` returns epoch; `ClockGate.valid(stamp:float,epoch:int,ros_now:float,wall_now:float,receipt_wall:float)->bool`; `LatestSlot.replace(item)->None`, `take(timeout:float)->object|None`, `close()->None`. `RGBDCache.add_rgb(msg,epoch)`, `.add_depth(msg,epoch)`, `.add_info(msg,epoch)`, `.match(stamp:float,frame_id:str,epoch:int)->FrameBundle|None`. FrameBundle is frozen and contains rgb/depth messages, Intrinsics, capture/depth/info stamps and epoch. `lookup_capture_point(buffer,point:np.ndarray,source_frame:str,stamp_msg,target_frame:str='odom')->PointStamped` uses captured time only.

- [ ] **1. Write failing tests.** Cache tests match detection stamp1.0 to RGB1.0/depth1.02 and reject depth1.031, different frame/resolution, stale Info>1s, ROI/binning, nonzero distortion, nonidentity rectification, noncanonical K/P. Allow binning0/1 only and P zero or K|0; no arbitrary unregistered depth. Freshness tests reject zero/future beyond0.030s, age>0.300s, late completion after calibration/epoch change, nonadvancing clock for wall>0.300s. LatestSlot receives100 inputs but returns only99 with capacity1 and closes promptly.
- [ ] **2. Write real tf2 Buffer tests.** Store optical→odom translation0 at t=1 and translation1m at t=1.15. A captured optical point `[0,0,1]` stamped1 must transform to `[0,0,1]`, never `[1,0,1]`; completion at1.15 retains source stamp1. Missing/disconnected/out-of-range/zero stamps produce no point and a diagnostic, without latest fallback. An observation that becomes stale during a 100ms TF wait is rejected after lookup.
- [ ] **3. Verify RED.** `python -m pytest Ch13/tests/test_section_13_4_freshness.py Ch13/ros2_ws/src/integrated_robot_vision/test/test_rgbd_cache.py Ch13/ros2_ws/src/integrated_robot_vision/test/test_historical_tf.py -q`; Expected: missing cache/freshness/fusion functions.
- [ ] **4. Implement minimum cache and fusion.** RGB/depth capacity10 each; Info capacity5 with calibration hash over K/D/R/P/ROI/binning/frame/dimensions. Match detection to exact RGB capture within1ns, nearest depth within30ms; tie chooses earlier depth. Any calibration/epoch change clears pending work. Heavy processing uses one worker and one waiting item; callbacks only validate/cache/enqueue. After decoding, TF wait and before publication, recheck current epoch/calibration/age and result ordering.
- [ ] **5. Implement VisionProcessor raw output.** Subscribe to common RGB-D/Info and `/vision/detections`; use sensor QoS. Separate tf listener executor/callback path must continue while worker waits≤100ms. Publish only valid `/vision/target_raw` PointStamped with capture stamp and odom frame. Diagnostic reasons include depth/calibration/skew/TF/stale/reset. Track publication is added in Task5. Worker's shutdown is Event→join→destroy publishers/context; never publish after node destruction.
- [ ] **6. Verify GREEN and commit.** Run named tests and complete Ch13 suite, then `feat(ch13): fuse stamped RGB-D with historical TF safely`. Record RED/GREEN output and no skipped geometry/TF tests.

### Task 4: 실제 YOLO·fixture backend·재현 가능한 자산

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/{detectors.py,object_detector.py}`; Create `Ch13/requirements-vision-13-4.txt`, `Ch13/config/vision_assets.json`, `Ch13/scripts/{fetch_vision_assets.py,verify_yolo_13_4.py}`; Create `Ch13/ros2_ws/src/integrated_robot_vision/test/test_detector.py`; Modify vision setup/package files.

**Interfaces:** `DetectionBackend.detect(bgr:np.ndarray)->list[Box2D]`; `YoloBackend(weights:Path,device:str='cpu')`; `ColorFixtureBackend()`; `to_detection_array(boxes:list[Box2D],header)->Detection2DArray`; `verify_asset(path:Path,expected_sha256:str)->None`. ObjectDetector exposes backend=yolo, weights_path='', max_rate_hz=10, processing_delay_s=0, confidence=0.5.

- [ ] **1. Write failing tests.** `test_missing_weights_fail_before_model_import` and `test_asset_hash_mismatch_rejected` must fail closed without network or fixture fallback. `test_fixture_red_box_and_header_preserved` uses a hand-built100×80 BGR image containing red rectangle x20:40/y10:30 and asserts box center(29.5,19.5), width20/height20 (document inclusive/exclusive conversion), class fixture_red, copied capture header. Detection2DArray conversion tests class/score/finite bbox/clipping, empty result and no relabeling of completion time.
- [ ] **2. Verify RED.** Run detector tests; Expected: missing backend/conversion/asset validation.
- [ ] **3. Implement bounded detector.** Lazy import Ultralytics only after explicit existing weight/hash validation. Call predict on BGR with device=cpu, imgsz320, conf0.5, verbose=false and translate original-image xywh values. No node-time download, training or model.track identity assumptions. Capture epoch/calibration generation before work, rate-limit by monotonic starts, keep only newest waiting frame, discard stale/out-of-order results after inference. An explicit color_fixture option performs deterministic red segmentation and never changes backend labels.
- [ ] **4. Install and freeze actual dependencies.** In a new persistent 13.4 venv with ROS system-site-packages, pin NumPy1.26.4, pytest8.4.2, ultralytics8.3.221, opencv-python4.10.0.84, Pillow10.4.0. Install torch2.5.1+cpu/torchvision0.20.1+cpu from the official CPU index. Run pip check and cv_bridge round-trip with NumPy1; record resolved versions. Do not install a NumPy2-only OpenCV release or both headless and GUI OpenCV wheels. The default non-YOLO math/runtime path must not import torch.
- [ ] **5. Fetch trusted assets explicitly.** Download official YOLOv8n from `https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt` and bus image from versioned `https://raw.githubusercontent.com/ultralytics/ultralytics/v8.3.221/ultralytics/assets/bus.jpg`. Record actual SHA256, URL, source version/license and size in vision_assets.json; subsequent downloads require recorded hash match. Do not load untrusted .pt files. Store large weights outside tracked source and supply absolute path; commit metadata, not incidental caches. If URL/license/source cannot be confirmed, stop that asset path and report, do not substitute an unexplained asset. Ultralytics distribution declares AGPL-3.0-or-later; document separately from Ch13's existing Apache declarations.
- [ ] **6. Verify GREEN and actual inference.** Run unit suite and `python Ch13/scripts/verify_yolo_13_4.py --weights <explicit-path> --image <explicit-path> --output Ch13/evidence/section_13_4/yolo/result.json`. Expected: real YOLO inference with ≥1 COCO bus(class5) detection score≥0.5, finite bounded bbox, version/hash/latency and annotated image recorded. This is inference smoke, not an accuracy benchmark or engine recognition proof. Commit `feat(ch13): add explicit YOLO and deterministic fixture detection`.

### Task 5: 대상별 추적·LPF·만료 출력

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/tracker.py`; Modify `.../vision_processor.py`; Create `Ch13/tests/test_section_13_4_tracking.py`, `Ch13/ros2_ws/src/integrated_robot_vision/test/test_target_messages.py`.

**Interfaces:** `TrackManager.update(observations:list[Observation],ros_now:float,wall_now:float)->TrackEstimate`; `.expire(ros_now:float,wall_now:float)->TrackEstimate|None`; `.reset(reason:str,epoch:int)->None`; `TargetFilter.update(point:np.ndarray,stamp:float)->np.ndarray` with tau=.20 or optional fixed alpha. Covariance is copied, finite/symmetric/PSD and derived from depth MAD with floor1e-6m², rotated into odom; it is a heuristic, not calibrated confidence.

- [ ] **1. Write failing tests.** With tau=.20 and dt=.20, starting point0 then point0.1m yields x=`0.1*(1-exp(-1))`. Fixed alpha=.25 yields .025. `test_new_track_never_averages_old_object` changes ID/class/epoch/frame/calibration and expects fresh point, not mixed values. Association requires same class, IoU≥0.1 and distance≤.20m; equal best candidates within0.05 association score margin are ambiguous/invalid, not chosen arbitrarily. Tests cover outlier, empty detections, repeated/older stamps, TTL at .301s, wall-clock pause, reappearance with a new track ID and no revived old filter.
- [ ] **2. Verify RED.** Run tracking/message tests; Expected: missing TrackManager/filter/output functions.
- [ ] **3. Implement deterministic association and filtering.** Keep one selected target at a time and IDs formed from a per-process UUID, epoch and monotonic counter so restart cannot revive an old identity. Tests inject a fixed instance ID. First acquisition selects highest confidence only if unique by the0.05 margin. Rank later candidates by IoU, reject ambiguous ones; never update on an invalid observation or duplicate time. A >.20m innovation is an outlier, does not extend previous TTL and may acquire a new ID only after the old track expires. No global multi-object tracking claim.
- [ ] **4. Publish valid and invalid states.** `/vision/target_filtered` uses capture stamp and odom. TrackedTarget includes source capture header, processed_at, copied filtered point/covariance and validity. On LOST/INVALID/TF_UNAVAILABLE/RESET, retain last observation stamp, valid=false and cease raw/filtered valid point outputs. The status path may report immediately but cannot refresh old target age. Reacquisition is new track identity. Add a steady-time watchdog independent of simulation timers.
- [ ] **5. Verify GREEN and commit.** Run tests and full suite. Replay delayed calibrated observations through a real tf2 Buffer and verify IDs/LPF/stamps and invalidation. Commit `feat(ch13): track and filter targets with explicit validity and TTL`.

### Task 6: 제한적 시선 추적·팔 작업 배타성

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/integrated_robot_vision/servo.py`, `Ch13/ros2_ws/src/integrated_robot_runtime/integrated_robot_runtime/visual_tracking.py`; Modify runtime `{package.xml,integrated_robot_runtime/manipulation.py}`; Create `Ch13/tests/test_section_13_4_servo.py`, `Ch13/ros2_ws/src/integrated_robot_runtime/test/test_visual_tracking.py`.

**Interfaces:** `projection_jacobian(chain:KinematicChain,q:dict[str,float],target_base:np.ndarray,k:Intrinsics,joints:tuple=('arm_joint_1','arm_joint_5'))->np.ndarray`; `servo_target(chain,q,target_base,k,dt:float)->dict[str,float]|None`. `VisualTrackingGuard.enable(conditions:dict)->int` returns generation token, `.disable(reason:str)->None`, `.reserve(token:int)->bool`, `.complete(token:int)->None`. ManipulationNode exposes `/manipulation_node/set_visual_tracking` SetBool and remains the only runtime FollowJointTrajectory client producer.

- [ ] **1. Write failing math tests.** Use full model FK and independent finite-difference perturbations1e-5rad to verify 2×2 image Jacobian sign/rank. For a small visible off-center target, one allowed step must reduce projected error. At q1/q5=.04, no step exceeds .04; for dt=.2 each step≤.02rad; all other joints unchanged. Reject nonfinite/negative dt, target behind camera, condition number>100, singular values<1e-6, missing/reordered joint names. Clamp dt≤.2 so a long scheduler pause cannot create a large step.
- [ ] **2. Write failing ownership tests.** Default false means zero tracking action goals. Enable fails if inactive, unsafe/unfresh joints, invalid/stale target, absent model/CameraInfo, other arm reservation or unknown leg state. Model same-generation disable-vs-completion race: a late result must not re-enable or send a successor. stow/PickObject/tracking reservations exclude each other. Two concurrent enable/goal callbacks cannot both reserve; external trajectory topic/action goal activity cancels tracking. Cancellation timeout must latch fault and block stow/new tracking until explicit recovery, rather than assume the arm is free.
- [ ] **3. Verify RED.** Run servo and visual_tracking tests; Expected: missing math/guard hooks, not false success from mocked publishers.
- [ ] **4. Implement minimum servo.** Compute FK Jacobian with centered finite differences1e-5, damped least-squares λ=.01, error gain=.5; clip q1/q5 to ±.04 and speed .10rad/s. Use target in odom transformed into base at the fresh measured joint timestamp; do not reuse camera capture-relative coordinates as current ones. Build KinematicChain from latched robot_description. The pure servo function changes only the two tracked entries of a copy of q. Runtime freezes the other four joints at the fresh safe activation reference, rather than sending noisy new values or moving them to another nominal pose.
- [ ] **5. Integrate one owner.** Under the existing manipulation lock, reserve tracking generation and keep the shared arm-work reservation for the entire enabled tracking session; goal completion clears only its outstanding-goal flag. Set safe false while a trajectory is outstanding. Action dispatch/result/cancel is asynchronous with bounded deadlines and continued executor progress. Send at≤5Hz, horizon .2s, six arm names in canonical order; do not send the next until completion/cancel ack. Register each chosen goal UUID before send_goal_async so controller status cannot misclassify its own not-yet-acknowledged goal. Observe action GoalStatusArray for unknown live UUIDs and reject any direct /arm_trajectory_controller/joint_trajectory publisher; external activity stops only this session's own commands, without claiming to cancel another operator's goal. Before every dispatch recheck generation, epoch, target ROS/wall age≤.3s, joint age≤.3s and safe_arm. On disable/loss/clock reset/lifecycle transition cancel outstanding and latch tracking OFF. Retain reservation until ack, or latch fault on timeout. The position controller holds its last safe setpoint; no torque-off claim and no automatic stow motion. Prevent stow/PickObject callbacks from bypassing the shared reservation.
- [ ] **6. Verify GREEN and actual controller refusal paths.** Run full tests and launch a real engine with tracking disabled; assert no extra arm action goals and existing stow/PickObject dry-run regression still works. Then enable local tracking, inject target loss/disable while an action is pending, and inspect actual cancel/result and absence of later goals. Commit `feat(ch13): add bounded visual tracking under exclusive arm ownership`.

### Task 7: 공통 launch·실제 엔진·실패를 숨기지 않는 검증기

**Files:** Create `Ch13/ros2_ws/src/integrated_robot_vision/launch/vision.launch.py`, `Ch13/ros2_ws/src/integrated_robot_runtime/launch/vision_system.launch.py`, `Ch13/scripts/{run_vision_13_4.py,verify_vision_13_4.py}`, `Ch13/tests/test_section_13_4_verifier.py`; Modify setup/package manifests only as needed for installed launch and dependencies.

**Interfaces:** Combined launch arguments: engine=gazebo|mujoco, detector_backend=yolo|color_fixture, weights_path, tracking_enabled=false, processing_delay_s=0, use_sim_time=true. No auto-enable: explicit tracking_enabled=true still waits for runtime readiness/valid target and requests the SetBool service; failure stays OFF. `verdict(result:dict,required:set[str])->str` requires complete required keys, all true, successful completion, no errors and matching run_id. Overall summary keeps RGB-D geometry, YOLO smoke, YOLO engine, tracking, legacy regression statuses separate.

- [ ] **1. Write failing verifier tests.** Fresh RUNNING overwrites an earlier PASS at start; missing check, exception, constructor/worker/finish failure, process death, deadline, stale run_id/timestamps and missing artifact all yield FAIL/nonzero. Partial semantic/Yolo recognition failures yield PARTIAL without marking engine geometry or inference unexecuted as PASS. Cleanup tests assert only recorded start_new_session process groups are signaled and every created resource is protected by try/finally, including constructor failures.
- [ ] **2. Verify RED.** Run verifier tests; Expected: missing launch/runner/verdict. Test actual subprocess behavior against controlled short-lived processes, not script text.
- [ ] **3. Implement installed launch.** Launch exactly one selected engine with vision_enabled=true; include runtime nodes and the new detector/fusion processes; do not also launch old simulated-delay vision_processor. Preserve 13.3 default launch behavior. Missing yolo weights fails startup explicitly; color_fixture is only explicit. Shutdown order: stop new goals, cancel/join workers, stop nodes, request Gazebo server stop, signal launch parent, then bounded TERM/KILL only owned groups if necessary. Record acknowledgement/forced cleanup/residual PIDs.
- [ ] **4. Implement measurable fixtures.** Red matte plane/box at the nominal optical sight line, recorded physical world pose and visible surface equation, no occluding robot link. Static camera/fixture geometry is declared identically in both engines. RGB/depth frame and optical→odom pose at capture time define ground-truth ray/surface intersection; compare to the visible surface, not cube COM. Delay case uses150ms artificial inference delay and actual arm1 small oscillation amplitude .03rad, period2s via the existing owner. It is a camera-motion robustness test, not PPO walking.
- [ ] **5. Execute geometry and delay trials serially.** `python Ch13/scripts/run_vision_13_4.py --engine gazebo --detector-backend color_fixture --output-dir Ch13/evidence/section_13_4/gazebo/geometry`, then equivalent mujoco. Each real run must collect≥30 valid observations, static RMS≤.03m, delayed historical-TF RMS≤.05m; record current-time-TF comparison as diagnostic, not replace source stamps. Record raw RGB/depth/Info, calibrated transforms, state/command timing, invalid counters, native versions and one clock/TF owner. Engine launch/update/shutdown failures return nonzero.
- [ ] **6. Execute YOLO and tracking trials separately.** Run real yolo backend on each engine's actual sensor images with explicit weight path; save detection coverage, confidence, 3D valid count and samples even if zero. Do not force a simple red cube into a COCO class or use object pose as detector output. A failed engine recognition trial remains FAIL/PARTIAL while geometry may pass. In separate color_fixture local tracking runs, collect≥5s, require≥20% pixel-error reduction, all position/speed/rate limits, then drop images/TF/joints and verify no new goals after .3s+.2s wall bound; record out-of-range safe refusals separately. Never turn a refusal into successful tracking.
- [ ] **7. Run regressions and commit.** Full Ch13 pytest, clean four-package build, colcon test and test-result (no zero-test false success); rerun existing 13.3 engine/runtime regression sequentially with vision disabled. Run each negative verification with a new output path. Commit `test(ch13): verify section 13.4 native vision and safety paths` with compact/raw evidence and exact outcomes, not fabricated expected counts.

### Task 8: 최종 가이드·재사용·자체 리뷰·커밋·push

**Files:** Create `Ch13/docs/{LAB_13_4_GUIDE_KO.md,SECTION_13_4_REPORT_KO.md,SECTION_13_4_REVIEW_KO.md}`, `Ch13/scripts/verify_all_13_4.py`; Modify `Ch13/{README.md,docs/REUSE_MANIFEST.md,.gitignore}`; Create/Update `Ch13/evidence/section_13_4/**`, `Ch13/tests/test_section_13_4_summary.py`.

**Interfaces:** `summarize(results:dict,run_id:str)->dict` records statuses plus measured values. Required engine geometry/core safety failure→FAIL; unavailable/failed YOLO engine recognition or tracking with other functional groups passed→PARTIAL; PASS requires all required groups executed and passed. Lack of observed motion/sensor data is never PASS. Runner exit0 for fully executed PASS/PARTIAL with clear printed status, nonzero for infrastructure/core failures; JSON controls feature-completion claims.

- [ ] **1. Write failing summary tests.** Empty/missing/old-run results or false-PASS error payloads fail; fixture success plus YOLO missing stays PARTIAL; weights smoke alone cannot imply engine YOLO success; declared unexecuted GUI/real robot/learning stays UNVERIFIED. Source manifest hashes use Git blob bytes at the source commit, not accidental CRLF checkout bytes. Source inventory prunes venv/build/install/log/cache/evidence and captures code hashes.
- [ ] **2. Verify RED.** Run summary tests; Expected: missing summarizer. Implement serial fresh command execution and strict run/mtime/schema validation; do not merely reread cached result.json. Record verified code SHA/dirty paths/commands/times/versions/durations and source hashes; final evidence commit SHA is verified separately to avoid self-reference.
- [ ] **3. Write student guide and reuse manifest.** Include clean dependency/venv setup, build four packages, explicit trusted asset preparation, default observation-only launch, backend topic/frame contracts, historical TF vs current control-frame explanation, invalidation/TTL, enable/disable tracking, failure diagnostics, engine differences and shutdown. Record all copied/concept-adapted Ch07/13.3 sources, exact commits/paths/licenses/blob SHA256/new path/changes and camera rounding correction. Keep source license TODO unresolved rather than invent a license. Explain Ultralytics dependency terms without asserting legal clearance.
- [ ] **4. Perform native self-review.** No subagent dispatch. Read the whole code diff as a separate pass, focusing on the five Review Focus rows. Verify controls cannot bypass the single arm owner, inactive/default behavior, late result/cancel races, depth/TF errors, provenance and truthful verdicts. Record the limitation that author self-review is not independent review. Any functional fix gets a reproducing RED→GREEN and full green suite, then affected real-engine replay.
- [ ] **5. Final verification.** Run `python Ch13/scripts/verify_all_13_4.py` in the documented clean environment. Expected: fresh four-package build, complete pytest/colcon result, actual engines and detailed PASS/PARTIAL/FAIL without hidden skips. Check installed package prefixes and non-source import/resource paths. `git diff --name-only df993e86 -- Ch05 Ch06 Ch07 Ch08 Ch09 Ch10 Ch11 Ch12` must be empty under canonical text comparison; verify native Windows Git and command-local CRLF normalization agree, without editing prior chapters. `git diff --check` must pass.
- [ ] **6. Commit and push only 13.4.** Stage explicit Ch13 sources/docs/evidence, excluding previous generated artifacts, caches and large unlicensed model weights. Commit final report/results. Inspect remote branch SHA for unexpected advance, normal push `git push -u origin feat/ch13-section-13-4`, never force/merge main. Compare `git rev-parse HEAD` with `git ls-remote --heads origin refs/heads/feat/ch13-section-13-4`; equality is required. Report full final SHA, verified code SHA, actual test counts, status/limits and useful document links. Do not claim completion before this evidence exists.
- [ ] **7. Handoff to 13.5.** Once 13.4 result and branch are handed off, resume the separately requested 13.5 design from the resulting target validity contract. Preserve measured failure/UNVERIFIED facts and the absent validated walking policy; 13.4's approval does not authorize silently asserting autonomous approach success.

## RED 테스트의 고정 assertion

각 Task의 첫 단계는 위 입력 fixture를 구성하고 다음 assertion을 해당 테스트 파일에 옮기는 것을 포함한다. `pytest`, `np`, `math`는 테스트의 명시적 import이며, 아래 fixture 변수는 각 Task에 기술한 입력/실행 결과다. 이 절은 구현 함수 본문이 아니다.

```python
# Task 1: test_mm_and_float_depth_project_same_point
np.testing.assert_allclose(point_mm, [0.1, 0.0, 1.0])
np.testing.assert_allclose(point_float, point_mm)
# test_padded_big_endian_depth
np.testing.assert_allclose(decoded, [[1.0, 2.0], [3.0, 4.0]])

# Task 2: test_zero_pose_optical_principal_ray
np.testing.assert_allclose(principal_ray_base, [math.sqrt(3)/2, 0, -0.5], atol=1e-8)
assert movable_joint_count == 20

# Task 3: test_capture_transform_is_not_latest
np.testing.assert_allclose(capture_point_odom, [0.0, 0.0, 1.0])
assert output_stamp == capture_stamp
# test_uninitialized_or_frozen_clock_rejected
assert valid_before_positive_clock_observation is False
assert valid_after_wall_clock_pause_0_301s is False

# Task 4: test_fixture_red_box_and_header_preserved
assert (box.cx, box.cy, box.width, box.height) == (29.5, 19.5, 20, 20)
assert output.header == image.header
assert box.class_id == 'fixture_red'
# test_missing_weights_fail_before_model_import
assert model_import_count == 0
assert fixture_fallback_count == 0

# Task 5: test_variable_dt_lpf_and_ttl
assert filtered_x == pytest.approx(0.1 * (1 - math.exp(-1)))
assert expired_after_0_301s.valid is False
assert reacquired.track_id != expired_after_0_301s.track_id

# Task 6: test_bounded_step_and_late_completion
assert abs(next_q['arm_joint_1']) <= 0.04
assert abs(next_q['arm_joint_5']) <= 0.04
assert max_step_for_dt_0_2 <= 0.02 + 1e-12
assert goals_after_disable_and_late_completion == 0
assert simultaneously_outstanding_own_goals <= 1

# Task 7: test_incomplete_verification_fails_closed
assert verdict(missing_required_check_result, required) == 'FAIL'
assert verdict(previous_run_result, required) == 'FAIL'
assert sensor_frames_observed >= 30
assert static_rms_m <= 0.03
assert delayed_capture_tf_rms_m <= 0.05
# Measured acceptance assertions belong only to actual engine trials, never mocks.

# Task 8: test_fixture_does_not_imply_yolo_success
assert summarize(fixture_pass_yolo_missing, run_id)['status'] == 'PARTIAL'
assert summarize(empty_results, run_id)['status'] == 'FAIL'
assert changed_prior_chapter_paths == []
```

## 계획 자체 검토

- 설계 1–3/9 → Tasks1/7/8, 센서·프레임4 → Task2, 탐지/깊이/TF5 → Tasks1/3/4, 추적·필터6 → Task5, 제어권7 → Task6, 인수8 → Tasks1–8에 매핑했다.
- Task1 dataclass/geometry→Task3 fusion→Task5 TrackEstimate→Task6 servo, Task2 FK→Task6 Jacobian, Task4 Detection2DArray→Task3 cache의 이름/단위/시각을 일치시켰다.
- runtime→vision 순수 수학의 단방향 의존으로 고정하고 vision에서 runtime을 import하지 않는다. 모든 목표·관절 배열은 이름과 frame/stamp를 검사한다.
- 성능·오차 요구는 시험할 값으로 고정했다. 실제 실패를 허용치를 넓히거나 backend를 바꿔 숨기지 않고 판정·보고한다.
- 사용자는 네이티브 실행을 이미 선택했다. 다음 단계는 이 계획의 사용자 검토·승인 후 executing-plans로 실행하는 것이다. 현재는 계획 문서만 작성했으며 제품 코드/의존성 설치/엔진 실습을 아직 변경하지 않았다.

## 확인한 배포 자료

- https://pypi.org/pypi/ultralytics/8.3.221/json
- https://pypi.org/pypi/opencv-python/4.10.0.84/json
- ROS/모델/TF 근거와 기존 기능 한계는 승인된 설계서의 참조와 로컬 고정 커밋을 따른다.
