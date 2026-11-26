# G00 CPU 환경 후보 검증 실행 설계

## 문제와 가설
Debian13/Python3.13 작업 환경에서 설치 검증을 해도 Jazzy/Python3.12 cv_bridge ABI를 입증하지 못한다. 기존 Ch12의 CPU torch2.5.1+cpu/numpy1.26.4 조합에 ONNX/ORT/Ultralytics 후보를 결합하고 실제 ROS Jazzy 컨테이너에서만 검증한다. GPU, 모델 가중치, 물리 시뮬레이터는 이번 실행에 필요 없다.

## 구현·실행 흐름
ubuntu-24.04 runner → ros:jazzy-ros-base 실제 digest 기록 → apt cv_bridge/vision_msgs → Python3.12 venv → 공식 CPU index torch wheels → PyPI 후보 해석 → 전체 wheel bytes 해시 lock → --no-index --require-hashes 설치 → pip check → bgr8/16UC1/32FC1 cv_bridge round-trip, ROS publisher 생성 → 실제 opset13 untrained smoke export/ORT CPU parity → evidence archive. 해시 고정 전 설치 금지. GPU/NVIDIA 설정 없음. 데이터/YOLO 체크포인트를 다운로드하거나 랜덤 모델을 YOLO 성공으로 처리하지 않는다.

## 검증 경계
CI 결과가 돌아오기 전 NOT_RUN/PENDING. CPU preflight가 PASS라도 G00 전체 승인 또는 G01 완료가 아니다. WSL2 Owner L3와 분리. 실제 dependency lock은 artifact 내용을 검토 후 별도 commit; 실패 시 최초 실패 stage와 로그를 보존하고 동일 반복 금지. base digest/apt 목록은 결과에서 확정한다. CI 결과를 후속 보고서에 기록한다.
