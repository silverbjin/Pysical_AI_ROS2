# 2.3절 — 코드 수정 및 정적 테스트 보고서

- 기준: main@7b7c10f25194c770d0adc80b3f02b5493da94c8a (2026-10-20 KST, 2차 검토)
- 수정 브랜치: fix/ch02-section-2-3-static
- 판정: STATIC_REVIEWED + SYNTAX_PASS + STATIC_TEST_PASS / BUILD·ROS_RUNTIME NOT_RUN

## 1. 발견 문제와 수정

- 원인·영향: 고주기 Pose마다 로그를 출력해 콘솔이 과다 출력됨
- 조치: time.monotonic 기반 0.5초 로그 제한, 구독 객체 더미 표현식 삭제
- 관련 소스: turtle_pose_subscriber.py
- 추가 테스트: Ch02/tests/test_section_2_3_static.py

## 2. 실제 정적 검증 기록

- 절별 테스트: AST/py_compile PASS; 구독 토픽 불변·로그 제한 조건 정적 검사 PASS
- 실행 환경: Python 3.13.5, ROS 2/colcon 미설치 환경
- GitHub Blob SHA와 정확히 일치하는 로컬 검증 사본 14개 파일 확인: INTEGRITY_PASS
- 검증 사본 Python 11개 파일 ast.parse 및 py_compile: SYNTAX_PASS
- Python 순수 함수 경계값, ROS 통신 계약의 소스 검사, XML/srv 구조, Bash -n 및 CLI 무설치 종료 경로 검사: 8개 절 STATIC_TEST_PASS
- 사용한 로컬 검증 도구: /mnt/data/ch02_static_validation/verify_ch02_static.py (작업 세션 내부 경로; GitHub 저장소에는 별도 추가하지 않음)

### 출력 발췌 (실제 로컬 검사)

```text
INTEGRITY_PASS 14 files
SYNTAX_PASS 11 Python files
SECTION_2_3 PASS
FINAL: 8 SECTION STATIC SUITES PASS; ROS2 BUILD/RUNTIME NOT RUN
PY_COMPILE_PASS 11
```

### 저장소에 포함한 절별 테스트 재실행

```bash
python3 -m unittest discover -s Ch02/tests -p 'test_section_2_3_static.py' -v
```

- 참고: 위에 표시한 실제 PASS는 SHA 검증된 소스 사본을 대상으로 실행한 **독립 로컬 정적 검증** 결과다. 브랜치 내 unittest 파일은 재실행용으로 추가했으며 해당 파일을 실행한 별도의 CI 결과는 없다.
- ROS 의존성 없이 소스와 인터페이스 구조를 검사한 결과이므로 실제 통신이 된다는 뜻이 아니다.

## 3. 미실행·제한

- 절 고유 제한: 실측 수신·로그 주기는 ROS 실행 후 별도 측정 필요
- colcon build, rosidl code generation, ros2 run/launch, DDS 통신, turtlesim GUI, 실제 E2E: NOT_RUN
- 다른 장의 오버레이 충돌, 메시지 전송률, 서비스 중복 응답, 액션 취소 안전성은 이번 테스트에서 판정하지 않았다.

## 4. 실제 환경 검증 절차

```bash
cd Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_robot_system
```

- 절별 실습 가이드는 Ch02/docs/LAB_2_3_GUIDE_KO.md, 기존 1차 코드 리뷰는 Ch02/docs/SECTION_2_3_REPORT_KO.md 참조.
- 실행 성공 근거가 확보되기 전에는 RUNTIME_PASS나 TASK_PASS를 선언하지 않는다.
- main 직접 Push·기존 병합 브랜치 변경·PR 생성/병합은 수행하지 않는다.
