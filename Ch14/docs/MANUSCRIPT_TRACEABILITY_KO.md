# 개정 원고 직접 대조 — 구현 예정 추적표
S2 26쪽, SHA256 0ca3425f57c3608a5078edb5a8c708dc1d734459072532f9954634695df2b3a6. 19개 코드 번호 확인. S1/S3 전량 대조 미완료. 표는 예정 경로이며 실행 증거 아님.

| 코드 | S2 쪽 | Gate | 대상 | 시험 |
|---|---|---|---|---|
| 14-1 | 2–3 | G01 | python/benchmark_torch.py | T01 actual CPU 2x100 PASS, CUDA unavailable rejected |
| 14-2 | 4 | G01 | python/export_yolo.py | T02 fresh actual n/s export PASS |
| 14-3 | 4 | G01 | python/export_custom_model.py | T03 actual 100 inputs PASS |
| 14-4 | 5–6 | G01 | python/inference_onnx.py | T04 raw/paired PASS, required semantics FAIL |
| 14-5 | 7–8 | G02 | python/trt_inference.py | T05 NOT_RUN |
| 14-6 | 8 | G02 | python/ov_inference.py → ch14_ai_common/ov_backend.py | T06 actual CPU SCOPED_PASS 45748461194 |
| 14-7 | 9–11 | G03 | python/async_inference_node.py → detector_node.py/latest_slot.py | T07 actual L0/L1 scoped 45750110277 |
| 14-8 | 11–12 | G03 | python/rgbd_sync.py → rgbd_sync.py/detector_node.py | T08 L0/L1 scoped 45750520212/45750895879/45751287261; L2 actual scoped 45751598173 |
| 14-9 | 12 | G04 | python/parameter_declaration.py | T09 actual startup/descriptor/YAML/CLI 45755020128 |
| 14-10 | 12 | G04 | python/param_callback.py | T10 actual atomic17 and frame snapshot 45755020128 |
| 14-11 | 13 | G04 | python/hot_swap.py | T11 actual CPU n→s and rollback/busy 45755020128 |
| 14-12 | 14 | G04 | ros2_ws/src/ch14_ai_perception/launch/robot_ai_system.launch.py | T12 actual installed replay/sim launch 45755020128 |
| 14-13 | 15 | G05 | python/profiler.py | T13 actual CPU A/B/C 60s 45758721447; D N/A; node-local age caveat |
| 14-14 | 17 | G06 | docker/Dockerfile.cpu | T14 actual source-free CPU image/4 packages/ORT 45761633396 |
| 14-15 | 17 | G06 | docker/run_docker.sh | T15 actual standalone DDS/replay/negative domain/exit 45761633396 |
| 14-16 | 18 | G06 | docker/compose.yaml | T16 actual three-service compose bag/AI/monitor and cleanup 45761633396 |
| 14-17 | 19–20 | G07 | python/export_rl_policy.py | T17 actual SMOKE_ONLY scoped 45763347165 |
| 14-18 | 20–21 | G07 | python/observation_builder.py | T18 actual ROS DDS shadow scoped 45763347165 |
| 14-19 | 21–22 | G08 | python/rl_controller.py | T19 actual SMOKE_ONLY scoped: MuJoCo 45787876247, Gazebo 45799511462, protection 45799639451, clock DDS 45799888629 |

차이: 14-7 예시에서 모델 생성은 노드 init이지만 GPU worker 자원 수명은 worker 내에서 관리; threshold snapshot 단일 읽기. 14-8 ATS slop은 공간 정렬 보장 아님. 14-9 중복 선언 금지. 14-11 후보 warmup 외 hash/클래스/계약·rollback·terminal request 상태 추가. 14-12/14-14/14-16 my_robot_ai_pkg → ch14_ai_perception, compose 명칭 정리. 14-17 shape 단독 검사보다 원본 load_bundle 선검증. 14-18/19 발췌는 기존 보호 계약과 결합. 14.6.6 Q6 예시 값 실측 아님. GPU 선택, 실제 HW 제외. T19 actual joint feedback, shadow/hold 별도 검증. 구현·실측 시 표 갱신.

Actual G01 evidence: 45744146299 T01, 45742206902 T03, 45745101023 fresh T02/T04. G01 not complete; actual T04 semantic failure documented. 14-2 canonical export_yolo currently implemented in backends.py (single backend contract), not export.py; 14-1/2/4 wrappers use yolo_lab.py. At that G01 checkpoint, no code 14-5 onward acceptance.

G02 Code 14-6 actual CPU comparison: compare_backends.py and backend_comparison.py, T06 scope 45748461194. Code 14-5 T05 remains NOT_RUN. No L1/L2/L3 promotion.

G03 actual L2: ch14_simulation/worlds/semantic_rgbd.sdf and scripts/g03_gazebo_ci.sh, 13/13 evaluable semantic/3D frames. CPU scope only; no release or L3 promotion.

G04 canonical parameters.py, model_slot.py, ch14_ai_interfaces/srv/SwapModel.srv, installed YAML. Actual T09–T12 CPU ORT scope 45755020128; G04 launch node yolo_detector_node, legacy G03 direct node/name maintained. /diagnostics and debug topic completion G05; GPU/WSL2 NOT_RUN.

G05: canonical ch14_ai_common/profiler.py, ch14_performance_monitor/monitor_node.py, scripts/g05_actual_compare.py; actual CPU benchmark and manuscript table G05_EXECUTION_REPORT_KO.md. G04 historical PASS retained; latest regression shutdown HOLD 45758721305. No overall release promotion.

G06 canonical docker/Dockerfile.cpu, entrypoint.sh, build_cpu.sh, run_docker.sh, compose.yaml. Actual L1 CPU deployment scope 45761633396, 39/39 semantic + points each in two executions. Synthetic depth/TF bag, not actual Gazebo source; owner WSL2/GPU NOT_RUN.

G07 code14-17 python/export_rl_policy.py → ch14_rl_deployment/export_policy.py and policy.py; code14-18 observation_builder.py → observation_adapter.py and exact vendor/ch12 ros_core. Actual 45763347165 one SMOKE_ONLY training, 136 FP32 parity, actual ROS shadow DDS240/command0, T17/T18 scoped PASS. No original trained checkpoint/physical command or walking claim. T19 G08 pending.

G08 code14-19 canonical Ch14/python/rl_controller.py → installed ch14_rl_deployment/rl_controller.py. MuJoCo normal/pause actual 45787876247 SCOPED_PASS; actual 400/400 DDS and feedback. Gazebo and protection candidates submitted, full T19 pending. No walking quality or L3 claim.

G08 final: T19 SCOPED_PASS, actual MuJoCo and Gazebo ROS closed-loop normal cases; MuJoCo 5 negative checks and synthetic clock-reset DDS. 400/399 complete target-feedback pairs, 50Hz each. Gazebo source-time latency not established; no walking quality or L3 promotion. Earlier pending statements are historical checkpoints.

## G09 canonical execution index (scope, not a new runtime test)
| Code | command / entry point (prepared environment) | historical test/evidence | current release scope |
|---|---|---|---|
| 14-1 | python python/benchmark_torch.py --help; LAB14.1 pinned asset command | T01 45744146299 | CPU scoped |
| 14-2 | python python/export_yolo.py --help; LAB14.2 | T02 45744146299 / 45745101023 | CPU parity |
| 14-3 | python python/export_custom_model.py --output NEW_DIR | T03 45742206902 | synthetic custom model parity only |
| 14-4 | python python/inference_onnx.py --help; LAB14.2 | T04 45745101023 / 45746373267 | absolute semantic FAIL; conversion scoped |
| 14-5 | no implemented file; GPU optional | T05 NOT_RUN | NOT_IMPLEMENTED |
| 14-6 | python python/ov_inference.py --help; compare_backends.py; LAB14.3 | T06 45748461194 | CPU scoped |
| 14-7/8 | ros2 launch ch14_ai_perception perception.launch.py with verified args; LAB14.4 | T07/T08 45750110277/45751287261/45751598173 | DDS/actual RGB-D scope |
| 14-9/10/11 | ros2 param get/set and /ch14/swap_model; LAB14.5 | T09~11 45755020128 | atomic/rollback scoped |
| 14-12 | ros2 launch ch14_ai_perception robot_ai_system.launch.py; LAB14.5 | T12 45755020128/45760289636 | ordered runner scope |
| 14-13 | ros2 run ch14_performance_monitor monitor_node; LAB14.6 | T13 45758721447 | 60s A/B/C scoped |
| 14-14/15/16 | docker/build_cpu.sh, docker/run_docker.sh, docker compose -f docker/compose.yaml; LAB14.7 | T14~16 45761633396 | Linux CPU replay only |
| 14-17/18 | python python/export_rl_policy.py; ros2 run ch14_rl_deployment rl_shadow; LAB14.8 | T17/18 45763347165 | original accepted smoke artifact reuse; no new training/export |
| 14-19 | ros2 run ch14_rl_deployment rl_controller; LAB14.8 | T19 45787876247/45799511462/45799639451/45799888629 | two engines normal, MuJoCo negative, synthetic reset |
| 14.9 | scripts/bootstrap.sh, doctor.sh, run_lab.sh, verify_ch14.sh; LAB14.9 | G09 Linux CI 45815645513/45816276822 + actual WSL2 owner all 2026-11-26 | OWNER_L3_SCOPED_PASS, full release HOLD |

See G09_PUBLICATION_QA_KO.md for proposed checklist replacement; G09_ASSET_RELEASE_REGISTER_KO.md for current provenance vs historical manifests. Existing "NOT_RUN" statements inside historical paragraphs reflect the recorded checkpoint, not superseding the acceptance ledger.

G09 final owner preparation: exact source 6c458e345236b124c9aa60f65788f35cfed74e62; immutable build45815645513 and three physical entrypoints45816276822 actual Linux CI success. 9 guides, 18 code paths and optional14-5 absent. WSL2 actual L3 NOT_RUN; combined all not separately repeated, headless Docker only. Full release HOLD. See G09_WSL2_OWNER_ACCEPTANCE_KO.md.

G09 actual owner acceptance supersedes prior preparation checkpoint: --check all on WSL2, 82/82 hashes, build 6, perception13/13, MuJoCo400/400/400, Gazebo398/398/397, both50Hz, exit0 and no owned containers. Only 14.9 selected paths; no blanket T01–T19 L3 promotion or manuscript full QA. See reports/G09_WSL2_OWNER_ACCEPTANCE_REVIEW_20261126_KO.md.
