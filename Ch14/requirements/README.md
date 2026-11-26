# G00 CPU 의존성 결정 절차
candidate는 설치 확정 lock이 아니다. Ch12 실제 manifest의 torch2.5.1+cpu/numpy1.26.4를 보존하고 ONNX1.17.0, ORT1.20.1, Ultralytics8.3.162, OpenCV4.10.0.84를 검증 후보로 선정. CPU torch/torchvision 조합은 https://pytorch.org/get-started/previous-versions/ 근거. GPU/OpenVINO 별도 lock은 해당 장치 검증 전 미확정.
실제 CI에서 wheel 다운로드 → wheel별 SHA256 및 정확한 전체 버전 lock 생성 → 네트워크 없는 wheelhouse 설치(--no-index --require-hashes) → pip check → ROS cv_bridge와 NumPy ABI/실제 ONNX smoke. lock 후보는 artifact에서 회수하여 검토하고 immutable CPU lock으로 승격하기 전 release 설치에 사용하지 않는다. 이미지 digest와 apt 패키지도 기록. WSL2 L3 별도.
