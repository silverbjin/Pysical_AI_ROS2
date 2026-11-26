# G04 개발·검증 보고서 — T09~T12 CPU ORT SCOPED_PASS

## 1. 기준 및 실제 실행
- 사용자 승인 저장소 silverbjin/Pysical_AI_ROS2, 기존 main 9431fb535ce7a51416c19c4395fb2ba3fabdad40, G03 기준 2f186a9bb7688deb2dd4ddcec0a18b2c8fab4f28. 구현 502e3374901d2017a9cc33d9518c6525708e8b18, 실제 검수 source 0a94aebe5438df0b6de462b0f961299bb90f5b3e.
- [Run 45755020128](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45755020128) 첫 실행 SUCCESS, 121s, result PASS/complete/exit0, job139691510641, artifact15086703629 ZIP SHA256 2aa2d4d6a8a88e0946c2a05a2dcaf688b384f6c9a11ef1c36e8d70fdb9d60ab2, 23/23 내부 파일 SHA 및 exact coverage 독립 검증. 증거는 evidence/g04_run_45755020128.json, g04_frame_trace.csv, 원본 artifact.
- G00 CPU lock exact SHA 73a9ca05ed6d36893faf575a06398dd6420e609dfca80753b1f3bb7c9ea1ada3, pip check PASS, 기존 Jazzy/Harmonic image digest 8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f 재사용. 15/15 pytest (G04 11, G03 순수 회귀 4), 4개 설치 빌드 6.33s. 기존 G01/G02 20-image/benchmark 및 G03 전체 과부하·fault·pause/resume는 반복하지 않음. 모델 바이너리가 배포되지 않으므로 pinned 원본 PT에서 n/s 각각 1회 실제 export 및 seed reference 생성. 두 ONNX SHA가 기존 G01 T04와 동일, n e8950e7e6edc29ee614a027ee7a07aa492afbda7f24faad049972be5b7c96546, s 6b213b04c58fc0df0039d59f00b665b727943ebed2a6a393727a2423a95e50e9. 새 모델 학습/threshold 완화 없음.

## 2. T09/T10 — ROS 2 parameter
parameters.py: 초기 descriptor/read_only, 순수 validator, on-set callback에는 상태 변경 없음. rclpy가 성공한 변경만 commit하고, executor에서 frame마다 immutable threshold pair 읽음. 모델·백엔드·시계·입력 토픽·max age는 startup-only. onnx legacy alias와 model_path 충돌 거부, max_age_sec startup 값은 0<age<=.3으로 제한. use_sim_time은 기존 rclpy 선언을 재선언하지 않고 callback으로 runtime 변경 거부. 기본 .5/.45 유지.
- 실제 startup 실패 2/2 (confidence 1.1, 파일 없음), READY 미발행.
- YAML confidence .6/iou .4, CLI confidence .5 → 실제 .5/.4, ros2 param get iou 출력 .4. 설치된 launch를 /tmp CWD에서 실행.
- 실제 SetParametersAtomically 17회: 7 정상, 10 거부. 0.0/1.0 수용; -0.01/1.01/NaN/Inf, integer, startup-only model_path/backend/use_sim_time/input_topic/max_age 거부. 혼합 요청 9개 전부 기존 .5/.45 보존. 0.0은 설정 수용만 검증, 과도한 NMS 비용을 유발하는 0.0 추론을 강제하지 않음.
- 실제 frozen bus image 동일 입력, threshold .5→1.0→.5의 검출 수 1→0→1, 빈 배열은 유효 무검출. 독립 DDS 수신 11/11 source emits.
- **처리 중 설정 스냅샷 실제 증거**: heartbeat wall_ns 181644072173에서 committed confidence=1.0, slot started4/completed3 (frame in-flight). 그 뒤 wall_ns 181654597906 (10.526ms 후) 이전 frame은 confidence=.5로 bus 1개 발행; 다음 frame은 1.0, box0. 한 프레임 안에서 threshold 혼합 없음. Source monotonic과 ROS age 분리.

## 3. T11 — 실제 모델 교체
SwapModel.srv ament_cmake/rosidl 설치 확인. ID만 허용, local trusted registry에 publisher PT/ONNX/ref/class hash, static FP32 IO, opset13, nms false. 후보 loader는 별도 CPU thread에서 실제 load/seed parity/2회 warm-up. 로딩 동안 기존 추론 유지, ready 이후 pending/result 정리·in-flight drain, executor의 atomic active/generation commit, epoch 갱신. 실패 시 active 변경 없음. 서비스 accepted는 terminal 성공이 아님.
| 결함/요청 | 실제 결과 | 경과 |
|---|---|---:|
| 임의 경로 | UNAPPROVED_MODEL | 거부 |
| 현재 활성 n | ALREADY_ACTIVE | 거부 |
| s 파일 없음 | FAILED, n/gen0 그대로, 이후 bus 검출 | 3.394ms |
| s 파일 손상 | FAILED, n/gen0 그대로, 이후 bus 검출 | 6.530ms |
| 실제 n→s | SUCCEEDED, s/gen1, 이후 bus 검출 | 704.046ms |
| 동시 s 요청 | BUSY 1회, 1개 요청만 accepted | 거부 |
| incompatible IO / ref SHA / class map | 실제 loader/registry offline 3/3 거부 | 별도 범위 |

성공 request_id 61a66e9f1b0b40278ec501b5ed7ff10e, LOADING 634.006ms + DRAINING 70.042ms = 704.046ms. 실제 candidate FP32 seed max abs 7.9345703125e-4, mean abs 1.0551162859e-6, 2회 warm-up. 기존 모델 LOADING 이후 commit 이전 3회 유효 발행. 이후 generation0 발행 0. Source age11개 평균168.196/max286.909ms, 모두 300ms 이하. Heartbeat 최대126.742ms. 마지막 old와 첫 new 발행 사이 719.808ms (probe pacing 및 신규 frame 대기 포함, 순수 교체 downtime 아님); 인지 공백 실제 존재, 무중단 보장 아님. 14 callbacks=13 accepted+1 drain drop; 13=12 started+1 overwrite; 12 completed=11 published+1 invalidated result. Worker joined, launch exit0.
교육 포인트: 잘못된 파일은 active session을 삭제한 뒤 로드하면 인지가 중단된다. 먼저 후보를 검증하고 성공 때만 generation 변경. 결과 유효성의 300ms 상한과 출력 간격 상한은 다른 계약. 이번 실패는 의도적 fault injection이며 첫 CI 자체는 실패하지 않음. Old CPU engine은 참조 수명으로 해제; 장시간 RSS 또는 leak/메모리 회수는 이번 시험에서 독립 측정하지 않음. GPU context swap 미구현/미검증.

## 4. T12 — 실제 설치 Launch 두 프로파일
- Replay: fixed COCO bus image 455085 실제 DDS, explicit RELIABLE fault test profile (기본 sensor BEST_EFFORT 유지). profile YAML + CLI, 실제 service/param CLI, clean exit0.
- Sim: 동일 G03 고정 person_standing mesh/world 및 자산 검증 재사용. 기존 G03은 direct process runner, 이번에는 실제 설치 robot_ai_system.launch.py를 /tmp CWD에서 실행. /clock, RGB/depth/info, bridge, static TF, actual YOLO and point. 독립 GT 3/3 class person, confidence .831024766, bbox IoU .921887173, RGB-D alignment .993447446, point [2.2531597614,-.0858891316,.9409519571]m. Source emits4 max age123ms; heartbeat max102.178ms, clock samples3727. Actual server stop true, Gazebo/bridge/TF/detector 모두 clean exit, worker joined. 3개 독립 GT-evaluable frames만 검수, 전체 카메라 프레임 및 60초 성능 보장 아님. Sim에서 model swap 자체는 실행하지 않음 (actual swap replay에서 검증).
- New launch canonical node name yolo_detector_node, G03 legacy launch/name onnx and mode/rgbd compatibility 유지. /perception/diagnostics와 heartbeat 유지; spec /diagnostics 및 /debug timing topics standardization G05에서. ROS OpenVINO/GPU/GUI/WSL2 NOT_RUN.

## 5. 인수 및 CI 관리
T09~12 CPU scope 실제 PASS; G04 L0/L1 SCOPED_PASS, L2는 T12 새 설치 경로의 실제 Gazebo 통합 scoped PASS. G01 absolute semantic fail, 외부 권리, legacy PR 체크, WSL2 L3, 이후 Gate 전체 배포 HOLD. No main merge. G03 workflows broad node-change push를 gate-specific verifier/world paths로 좁혀, G04 node changes로 이미 성공한 suite 전체 반복 방지; branch-specific manual dispatch is only available when workflow is in default branch, so gate-specific push path remains for future targeted runs. 기존 evidence 수정하지 않음. G04 변경에 맞춰 G03 script build includes interface package; G03 entire scripts not rerun. G05에서 60 wall-second profiles A/B/C + measured D selection and CPU/RSS/RTF; no prior benchmark repeat as new end-to-end scope.
