# 14.5 파라미터 및 Hot Swap 실습 (검증 후보)
G03 기반 CPU ORT. 모델 파일/레지스트리는 절대 경로, publisher PT 해시와 권리 확인 후 로컬에서 생성; 모델/참조 tensor 재배포 금지. `python scripts/g04_prepare_registry.py --cache /absolute/models --output /absolute/registry --manifest models/model_manifest.json --receipt /absolute/registry-receipt.json`. 실제 설치: `colcon build --packages-select ch14_ai_common ch14_ai_interfaces ch14_ai_perception ch14_simulation` (검증된 venv 사용). `source install/setup.bash`. 
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
서비스 accepted는 요청 등록이며 교체 완료가 아니다. heartbeat swap_event의 request_id/state/generation/model_sha256으로 terminal 확인. 잘못된 후보는 이전 모델 유지. YAML config 기본값보다 명시 CLI launch override 우선. `profile:=sim assets:=/absolute/ch14-assets` (G03 scene fetcher), 기본 headless, gui:=true 선택 미검증. replay는 실제 외부 DDS 입력; bag replay G06 별도. 파라미터/모델/ROS 계약 검수 후 결과 갱신. 
