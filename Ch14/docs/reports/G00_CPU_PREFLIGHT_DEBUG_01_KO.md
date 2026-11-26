# G00 CPU preflight — wheel 메타데이터 선택 장애

## 원본 실패
SHA 2a41906353027454bf32357615b53deef3b6cf3c, Actions run [45739048641](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739048641), job 139639251040, FAIL. [원본 artifact 15080153039](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739048641/artifacts/15080153039), 33694 bytes, zip SHA256 bc7c9d67c49a65efe53e33542562b2109f4b167135f64895e29b4da0d88c17f8. apt 및 CPU wheel 다운로드 성공, hash_lock에서 ValueError: Invalid wheel metadata: setuptools-84.2.1-py3-none-any.whl. 설치/ABI/ONNX smoke 미도달. 원본 artifact 삭제 금지.

## 원인 가설과 단일 수정
기존 구현은 모든 경로의 .dist-info/METADATA를 검색해 정확히 1개가 아니면 실패했다. setuptools의 vendored package 내부 metadata가 함께 들어가는 구조를 잘못 처리했을 가능성이 높다. 실제 실패 wheel의 zip 내부 목록은 첫 run에 기록되지 않아 구조는 아직 미확정. root-level dist-info만 선택하며 nested metadata 목록을 출력해 다음 CI에서 가설을 확인한다. root-level 복수/누락은 계속 거부. 버전·시험 기준 변경 없음.

## 회귀 실험
합성 wheel로 nested metadata 무시, root 복수 거부, 필수 패키지 누락 거부를 검증. 로컬 unittest 3/3 PASS, 0.008s, exit 0. 실제 dependency 다운로드나 ABI 통과로 해석하지 않는다. CI 재실행은 최초 실패 수정 후 1회만. 다운로드를 다시 수행하는 이유는 최초 wheelhouse가 일회용 컨테이너 내부에 있어 artifact에 저장되지 않았기 때문이다. 다음 실패가 있으면 최초 경계 확인 후 진행.
