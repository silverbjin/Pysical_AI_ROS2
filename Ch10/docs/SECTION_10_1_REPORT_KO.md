> **사후 보완 (2026-10-21):** 이 문서는 최초 코드 리뷰 시점의 판단을 보존합니다. 이후 소스 수정과 정적 점검은 [SECTION_10_1_FIX_TEST_REPORT_KO.md](SECTION_10_1_FIX_TEST_REPORT_KO.md)를 참조하세요. 기존의 '코드 변경 없음' 기록은 최초 리뷰 당시 상태입니다.

# 10.1절 코드 리뷰 보고서 — 보행 제어 개요와 노드 구조

- 검토일: 2026-10-21 (KST)
- 원고: 첨부된 『Physical AI 실무 가이드』 10장 10.1절
- 원격 기준: `silverbjin/Pysical_AI_ROS2` main, 작업 시작 시점 `bab76f6ca7df0bda6efd8882c1a698561707e51d`
- 검토 대상: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/quadruped_controller.py`, `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/quadruped_controller_ros2.py`, `Ch10/ros2_ws/src/my_quadruped_bot/package.xml`, `Ch10/ros2_ws/src/my_quadruped_bot/urdf/common/robot_properties.xacro`
- 판정: **코드 정적 검토 완료 / 환경 실행 및 Gazebo 물리 검증 미수행 / 종합 승인 보류**

## 핵심 결론

10.1은 실제 보행 성공 판정이 아니라 `/cmd_vel → 보행계획 → 궤적 → IK → 12개 위치 지령 → Gazebo` 계약 이해가 목표다. 원고의 50 Hz 골격과 현행 `quadruped_controller.py`의 100 Hz, `quadruped_controller_ros2.py`의 50 Hz를 구분한다.

## 소스 기준 결함·위험 목록

| 심각도 | 발견 | 소스 근거 및 영향 | 수정 권고 |
|---|---|---|---|
| HIGH | 제어기 진입점·실제 메시지 계약이 원고 골격과 다름 | 원고는 `/joint_commands`의 JointState를 가정하지만 현행 `quadruped_controller.py`는 12개 Float64 `/model/my_quadruped/joint/.../cmd_pos`로 전송한다. 브리지는 후자만 ROS_TO_GZ로 연결한다. | 실습 시작 전에 실제 인터페이스를 도식화하고 `ros2 topic info`로 타입·발행자 수를 확인한다. |
| HIGH | URDF-제어기 기구학 기준 불일치 | `robot_properties.xacro`: hip_offset_y=0.10, hip_length=0.08, thigh=0.25, calf=0.25m; `InverseKinematics`: l1=0.05, l2=l3=0.20m, `TrotController` hip 기준 y=±0.15m. | 실제 URDF/Xacro FK와 IK를 같은 기하·관절 영점/축으로 통일한다. |
| MEDIUM | 컨트롤러가 여러 개 존재하며 동시에 구동하면 명령 충돌 | `stand_up`, `single_leg_mover`, `trot_gait_preview`, `quadruped_controller`, `trot_controllerFSM`은 동일 관절 명령 토픽에 쓰기 가능. | 제어권 1개만 활성화하고 나머지는 종료한다. |
| MEDIUM | 패키지 의존성 선언 미비 | `package.xml`에는 노드에서 직접 import하는 rclpy, 메시지, ros_gz 관련 런타임 의존성 선언이 충분하지 않다. | rosdep/manifest 의존성 점검 후 환경별 빌드 검증. |

## 검토 절차와 검증 수준

1. 도서 원고의 10.1절 학습 목표와 실제 저장소의 파일명·API·메시지 계약을 대조했다.
2. Python 클래스 구현, 설정, 관련 테스트 스크립트의 호출 관계를 **소스 열람 기반**으로 점검했다.
3. 본 작업 환경에는 ROS 2 Jazzy/Gazebo Harmonic 구동 권한과 원격 사용자의 WSL2 실행 증거가 없어 **실제 colcon 빌드·ROS 토픽 송수신·Gazebo 물리 실행은 수행했다고 주장하지 않는다**.
4. 따라서 오류 수준은 코드만으로 확인되는 구조적 결함 또는 실행 시 검증해야 하는 위험을 구분한다. 위 검토는 실제 시뮬레이션에서 재현된 장애 기록이 아니다.

## 재현·회귀 검증 권장 명령

```bash
# 저장소 루트에서 작업 시작
source /opt/ros/jazzy/setup.bash
cd Ch10/ros2_ws
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot
colcon build --symlink-install
source install/setup.bash
# 절별 검증은 짝 문서 LAB_10_1_GUIDE_KO.md 참조
```

## 수락 조건과 보류 항목

1. [ ] 실제 실행 파일(`setup.py` console_scripts)과 원고 내 가상 이름의 차이를 식별한다.
2. [ ] 실제 브리지의 12개 Float64 명령 토픽을 확인한다.
3. [ ] URDF 치수·각도 영점이 코드와 다른 점을 표로 기록한다.
4. [ ] `ros2 pkg prefix my_quadruped_bot`가 현재 Ch10 workspace 설치 디렉터리를 가리키는지 확인
5. [ ] 필요한 경우 단위테스트/ros2 topic/시뮬레이터 로그와 결과 수치·실행 시간·Git SHA 보존

**결론:** 현행 소스를 변경하지 않았으며, 학습 실행의 성공을 입증하지 않았다. 근본 원인 해소 후 정적·단위·통합·Gazebo 검증을 거쳐 최종 승인해야 한다. 이 문서는 [실습 가이드](LAB_10_1_GUIDE_KO.md)와 한 쌍이다.
