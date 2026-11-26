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
| 14-9 | 12 | G04 | python/parameter_declaration.py | T09 NOT_RUN |
| 14-10 | 12 | G04 | python/param_callback.py | T10 NOT_RUN |
| 14-11 | 13 | G04 | python/hot_swap.py | T11 NOT_RUN |
| 14-12 | 14 | G04 | ros2_ws/src/ch14_ai_perception/launch/robot_ai_system.launch.py | T12 NOT_RUN |
| 14-13 | 15 | G05 | python/profiler.py | T13 NOT_RUN |
| 14-14 | 17 | G06 | docker/Dockerfile.cpu | T14 NOT_RUN |
| 14-15 | 17 | G06 | docker/run_docker.sh | T15 NOT_RUN |
| 14-16 | 18 | G06 | docker/compose.yaml | T16 NOT_RUN |
| 14-17 | 19–20 | G07 | python/export_rl_policy.py | T17 NOT_RUN |
| 14-18 | 20–21 | G07 | python/observation_builder.py | T18 NOT_RUN |
| 14-19 | 21–22 | G08 | python/rl_controller.py | T19 NOT_RUN |

차이: 14-7 예시에서 모델 생성은 노드 init이지만 GPU worker 자원 수명은 worker 내에서 관리; threshold snapshot 단일 읽기. 14-8 ATS slop은 공간 정렬 보장 아님. 14-9 중복 선언 금지. 14-11 후보 warmup 외 hash/클래스/계약·rollback·terminal request 상태 추가. 14-12/14-14/14-16 my_robot_ai_pkg → ch14_ai_perception, compose 명칭 정리. 14-17 shape 단독 검사보다 원본 load_bundle 선검증. 14-18/19 발췌는 기존 보호 계약과 결합. 14.6.6 Q6 예시 값 실측 아님. GPU 선택, 실제 HW 제외. T19 actual joint feedback, shadow/hold 별도 검증. 구현·실측 시 표 갱신.

Actual G01 evidence: 45744146299 T01, 45742206902 T03, 45745101023 fresh T02/T04. G01 not complete; actual T04 semantic failure documented. 14-2 canonical export_yolo currently implemented in backends.py (single backend contract), not export.py; 14-1/2/4 wrappers use yolo_lab.py. At that G01 checkpoint, no code 14-5 onward acceptance.

G02 Code 14-6 actual CPU comparison: compare_backends.py and backend_comparison.py, T06 scope 45748461194. Code 14-5 T05 remains NOT_RUN. No L1/L2/L3 promotion.

G03 actual L2: ch14_simulation/worlds/semantic_rgbd.sdf and scripts/g03_gazebo_ci.sh, 13/13 evaluable semantic/3D frames. CPU scope only; no release or L3 promotion.
