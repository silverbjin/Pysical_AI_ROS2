# 13.5 실행 원장

구현 시작: `a077ff2b15145e58fca8319595215d0db41cf905`, 브랜치 `feat/ch13-section-13-5`.
작업 범위: 사용자 승인 상세 설계·구현 계획. 네이티브 단일 작업자.
아래 기록은 초기 구현 시험이며 G1~G5 실제 엔진 인수 완료가 아니다.

## G0

- 기존 설치 감사: `python Ch13/scripts/verify_all_13_4.py --audit-install-prefix Ch13/ros2_ws/install13_4_completion_f8c0bed5-cdac-43d8-81ff-84ab88360cdb`.
- 결과: 기존 6패키지 소스/설치 byte 감사 성공. 원본 JSON: `g0-install-audit.json`, stderr: `g0-install-audit.stderr`.
- 기존 소스 시험: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test -q`.
- 결과: **374 passed, 224.38초**, `g0-pytest.log`.
- 원격 조회: 일반 sandbox의 네트워크 연결 실패 뒤 허용된 네트워크 조회로 재확인했다. 동명 13.5 원격 브랜치 없음. main은 `e83fe949553d9a2217c274c0bab23bf8f0713241`. 원격 변경은 하지 않았다.

## Task 1

- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test -q`.
- 최초 `task1-red.log`: 3 failed/9 fixture errors. 누락 샘플 모듈과 신규 IDL 때문에 실패했다. 모델 계약 시험을 더하고 fixture 부재를 시험 본문에서 드러내도록 고쳤다.
- 재확인 `task1-red-confirmed.log`: **15 failed**, 새 샘플/모델/IDL 부재. 무관한 의존성 실패를 의도한 RED로 세지 않았다.
- 순수 코어 GREEN: 같은 명령에서 `test_samples.py test_model.py` 선택, **12 passed, 3.23초**, `task1-core-green.log`.
- 빌드 명령: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`.
- 기존 ROS/외부 MuJoCo underlay와 지정 venv만 source한다. 이전 장·기존 13.4 overlay를 새 빌드의 의존성으로 사용하지 않는다.
- 전용 build/install/log 접미사는 이 실행 UUID와 같다. `task1-build.log`에 실제 결과를 보존한다. 신규 센서 패키지는 아직 작성 전이므로 이 단계는 7패키지 빌드다.
- 빌드 결과: **7 packages finished, 6분52초**. 기존 제어기 deprecation 경고 외 빌드 실패 없음.
- 전체 소스 회귀: 기존 세 시험 경로+신규 navigation/test, **389 passed, 202.34초**, `task1-all-source.log`.
- colcon 시험: `--packages-select integrated_robot_navigation integrated_robot_interfaces`, test-result **15 tests / 0 errors / 0 failures / 0 skipped**, `task1-package.log`.
- 새 설치본 감사: 기존 6패키지 감사+신규 모듈이 실제 새 prefix에서 로드되는지 및 Python byte 일치를 검사해 통과했다. `task1-install-audit.json`에 모듈·기존 .so 경로와 소스 SHA256를 보존한다.
- 이 시점에는 엔진을 기동하지 않았다. 실제 crawl/Nav2 성공을 주장하지 않는다.

## 환경·결정

- WSL은 일반 사용자 jinho/uid1000로 실행한다. sandbox WSL 접근 거절에만 도구 실행 허용을 사용했으며 sudo/관리자 권한을 사용하지 않았다.
- 기존 `/etc/wsl.conf`의 알 수 없는 키 경고를 관측했다. 범위 밖 설정을 수정하지 않았다.
- Windows→WSL 중첩 인용 명령에서 증거 경로 변수가 사라진 실행은 permission denied로 중단됐다. 같은 환경을 별도 shell 파일에서 읽으면 올바른 경로임을 확인해 이후 plan-local 실행 파일을 사용한다. 이 실행 오류를 제품 시험 FAIL/PASS로 계산하지 않는다.
- 기존 제어기 빌드의 deprecated API 경고는 원본 로그에 남기고 새 기능 때문에 관련 없는 소스를 변경하지 않는다.
- 커밋 시 `.git/index.lock` 때문에 실패했다. Windows/WSL의 Git 프로세스·열린 핸들이 없고, 0바이트 잠금의 시각이 16분 넘게 변하지 않았음을 확인했다. 삭제하지 않고 `.git/index.lock.stale-85670137-e73c-4c72-bcb2-0c73e755088b`로 보존해 정상 Git 동작을 복구했다. 실패한 커밋 뒤 자동 완료 원장에 같은 BASE/HEAD가 들어간 항목은 미완료로 정정하고 실제 커밋 뒤 재시험한다.
- pytest 원본 실패 로그에는 프레임워크가 출력한 줄 끝 공백이 있다. 원본 증거를 정리해 바꾸지 않고 보존한다. 소스·문서의 whitespace 검사는 raw evidence를 제외한 별도 검사로 적용한다.

## Task 2

- 시작 기준/Task 1 완료 커밋: `01ad4986cf740673dd8452c111b589dde4805a97`.
- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_leg_kinematics.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_support.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_center_of_mass.py -q`, **15 failed**, `task2-red.log`.
- 최초 GREEN: navigation/test 전체 **30 passed**, `task2-green.log`. 전진 기구학은 별도 MuJoCo native 모델의 8자세×4발과 대조했다. 이는 물리 step/ROS/보행 시험이 아닌 오프라인 FK 교차검사다.
- 자체 검토에서 실제 thigh 상한 4rad와 atan2 주값 범위 차이를 발견했다. q=(0,3.8,0.4)의 유효 자세가 IK에서 거절되는 것을 `task2-angle-wrap-red.log`로 재현했다.
- 최소 수정: 원래 관절 한계 안의 2π 동등 해를 열거하고 직전 자세에 가까운 해를 선택한다. 작업 공간·관절 한계를 clipping해 통과시키지 않는다.
- 수정 GREEN: 전체 navigation/test **31 passed, 3.96초**, `task2-angle-wrap-green.log`.
- 수정 전 패키지 결과 `task2-package.log`와 소스 실행 `task2-all-source.log`는 최종 수정본 증거로 재사용하지 않는다. 수정 후 고정 소스로 `task2-fixed-*`에 재빌드·시험·감사를 수행한다.
- 수정 후 전체 소스 회귀: **405 passed, 202.55초**, `task2-fixed-all-source.log`.
- 수정 후 패키지 시험: **31 tests / 0 errors / 0 failures / 0 skipped**, `task2-fixed-package.log`. 새 설치본 byte 감사도 통과했으며 `task2-fixed-install-audit.json`에 해시를 보존한다.
