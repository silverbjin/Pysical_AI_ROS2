# 14.3 — CPU 추론 엔진 비교 (실제 CI CPU 실측 완료, WSL2 별도)

> 출고 상태(2026-11-26): [최신 인수 원장](CH14_ACCEPTANCE_LEDGER.md), [출판 QA](reports/G09_RELEASE_CLOSEOUT_QA_20261126_KO.md) 우선. 아래 기존 checkpoint는 역사적 증거이며, G09 WSL2 L3는 14.9의 네 선택 경로에만 해당합니다. 전체 출고 HOLD, 권리 및 범위 승인 필요. 실제 실행 PIN은 G09_WSL2_OWNER_ACCEPTANCE_KO.md를 참조합니다.

목표: 기존 YOLO ONNX의 의미적 품질을 유지하면서 ORT CPU와 OpenVINO CPU의 실행 비용을 비교한다. GPU/실제 HW 불필요. 검증된 CPU+export 환경에 `python -m pip install --require-hashes --no-deps -r requirements/openvino.lock.txt` (CP312 Linux x64 only), 이후 `python -m pip check`. 기본 CPU lock 변경 없음. G01의 모델/고정 20개 fixture를 권리 확인 후 준비한다. `python python/ov_inference.py --onnx /absolute/model.onnx --sha256 ACTUAL_SHA --image /absolute/image.jpg --output evidence/ov_sample`. 비교: `python python/compare_backends.py --onnx /absolute/model.onnx --sha256 ACTUAL_SHA --fixtures /absolute/manifest.json --images /absolute/images --output evidence/g02 --threads 2`. CI는 frozen fixture SHA와 G01 exact ONNX SHA 또는 fresh PT parity를 강제한다. 동기 단일 request, batch1, FP32, 2 threads, 10 warmup/100 measured each mode/engine/model; alternating engine order. Model API time: preprocessed tensor -> validated host output, API/copy 포함; end-to-end in-memory: BGR preprocessing/NMS 포함, disk/ROS 제외. sequential_fps=1000/mean_ms, 실제 동시 처리량 아님. 결과 CSV/JSON/PNG를 비교한다. 속도 향상 자체는 필수 성공 조건이 아님. 모든 20개 raw allclose, 1:1 box/score, exact GT hit sets, no new miss, blank and invalid input checks. G01 absolute semantic failure retained. TensorRT T05 및 FP16/INT8 실행 없음; INT8은 이론. WSL2 owner 별도.

## 실습 순서 (Ch14 루트, 검증된 Python3.12 CPU 환경)
1. 기존 CPU 환경 활성화 및 source overlay. OpenVINO 두 wheel만 추가. pip check 오류 시 중단한다.
2. 고정 영상은 `python scripts/g01_select_coco.py /tmp/ch14-coco`로 준비한다. 다운로드/라이선스/고정 SHA 검사; 이미 존재하는 출력 경로 덮어쓰기 금지.
3. 사용자 권리 확인 후 `python scripts/fetch_models.py yolov8n --cache /tmp/ch14-models --fetch --acknowledge-agpl`로 모델 확보. s도 동일.
4. 실제 변환: `python python/export_yolo.py --manifest models/model_manifest.json --cache /tmp/ch14-models --model yolov8n --output /tmp/ch14-v8n --threads 1`.
5. export.json에서 actual onnx_sha256을 읽고 아래의 ACTUAL_SHA 및 PT_SHA에 넣는다. G01 T04의 기존 n ONNX SHA e8950e7e6edc29ee614a027ee7a07aa492afbda7f24faad049972be5b7c96546, s 6b213b04c58fc0df0039d59f00b665b727943ebed2a6a393727a2423a95e50e9. 재생성 SHA가 다르면 실제 PT 원본 모델로 해당 artifact를 재검증한다. 예시는 n (s는 모델명·SHA 교체).
```bash
python python/compare_backends.py \
  --onnx /tmp/ch14-v8n/yolov8n.onnx --sha256 ACTUAL_SHA \
  --prior-sha e8950e7e6edc29ee614a027ee7a07aa492afbda7f24faad049972be5b7c96546 \
  --pt /tmp/ch14-models/yolov8n.pt --pt-sha PT_SHA \
  --fixtures /tmp/ch14-coco/manifest.json --images /tmp/ch14-coco/images \
  --output evidence/g02_n --threads 2 --warmup 10 --iterations 100
```
ACTUAL_SHA/PT_SHA are placeholders for real hash, not shell variables. For direct CLI on other fixture use scope only, not G02 fixed-fixture acceptance. No claim of local WSL2 run. CI actually executes all three CLIs via g02_cpu_compare.sh. Use `PYTHONPATH` for source execution if package not installed.
6. OpenVINO sample CLI creates detections.json + annotated.jpg locally; don't publish third-party images/weights. `benchmark.json`, model_api.csv, end_to_end.csv, plots and parity.json compare engine behavior.
## 실측 결과 및 과제
Run 45748461194 PASS, 800 samples, actual CPU AMD EPYC 7763 4 logical affinity, both 2 threads. n API ORT68.139 / OV60.350 ms, E2E70.031/62.314 ms. s API184.577/170.960, E2E185.820/172.649. Explain why average improvement differs from P95 and max, and why n vs s affects 10Hz scheduling. n precision/recall .8667/.40625, s .8780/.5625 identical ORT/OV. All raw 40/40 and 71 paired, new GT miss0; original required n14/16, s15/16 remains FAIL, no threshold change. Student exercise: calculate mean, P95, max and sequential FPS from raw CSV, identify latency tails, verify per-image GT identity rather than count. Full report [G02_CPU_EXECUTION_REPORT_KO.md](reports/G02_CPU_EXECUTION_REPORT_KO.md). TensorRT/FP16 NOT_RUN, INT8 theory. CPU scope accepted, full gate and main HOLD.
