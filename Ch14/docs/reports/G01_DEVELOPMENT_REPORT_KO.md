# G01 개발 보고서 — 독립 foundation (미완료)

2026-11-26, 상태 PARTIAL / BLOCKED. G00 CPU 후보 검증 중이며 미확보 YOLO 가중치 및 fixture에 의존하는 실제 시험은 수행하지 않았다. 14-1의 seed/계측·통계 모듈, 14-3의 결정적 미학습 MLP와 ONNX 변환 wrapper, 14-4의 공통 전후처리 및 음성/경계 회귀를 독립 구현했다. 14-1 전체 CLI/실제 모델 측정, 14-2 YOLO export, 14-4 ORT backend/실제 이미지 탐지/parity는 미구현. G01 T01~04 전체 합격 금지.

## 문제 → 설계 → 검증
- 벤치마크: warmup 10회 이상, 실제 측정값만 통계에 넣고 동기화 callback을 전후 호출. 가짜 단조시계 테스트로 측정 경계를 검증한다. 실제 YOLO 모델 속도는 아직 측정하지 않았다.
- 전처리: 640x480 영상을 640x640 letterbox로 바꾸고 BGR→RGB, NCHW FP32 [0,1]로 정규화. 역변환에는 반올림된 실제 x/y scale을 사용한다. class-wise NMS와 동률 입력 순서 보존. 음수 크기/zero score는 탐지로 취급하지 않으며 NaN/shape/type 오류는 명시적으로 거부한다. 테스트 출력은 합성 bbox fixture로 실제 의미 탐지가 아니다.
- MLP: 원고의 9→64→64→6, ReLU, seed14를 그대로 사용. 호출자의 Torch RNG 상태를 보존하고 CPU untrained forward를 실제 확인. exporter는 opset13/정적 IO/CPU provider를 검사한 뒤 동일 입력 100개의 PyTorch/ORT parity를 실행하도록 구현. 현재 환경에 onnx/ORT가 없으므로 export 함수 실행은 하지 않았다. motor_command=False.

## 실제 실행 증거
실행 환경 Debian 13, Python 3.13.5, torch 2.10.0+cpu, NumPy 2.3.5, cv2 4.13.0. 대상 Jazzy/Python3.12 ABI의 대체가 아니다.

`PYTHONPATH="$PWD/ros2_ws/src/ch14_ai_common" python -m pytest tests/test_g01_foundation.py -q`

12 tests passed, 1.47s, exit=0. 원본 로그 `evidence/g01_foundation_local.log`. 실제 Torch forward 및 합성 계약 검수만 SCOPED_PASS. ONNX/ORT/YOLO/ROS/GPU/Docker/WSL2 NOT_RUN. 새로운 ROS 패키지 설치 metadata는 작성했으나 colcon build 미실행. 소스 권리 선언은 배포 전 owner 확정 필요.

## 재개 경계
G00 CPU lock 및 권리·모델 manifest 확인 → 실제 T03 export/parity → 승인 YOLO 자산과 평가 fixture 확보 → T01/T02/T04 전체 검수. 이후 G02. 기존 Ch01~13 또는 main 변경 없음.
