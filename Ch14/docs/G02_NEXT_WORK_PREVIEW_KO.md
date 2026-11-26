# G02 다음 개발 프리뷰 (실행 전)
선행 G01 actual n/s exports and fixed fixture T04 acceptance required; reuse actual T02 ONNX bytes/hash and frozen fixture, no new training. Code 14-5 python/trt_inference.py → ch14_ai_common/trt_backend.py: TensorRT 10.x static LINEAR FP32/FP16, explicit set_tensor_address/execute_async_v3/stream sync, no fallback; WSL2 GPU/driver/CUDA/TensorRT qualification first, actual engine built on target, unsupported GPU N/A only with evidence. Code 14-6 python/ov_inference.py → ov_backend.py: OpenVINO Core CPU, explicit latency/FP32 hints, actual device/settings, separate lock; ORT CPU default vs OpenVINO same tensor/model/fixture, 10 warmup/100 samples, P50/P95/P99, throughput and raw allclose at 1e-3/1e-3, 1:1 bbox IoU>=.95 score<=.02, required target misses zero. FP16 optional bbox>=.90 and score<=.05 per spec. Keep model-only vs end-to-end metrics separate. No GPU claims on CPU CI. No regression of already verified T01/T03 if source/lock same. G02 report+LAB14.3+evidence+commit. Next G03 actual Gazebo RGB-D and ROS worker, not part of G02. Gate-level L0 offline / L1 ROS / L2 physical / L3 owner per original spec.

## G01 결과에 따른 착수 조건 갱신
G01 T04 실제 raw/box parity PASS, required semantic FAIL (n 2/s1), run 45745101023. 즉시 G02 전체 Gate 진행하지 않는다. Prior successful export/benchmark evidence 유지. 우선 두 고정 이미지의 raw score/GT만 단일 분석하고 owner release/semantic policy 및 legacy PR sparse checkout fix 확인. G02의 OpenVINO CPU 비교 설계/lock 사전 감사만 독립적으로 가능; 실제 G02 통합 검수는 G01 gate 승인 뒤. 모델을 변경하지 않으면 G01 T01/T03 반복 금지. G02는 실제 입력·출력 동일 계약 유지, backend별 latency 비교와 의미 검출 한계를 분리한다.

## 최종 범위 확정 이후
두 영상 raw 진단 45746373267 완료. G01 기술 범위 SCOPED_PASS, 원래 전체 Gate BLOCKED. 독립 G02 CPU 비교 개발을 허용하되 G01 전체 PASS 주장 및 통합 인수 금지. 동일 frozen fixture/모델/threshold, 새 GT 누락 0을 상대적 배포 기술 검수로 적용하고 절대 의미 누락은 공개 기록한다. G03 실제 target criterion remains strict. Reference G01_ACCEPTANCE_SCOPE_KO.md.

## G02 CPU actual result
45748461194 SUCCESS, T06 CPU scoped PASS; 800 raw timing samples and 40 raw/71 paired / no new GT loss. Full G02 BLOCKED due G01 full/rights; T05 not run. G03 independent design/implementation preview docs/G03_NEXT_WORK_PREVIEW_KO.md. No main merge.
