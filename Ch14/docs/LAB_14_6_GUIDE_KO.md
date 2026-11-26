# 14.6 성능 모니터링 실습 — 실제 CPU 검증 범위

> 출고 상태(2026-11-26): [최신 인수 원장](CH14_ACCEPTANCE_LEDGER.md), [출판 QA](reports/G09_RELEASE_CLOSEOUT_QA_20261126_KO.md) 우선. 아래 기존 checkpoint는 역사적 증거이며, G09 WSL2 L3는 14.9의 네 선택 경로에만 해당합니다. 전체 출고 HOLD, 권리 및 범위 승인 필요. 실제 실행 PIN은 G09_WSL2_OWNER_ACCEPTANCE_KO.md를 참조합니다.

코드14-13 `python/profiler.py` → `ch14_ai_common/profiler.py`. 단조 벽시계는 처리시간, ROS clock은 메시지 stamp age, RTF는 sim/wall 비율입니다. `published()`는 실제 성공 발행 후 호출. Bounded history와 fake-clock 회귀에서 NaN/역행을 거부합니다.

## 준비
G04까지 검증한 CPU venv/ROS Jazzy/Harmonic을 활성화합니다. Ch14/ros2_ws에서 `python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_simulation ch14_performance_monitor --cmake-args -DPython3_EXECUTABLE="$(command -v python)"`, 설치 setup.bash source. 고정 G03 scene assets, 기존 G01 publisher PT hash 검증 및 ONNX export/receipt를 사용. 원본 모델/외부 자산 권리 확인, 재배포 금지. WSL2 최종 실행은 아직 미검증. CI와 동일 source는 595e88a23856c9c791c227a189ea90388e0bb208.

## 관측
이미 실행 중인 인지 시스템과 같은 ROS_DOMAIN_ID에서 별도 terminal:
```bash
ros2 topic hz /perception/detections
ros2 topic bw /camera/color/image_raw
ros2 run ch14_performance_monitor monitor_node --seconds 60 --out /tmp/ch14_observer.json
ros2 run rqt_plot rqt_plot /debug/inference_latency/data /debug/result_age/data /debug/heartbeat_interval/data
```
Debug topics ms Float32, /diagnostics와 기존 /perception/diagnostics. RQt GUI 및 CLI hz/bw 자체 WSL2 현장 미검증. Independent observer count와 source count를 비교. 같은 node-local ROS clock age와 wall pipeline은 다른 지표.

## 실제 A/B/C 비교
Ch14 루트에서 실행. 아래 PT, ONNX, ASSETS를 실제 검증 절대 경로로 지정하고 SHA를 해당 export receipt에서 읽습니다. 새 output directory 사용 (script creates A/B/C children). 다른 실습을 동시에 실행하지 않습니다.
```bash
export GZ_PARTITION=ch14_g05_lab
PT=/absolute/models/yolov8n.pt
ONNX=/absolute/exports/yolov8n.onnx
ASSETS=/absolute/ch14-assets
SHA="$(sha256sum "$ONNX" | cut -d' ' -f1)"
OUT="$(mktemp -d "$HOME/ch14-g05.XXXXXX")"
python scripts/g05_actual_compare.py --pt "$PT" --onnx "$ONNX" --sha256 "$SHA" --assets "$ASSETS" --out "$OUT" --profiles ABC
```
ONNX SHA는 기존 export receipt와 사전 대조, PT는 pinned publisher만. CI actual image via scripts/g05_ci.sh; GUI 별도. A Torch CPU sync, B ORT CPU sync, C ORT CPU async, D optional TRT N/A. 각 10 actual output warmup 후 60 wall sec, fixed scene. Raw metrics.csv, callbacks.csv, resources.csv, observer.json, result.json 및 comparison.json/4 plots. 자세한 수치 [G05_EXECUTION_REPORT_KO.md](reports/G05_EXECUTION_REPORT_KO.md). 실제 CI 660 emissions/660 independent receipts, A/B/C inference mean90.782/78.406/82.670ms, heartbeat miss16/7/0. A/B local age is not comparable proof of actual freshness because sync executor /clock callbacks may lag; output interval distinct. CPU resource tradeoff and input synchronization bottleneck explain why fast model does not imply higher FPS. G04 latest shutdown regression remains HOLD, G05 three actual launches clean. No WSL2 L3 or full release claim.
