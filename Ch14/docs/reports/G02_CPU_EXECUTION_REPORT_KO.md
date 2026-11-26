# G02 ORT CPU ↔ OpenVINO CPU 실제 비교 개발 및 검수 보고서
## 결과와 증거
Run [45748461194](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45748461194), source a9d7e7d3514a2a9ab2698ef66dc8f91b5fd81bbd, job 139670157282, artifact [15084542683](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45748461194/artifacts/15084542683). ZIP SHA256 93403937224455a1450cd716b81ef92db68d969ad6e5cdb6b6a2140d60a52483, 27/27 internal hashes verified, workflow SUCCESS stage complete exit0. 265s elapsed from creation to completion. T06 CPU scope PASS, G02 SCOPED_PASS (full gate pending G01 full and release); T05 NOT_RUN, WSL2 NOT_RUN. Original G01 absolute semantics FAIL retained. No main merge.

## 구현·디버깅 및 재사용
Code 14-6 ov_inference.py and ov_backend.py: native openvino.Core explicit CPU, static FP32 names/shape/types, actual execution devices/precision/threads/streams checked, request infer synchronous. Same canonical G01 preprocessing/NMS/COCO class map. compare_backends.py: fixed 20 images, alternating synchronous engine order, 10 warmups and 100 measured each model/mode/engine. 800 samples total. First run 45748144504 FAIL at CPU-specific wheel validator used on 2-wheel optional overlay; artifact 15084171697 internal 6/6. New standalone verifier checks package set/version/SHA/root metadata, local regression 1/1 and actual CI 1/1; existing G00 unchanged. Actual optional wheel metadata: openvino requires numpy>=1.16.6,<2.3.0, openvino-telemetry>=2023.2.1, packaging; telemetry no Requires-Dist. Both Apache license classifier, not whole-book legal clearance. Actual graph 199 distributions/185 edges/zero errors, pip check PASS. Base 45-wheel lock hash identical to G00. Target regressions 3/3. Cache HIT; no G01 T01/T03 rerun. Third-party weights/ONNX binaries not persisted; fresh n/s export once because previously evaluated binaries not retained; SHA differed from G01 T04, thus fresh 40-image-pair PT/ORT raw parity and 71 matched boxes were needed, not evidence reuse. Both engines consume same actual byte-identical ONNX within G02. Frozen fixture exact manifest 20/20. All four raw CSVs saved with original SHA and Git blob identities, independently recomputed all stats and fixture order.

## 환경
Ubuntu 24.04 Python3.12 ROS Jazzy container; AMD EPYC 7763 CPU affinity [0,1,2,3], threads2 each, ORT 1.20.1 CPUExecutionProvider inter-op1; OV 2025.1.0 CPU FP32 LATENCY stream1 pinning false. Model API includes runtime call/input-output host API/copy/validation, no disk, preprocess, NMS, GPU transfer. In-memory E2E includes preprocess/infer/NMS; no ROS/sensor/render/disk. Sequential FPS reciprocal mean, not concurrent throughput.
| model | mode | backend | mean ms | P50 | P95 | P99 | max | std | sequential FPS |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| yolov8n | model_api | ort | 68.139 | 67.734 | 68.885 | 74.998 | 85.124 | 2.150 | 14.676 |
| yolov8n | model_api | ov | 60.350 | 59.730 | 67.272 | 72.702 | 75.837 | 4.378 | 16.570 |
| yolov8n | end_to_end | ort | 70.031 | 69.690 | 71.657 | 79.217 | 79.293 | 1.518 | 14.279 |
| yolov8n | end_to_end | ov | 62.314 | 64.057 | 69.316 | 72.641 | 73.316 | 3.744 | 16.048 |
| yolov8s | model_api | ort | 184.577 | 183.526 | 189.180 | 200.254 | 205.323 | 3.387 | 5.418 |
| yolov8s | model_api | ov | 170.960 | 171.307 | 180.499 | 183.007 | 185.733 | 5.037 | 5.849 |
| yolov8s | end_to_end | ort | 185.820 | 185.447 | 188.575 | 193.795 | 193.879 | 1.724 | 5.382 |
| yolov8s | end_to_end | ov | 172.649 | 172.942 | 181.905 | 191.432 | 204.271 | 6.054 | 5.792 |
Mean latency reductions model API n11.43%, s7.38%; E2E n11.02%, s7.09%. E2E P95 reductions n3.27%, s3.54%. E2E max s ORT193.879 vs OV204.271 ms; OV std larger, no universal speedup claim. Input 10Hz/100ms nominal period: n within period in this offline run, s mean >period; no ROS freshness/heartbeat proof. Default G03 ORT CPU, n model, optional OV after same contracts. No changing baseline threshold or model.

## 수치 및 의미 품질
| model | raw allclose | pair | unmatched | min IoU | max score diff | max raw abs | mean raw abs | GT hits ORT/OV | required ORT/OV |
|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| n | 20/20 | 30 | 0 | .9999954343 | 9.536743e-7 | .0038146973 | 1.784166e-6 | 26/26 | 14/14 of 16 |
| s | 20/20 | 41 | 0 | .9999987402 | 9.536743e-7 | .0031433105 | 1.461261e-6 | 36/36 | 15/15 of 16 |
FP32 atol=1e-3/rtol=1e-3 unchanged, combined tolerance. Box IoU>=.95, score difference<=.02. 64 GT labels: exact per-image class-wise one-to-one greedy GT sets independently recalculated from existing G01 ORT, new ORT and OV: equal across all 20 per model. No added GT miss/hit. Precision/recall n .866667/.40625; s .878049/.5625 both ORT/OV (small fixture, not mAP). Baseline misses n 463199 and 392818, s 463199 unchanged. Both blank synthetic empty; six invalid contract tests per model pass (missing model, SHA, non-CPU, shape, dtype, NaN); actual 14-6 sample CLI detects bus 0.9233854413, coordinates [0,1.4906616211,408.3759155273,637.2526855469]. No full semantic pass. G01 scope reference unchanged. 
## 한계 및 다음 작업
Actual runtime comparison performed, not L1/L2 or WSL2 L3. T05 TensorRT, FP16 not implemented/executed in CPU request; INT8 theory only. No new training. No hardware. No approval for main merge due to full G01/release/legacy document-check blockers. G03 independent design/implementation can begin from accepted CPU scope, actual Gazebo strict required target zero-miss, valid RGB-D/TF/time, latest-slot and stale guard, no inherited semantic waiver. No repetition of G02 except affected source/fixture/lock. Existing legacy workflow error separate. Artifact expires after configured retention; preserve raw CSVs, per-image derived evidence and receipt in git and provide original ZIP to user. 
