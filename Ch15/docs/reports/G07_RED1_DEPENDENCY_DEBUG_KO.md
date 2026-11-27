# G07 RED1: Python 의존성 경계 검수

- 실제 CI [45952688381](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45952688381), job 140351950578, artifact 15177686113, source 96c924fc297ff51ef0fa8a0fe2c4d5fb0f74beb3.
- ZIP SHA256 1b5fdad774409b5e212ae6945262a0db09e0d74a95eb4e014edd62cef95d8856, 내부 6/6 독립 확인. 3개 package build 19.4s, XML/URDF 설치 성공. pip check exit nonzero: `python-dateutil 4.0.0 requires tzdata, which is not installed.` Unit 및 물리 스텝 NOT_RUN.
- 원인: 전체 Ch14 lock에서 독립 실험 의존성만 추출하는 과정에서 전이 의존 tzdata 제외. NumPy는 시스템 site-packages에서 만족 처리되어 wheel 해시 설치를 직접 확인하지 못함.
- 수정: 기존 Ch14 CPU lock의 tzdata exact hash 재사용, 새 venv에 --ignore-installed --require-hashes --no-deps 적용. pip check와 모든 lock 배포판 버전/venv 위치 확인. 시스템 apt 환경 변경 없음. 물리 모델, 제어기, 기준값 변경 없음.
- 재검수: 아직 실행하지 못한 G07 전체 검수만 수행. G04~06 재검수 금지. 결과 전 G07 인수 HOLD.
