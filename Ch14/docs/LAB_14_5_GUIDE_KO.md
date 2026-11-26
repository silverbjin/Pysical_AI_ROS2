# 14.5 파라미터 및 Hot Swap 실습 (CPU ORT 실제 검증 완료)
G03 기반 CPU ORT. 모델 파일/레지스트리는 절대 경로, publisher PT 해시와 권리 확인 후 로컬에서 생성; 모델/참조 tensor 재배포 금지. `python scripts/g04_prepare_registry.py --cache /absolute/models --output /absolute/registry --manifest models/model_manifest.json --receipt /absolute/registry-receipt.json`. 실제 설치 (Ch14/ros2_ws): `python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_simulation --cmake-args -DPython3_EXECUTABLE="$(command -v python)"` (검증된 venv 사용). `source install/setup.bash`. 
```bash
ros2 launch ch14_ai_perception robot_ai_system.launch.py profile:=replay \
  model_path:=/absolute/registry/yolov8n.onnx model_sha256:=ACTUAL_SHA \
  model_registry:=/absolute/registry/registry.json
ros2 param get /yolo_detector_node confidence_threshold
ros2 param set /yolo_detector_node confidence_threshold 1.0
ros2 param set /yolo_detector_node confidence_threshold 0.5
ros2 service call /ch14/swap_model ch14_ai_interfaces/srv/SwapModel "{model_id: yolov8s}"
ros2 topic echo /perception/heartbeat
```
서비스 accepted는 요청 등록이며 교체 완료가 아니다. heartbeat swap_event의 request_id/state/generation/model_sha256으로 terminal 확인. 잘못된 후보는 이전 모델 유지. YAML config 기본값보다 명시 CLI launch override 우선. `profile:=sim assets:=/absolute/ch14-assets` (G03 scene fetcher), 기본 headless, gui:=true 선택 미검증. replay는 실제 외부 DDS 입력; bag replay G06 별도. 실제 검증 Run 45755020128, 아래 실행 및 해설 참조. 

## 1. 실행 전 준비
G00의 검증된 CPU venv와 ROS Jazzy underlay를 활성화합니다. Ubuntu24.04/Jazzy/Harmonic, ros-jazzy-rosidl-default-generators, ros-jazzy-rosidl-default-runtime, ros-jazzy-ament-cmake, cv_bridge/vision_msgs/message_filters/tf2_ros/ros_gz_bridge 등 기존 G03 의존성을 갖춥니다. WSL2 실제 인수 전에는 로컬 실행 성공을 보장하지 않습니다. 작업은 Ch14 루트에서 진행. 아래 새 REG 디렉토리는 재사용/덮어쓰기하지 마십시오.
```bash
source /opt/ros/jazzy/setup.bash
# 검증된 CPU venv 활성화 후
cd /absolute/repository/Ch14
CACHE="$HOME/ch14-model-cache"
RUN="$(mktemp -d "$HOME/ch14-g04.XXXXXX")"
REG="$RUN/registry"
# AGPL 등 publisher 조건을 확인하고 동의한 경우에만 다음 2개 fetch 실행
python scripts/fetch_models.py yolov8n --cache "$CACHE" --fetch --acknowledge-agpl
python scripts/fetch_models.py yolov8s --cache "$CACHE" --fetch --acknowledge-agpl
(cd ros2_ws && python "$(command -v colcon)" build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_simulation --cmake-args -DPython3_EXECUTABLE="$(command -v python)")
source ros2_ws/install/setup.bash
python scripts/g04_prepare_registry.py --cache "$CACHE" --output "$REG" --manifest models/model_manifest.json --receipt "$RUN/registry-receipt.json"
SHA="$(python -c 'import json,sys;print(json.load(open(sys.argv[1]))["models"][0]["sha256"])' "$REG/registry.json")"
echo "$REG $SHA"
```
Registry는 로컬 신뢰 파일입니다. 서비스에는 경로가 아니라 승인 모델 ID만 전달. PT/ONNX/ref tensor를 배포하지 않습니다. 이전 CI 모델과 SHA가 다르면 동일 바이너리로 간주하지 않습니다.

## 2. 실제 ROS parameter/swap 검수 재현
CI에서 성공한 script: `python scripts/g04_actual_probe.py --registry "$REG/registry.json" --image /absolute/000000455085.jpg --out "$RUN"`. G01 고정 이미지 455085 SHA 022d2068d525b03a753287c333c09026fe22b9ae6d8071d4e8c757cbed32bdc4 (기존 G01 라이선스/출처). 이 스크립트는 새 scratch registry에서만 실행하고 별도 detector를 띄우지 않습니다. 파일 누락/손상 시험을 위해 s 파일을 잠시 옮기고 복구하므로 실제 운영 모델 cache를 전달하지 않습니다. 실제 installed replay launch/parameter service/model swap/CLI/종료를 자동 검수하고 JSON/log를 저장합니다. 0.0 threshold는 설정 수용만 검사. 실제 영상 .5→1.0→.5는 검출1→0→1. CLI 수동 관찰은 위 launch 명령 실행 후 별도 terminal에서 setup source.
- 정상값/비정상값 혼합은 `/yolo_detector_node/set_parameters_atomically` service로 한 묶음 요청. ros2 param set은 단일 설정 예시; 여러 번 호출은 한 transaction이 아님.
- 실제 hot swap request_id를 기록하고 `ros2 topic echo /perception/heartbeat`의 swap_event와 비교합니다. LOADING 동안 n, DRAINING에서 기존 in-flight 완료, SUCCEEDED에서 s/gen1. FAILED에서는 n/gen0 유지.
- /perception/detections, /perception/image_annotated, /perception/heartbeat, /perception/diagnostics 관찰. `ros2 topic hz`는 수신기 관측이며 source Age와 다릅니다.
- 실제 검수 17 requests(7 정상/10 거부), in-flight snapshot 증거, old emits3 while loading, swap704.046ms, source age max286.909ms, output gap719.808ms(실험 pacing 포함), heartbeat max126.742ms. 공백은 존재하고 이전 모델 출력을 재발행하지 않습니다. Source trace CH14_EMIT, CH14_SWAP와 독립 DDS 기록 비교.

## 3. 실제 Gazebo 통합 실행
```bash
python scripts/g03_fetch_scene_assets.py "$RUN/assets" "$RUN/scene-asset-receipt.json"
ros2 launch ch14_ai_perception robot_ai_system.launch.py profile:=sim \
  assets:="$RUN/assets" model_path:="$REG/yolov8n.onnx" \
  model_sha256:="$SHA" model_registry:="$REG/registry.json"
```
위 launch route는 실제 headless CI에서 검증했습니다. WSL2 GUI는 별도. 독립 검수기는 별도 launch를 스스로 구동하므로 위 launch와 동시에 실행하지 않습니다: `python scripts/g04_sim_launch_probe.py --registry "$REG/registry.json" --assets "$RUN/assets" --out "$RUN"`. 실제 sim 3/3 GT/point, RGB-D alignment .993447, source emit4/max123ms. Sim profile에서 model swap 자체는 재검증하지 않음; replay에서 실증. 실행 종료 Ctrl+C는 해당 launch만; 기존 로봇 프로세스 종료 금지.

## 4. 교육 실습 체크
기본값→YAML→CLI 우선순위 확인, 잘못된 묶음 요청 원자성, threshold snapshot과 generation 구분, model SHA/ref hash 검사, 실패 후보와 기존 활성 모델의 출력 확인, 관측 출력 공백과 데이터 Age 구분. 이전 G03 300ms freshness 계약을 완화하지 않습니다. 전체 장시간 성능은 G05. 보고서 [G04_EXECUTION_REPORT_KO.md](reports/G04_EXECUTION_REPORT_KO.md), 원장 [CH14_ACCEPTANCE_LEDGER.md](CH14_ACCEPTANCE_LEDGER.md).
