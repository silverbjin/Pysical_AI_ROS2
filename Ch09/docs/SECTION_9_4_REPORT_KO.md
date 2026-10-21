# 9.4절 코드 리뷰 — Gazebo Harmonic 플러그인과 ROS–Gz 브리지

검토일: 2026-10-21 (KST) · 기준 main: `bab76f6ca7df` · 원고: 「9.4 Gazebo Harmonic 환경 설정 및 플러그인 연동」

**결론: 소스 정적 리뷰 완료 / ROS 2·Gazebo 실제 실행 NOT_RUN / 전체 실습 성공 미인증.**
이번 PR은 요청에 따라 Markdown 보고서와 따라하기 가이드만 추가하며 소스 코드는 변경하지 않는다.

## 리뷰 대상

- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/common/gazebo_control.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`
- `Ch09/ros2_ws/src/my_quadruped_bot/worlds/empty_world.sdf`
- `Ch09/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`

## 발견 사항 및 개선 제안

| No. | 우선순위 | 근거: 원본 소스 상태 | 개선 및 확인 지점 |
|---|---|---|---|
| 1 | 확인 | gazebo_control.xacro에 gz::sim::systems::JointStatePublisher, leg 매크로에 다리별 3개 JointPositionController | 전개 시 12개 관절 위치 플러그인 구성이 기대됨 |
| 2 | 확인 | ros_gz_bridge.yaml에는 /clock, /joint_states + 실제 활성화된 12개 ROS_TO_GZ cmd_pos 항목 | 명령 ROS 토픽은 '/0/' 없음, Gz 토픽은 '/0/' 포함. 원고 9.4 예제와 구분 |
| 3 | 주의 | leg.xacro의 foot gazebo 블록은 <mu1 value='1.0'/> 같은 속성 기반 형태 | Harmonic 변환 후 SDF surface friction 반영을 gz sdf -p로 반드시 확인. 미적용이면 자식 텍스트 형태로 정정 |
| 4 | 높음 | simulation.launch.py는 /clock 브리지를 시작하지만 robot_state_publisher에 use_sim_time을 명시하지 않음 | ROS 시간·TF와 시뮬레이션 시간을 통일하는 조치 권고 |
| 5 | 주의 | 관절 위치 컨트롤러의 i_gain=0.1; 제어기는 순수 PD가 아니라 PID | 9.6 원고의 PD 설명과 실제 설정을 구분 |

## 검증과 한계

- **실시:** GitHub main의 실제 파일을 읽어 Xacro 구성, launch·Python 연계 및 첨부 원고의 9.4절 설명을 정적으로 대조했다. 사용한 분석 대상이 코드 수정 PR의 상태가 아니라 **위 main 기준 SHA**임을 유의한다.
- **미실시(NOT_RUN):** `xacro` CLI 전개, `check_urdf`, `rosdep`, `colcon build/test`, Gazebo Harmonic 물리 계산과 WSLg/RViz 실행, 실제 ROS 토픽 검증. 네이티브 ROS/Gazebo 실행 환경이 이 세션에 없으므로 PASS를 주장하지 않는다.
- **확정 실패(FAIL)와 구별:** 정적으로 확인된 논리 문제는 표에 기록했다. 아직 실행하지 않은 항목을 실패 또는 성공으로 꾸미지 않는다.

## 재현 및 수용 기준

1. ROS joint cmd_pos 12개와 gz cmd_pos 12개를 실제로 관찰했는가?
2. /joint_states와 /clock의 메시지 타입 및 방향은?
3. SDF 변환 결과의 발 마찰 계수가 실효 있게 들어갔는가?
4. robot_state_publisher의 use_sim_time 상태는?

**판정:** 실제 메시지 수신·매핑·SDF 변환이 확인되어야 한다. GUI 실행, 마찰·접촉 안정성은 이 문서 작성 환경에서 NOT_RUN이다.

## 원고 정합성·후속 조치

원고의 `/model/.../0/cmd_pos`는 Gazebo 토픽이다. 현재 ROS 발행 경로는 `/0/`이 없는 경로이므로 명령 예제에서 혼동하지 않는다.

각 항목 수정이 필요한 경우 별도 코드 수정 브랜치에서 RED→GREEN 회귀 검증, 실행 로그 및 소스 차이를 남길 것을 권장한다. [9.4 실습 가이드](LAB_9_4_GUIDE_KO.md), [대상 코드](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch09).
