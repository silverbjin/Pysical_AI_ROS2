# SECTION 1.6 — 기본 ROS 2 노드 코드 리뷰 보고서

- 작성: 2026-10-20 KST / 저장소 `silverbjin/Pysical_AI_ROS2`
- 기준 `main`: `f5aed1d250563efc298e717559497db3b4f205c7`
- 작업 브랜치: `feat/ch01-section-1-6`
- 상태: **STATIC_REVIEW_COMPLETE / FIXES_APPLIED / ROS_RUNTIME_NOT_VERIFIED**
- 분류: `simple_node.py` 주석의 “1.6절”을 따름. `my_robot_controller` 및 `robot_monitor`는 절 번호가 없는 **보조 예제**다.

## 1. 실제 파일·계약

| 소스 및 진입점 | 기대 동작 |
|---|---|
| `ref/my_first_package/simple_node.py` → `simple_node` | 이름 `/simple_node`, 1초 주기 INFO·증가 카운터 |
| `robot_ws/src/my_robot_controller/my_robot_controller/simple_controller.py` → `test_node` | 이름 `/my_robot_node`, 1초 주기 Heartbeat **로그만 출력**, 토픽 발행 없음 |
| `robot_ws/src/robot_monitor/robot_monitor/battery_node.py` → `battery_node` | 이름 `/battery_monitor`, 초기 가상 배터리 100%, 1초마다 10%p 감소, 0%에서 종료 |
| `setup.py`/`package.xml`/`setup.cfg` | ament_python 빌드 및 `ros2 run` 진입점 등록 |

실제 로봇 제어, 배터리 센서 수신, Gazebo, MuJoCo는 해당 소스에 없다.

## 2. 발견 사항과 조치

| ID | 중요도 | 근거 및 실행에 미치는 영향 | 결과 |
|---|---|---|---|
| 16-01 | High | `Ch01/ref`에 `setup.cfg`가 빠져 ROS 2 표준 `lib/my_first_package` 스크립트 배치가 불확실하고 `ros2 run`이 실패할 수 있음 | **수정**: 설치·개발 실행 경로 추가 |
| 16-02 | Medium | `ref/README.md`가 미완성 `git clone <your-repository-url>`에서 끝나 재현 불가능 | **수정**: 패키지 별도 복사·빌드·실행 순서 기재 |
| 16-03 | Medium | 배터리 노드는 0%에서 타이머만 cancel하고 `rclpy.spin()`은 남아 자동 종료되지 않음 | **수정**: `finished` 플래그+`spin_once` 루프로 완료 후 종료 |
| 16-04 | Medium | `battery_node`는 내부 숫자를 조작하며 실제 `/battery_state` 토픽을 읽지 않음 | **문서화/로그 수정**: 모의 배터리임을 명확히 표시 |
| 16-05 | Medium | `robot_ws/src/examples`의 외부 ROS 예제 다수로 전체 빌드 시 의도 밖 의존성·시간 증가 | **가이드**: 3개 패키지만 고립 복사·선택 빌드 |
| 16-06 | Low | `my_robot_controller`·`robot_monitor`의 메타데이터에 TODO 라이선스/설명이 남아 있고 기능 테스트가 없음 | **OPEN**: 저작권자 결정 필요, 테스트 후속 |

`ref/setup.py`의 `simple_node`와 `cmd_publisher` 진입점, `my_robot_controller/setup.py`의 `test_node`, `robot_monitor/setup.py`의 `battery_node` 정의와 Python의 `main` 함수를 대응 확인했다. 세 노드 모두 정상 종료 시 자원 정리 경로를 가진다. 새 배터리 종료 루프의 시간·신호 동작은 실제 ROS 환경에서 확인해야 한다.

## 3. 변경 목록

- `Ch01/ref/setup.cfg` 신규
- `Ch01/ref/README.md` 수정
- `Ch01/robot_ws/src/robot_monitor/robot_monitor/battery_node.py` 수정
- `Ch01/README.md` 신규 색인
- 이 보고서 및 `LAB_1_6_GUIDE_KO.md` 신규

## 4. 검증 구분 (Ch12 방식 준용)

| 검사 | 판정 | Evidence |
|---|---|---|
| 원격 소스 구조·패키지 메타데이터·진입점 | **REVIEWED** | GitHub `main`의 실제 파일 읽기 |
| 타이머/카운터/종료 제어 흐름 | **REVIEWED** | 소스 정적 추적; 실행 값 아님 |
| `python3 -m compileall` | **NOT_RUN** | Python 구문 검증 미실시 |
| `colcon build --symlink-install` | **NOT_RUN** | ROS 2 Jazzy·colcon 없음 |
| `ros2 run`, `ros2 node list`, 로그 주기 | **NOT_RUN** | ROS 그래프 구동 환경 없음 |
| 모의 배터리 10회 감소·exit 0 | **NOT_RUN** | 실제 실행과 종료 코드 확인 필요 |
| `colcon test`/CI/독립 리뷰 | **NOT_RUN** | 기능 테스트 로그 없음 |

리뷰 실행 환경은 Debian 13 / Python 3.13이며 `ros2` 및 `colcon` 명령이 설치되어 있지 않았다. 따라서 **실행 PASS·자동 테스트 PASS를 주장하지 않는다.**

## 5. 재현 및 Acceptance

[LAB_1_6_GUIDE_KO.md](LAB_1_6_GUIDE_KO.md)의 독립 워크스페이스를 먼저 만든 뒤:

```bash
source /opt/ros/jazzy/setup.bash
cd ~/ch01_lab_16
python3 -m compileall -q src/my_first_package src/my_robot_controller src/robot_monitor
colcon build --symlink-install --packages-select my_first_package my_robot_controller robot_monitor
source install/setup.bash
ros2 pkg executables my_first_package
ros2 pkg executables my_robot_controller
ros2 pkg executables robot_monitor
ros2 run robot_monitor battery_node
echo "exit_code=$?"
```

**ACCEPT:** 구문 검사 exit 0, 세 패키지 빌드 exit 0, 모든 실행파일 등록, 1Hz 노드 카운트/Heartbeat 3회 이상, 가상 배터리 잔량 90→0% 열 번 출력 후 **자체 exit 0**, 종료 후 `/battery_monitor` 소멸. 터미널 출력·ROS 버전·Commit SHA를 Evidence로 남겨 판정해야 한다. 이 실행 검증 전에는 **수정 완료 ≠ 실행 검증 완료**다.
