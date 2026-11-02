# SECTION 1.6 — Python 3.12 첫 번째 ROS 2 노드 코드 리뷰

- 작성: 2026-10-20 KST
- 기준 main: `f5aed1d250563efc298e717559497db3b4f205c7`
- 작업 브랜치: `feat/ch01-section-1-6`
- 원고 1.6.1~1.6.4: `SimpleController` 클래스, 타이머, OOP, `rclpy.spin`, `test_node`.
- 판정: **MANUSCRIPT_ALIGNED / STATIC_REVIEWED / ROS2_RUNTIME_NOT_RUN**.

## 1. 주교재와 저장소 코드의 정확한 연결

| 원고 항목 | 실제 기준 파일·심볼 | 분석 |
|---|---|---|
| 1.6.1 SimpleController | `Ch01/robot_ws/src/my_robot_controller/my_robot_controller/simple_controller.py` | `Node` 상속, 이름 `my_robot_node`, 1.0초 타이머 |
| 1.6.3 console_scripts | `Ch01/robot_ws/src/my_robot_controller/setup.py` | `test_node = my_robot_controller.simple_controller:main` |
| 빌드 타입·의존성 | `Ch01/robot_ws/src/my_robot_controller/package.xml` | `ament_python`, `rclpy`, `std_msgs` |
| 실행파일 설치 디렉터리 | `Ch01/robot_ws/src/my_robot_controller/setup.cfg` | `lib/my_robot_controller` 설정 존재 |
| 보조 예제(원고 본문 아님) | `Ch01/ref/my_first_package/simple_node.py`, `robot_ws/src/robot_monitor` | 기존 리뷰에서 주 대상으로 삼았으나 **이번에는 부록**으로 명시 |

원고의 `Count: N` 메시지와 실제 코드의 `Heartbeat: N`은 다르다. **실습의 기대 출력은 저장소 실제 코드인 `Heartbeat: N`을 기준으로 한다.** 원고 1.6.4에 인쇄된 실행 예시도 Heartbeat이므로 결과 예시와 일치한다.

## 2. 정적 코드 리뷰

| ID | 우선 | 관찰 | 판정·개선 |
|---|---|---|---|
| 16-01 | High | 이전 리뷰의 주대상을 `ref/simple_node.py`로 오인 | **문서 수정:** `my_robot_controller/simple_controller.py`를 핵심으로 변경 |
| 16-02 | High | 원고 `source install/setup.` 오탈자 | **가이드 수정:** `source install/setup.bash` 사용 |
| 16-03 | Medium | 원고 생성 초기 `simple_controller` vs 실제 최종 `test_node` | **가이드 수정:** `test_node` 실행 및 `ros2 pkg executables`로 확인 |
| 16-04 | Medium | 원고 1.6.1 메시지 `Count`와 실제 `Heartbeat` 상이 | **정정:** 실행 로그는 실제 source 문자열로 제시 |
| 16-05 | Low | `std_msgs` 의존성이 선언되지만 `simple_controller.py`에서는 import하지 않음 | 학습용 명시 의존성. 후속 정리 가능 |
| 16-06 | Medium | 실제 `rclpy.shutdown()`의 예외·중복 종료 동작을 Jazzy에서 검증하지 않음 | 종료 후 stack trace·exit code 실측 필요. 필요 시 `rclpy.try_shutdown()` 패턴 검토 |
| 16-07 | Medium | 타이머 콜백 INFO는 토픽 송신이 아님 | `create_publisher()`가 없어 `ros2 topic echo`로 Heartbeat은 수신 불가; 로깅과 publish 구분 |

## 3. 기존 브랜치에 포함된 보조 수정과 스코프

이 브랜치는 앞선 검토에서 `Ch01/ref/setup.cfg` 누락 수정, `ref/README.md` 재현 절차 보강, `robot_monitor/battery_node.py` 0% 이후 프로세스 종료 수정이 이미 들어 있다. **이번 1.6절 원고에서 핵심 구현으로 요구한 변경이 아니라 이전부터 포함된 보조 실습 수정이다.** PR 검토 시 별도 판단할 수 있도록 명시한다. `my_robot_controller/simple_controller.py` 자체는 원고와 핵심 흐름이 일치하므로 불필요한 재구현 없이 유지했다.

## 4. 검증 매트릭스

| 검증 항목 | 상태 | 비고 |
|---|---|---|
| `Node` 상속, logger, 타이머, `spin`, entry point 소스 대응 | **REVIEWED** | 실제 Python 소스·setup.py 열람 |
| `test_node` 이름, 로그 `Heartbeat` 확인 | **REVIEWED** | 소스 문자열 기준; 실행값 아님 |
| 기본 노드 Python 컴파일 | **NOT_RUN** | 대상 수정 없이 정적 확인 |
| `colcon build --packages-select my_robot_controller` | **NOT_RUN** | ROS 2/colcon 미설치 |
| `ros2 run my_robot_controller test_node`, `ros2 node list` | **NOT_RUN** | Jazzy executor/DDS 없음 |
| 실제 1Hz 로그 3회, 종료 후 Node 소멸 | **NOT_RUN** | 수동·자동 Acceptance 필요 |

과거 보조 가상 배터리 오프라인 검사 기록은 실 ROS 2 실행 증거가 아니며 1.6 주교재 노드의 검증 합격으로 전용하지 않는다.

## 5. 재현 및 Acceptance

```bash
source /opt/ros/jazzy/setup.bash
mkdir -p ~/ch01_lab_16/src
cp -a ~/Pysical_AI_ROS2/Ch01/robot_ws/src/my_robot_controller ~/ch01_lab_16/src/
cd ~/ch01_lab_16
python3 -m compileall -q src/my_robot_controller
colcon build --symlink-install --packages-select my_robot_controller
source install/setup.bash
ros2 pkg executables my_robot_controller
ros2 run my_robot_controller test_node
```

**ACCEPT:** 생성된 entry point가 `test_node`로 보이고, `/my_robot_node` 그래프 노드 확인, `Heartbeat: 1`, 2, 3 이상 1Hz 근사 로그 출력, Ctrl+C 후 정상 자원 해제. 상세 실습은 [LAB_1_6_GUIDE_KO.md](LAB_1_6_GUIDE_KO.md). **실측 로그 없으면 판정 NOT_RUN 유지.**
