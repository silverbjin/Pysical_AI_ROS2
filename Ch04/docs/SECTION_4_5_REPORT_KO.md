# 4.5절 코드 리뷰: Robot State Publisher와 JointState

- 기준일/커밋: 2026-10-20 KST / `main@7b7c10f`
- 브랜치: `feat/ch04-section-4-5`
- 검토 범위: 4.5 원고 + `Ch04/ros2_ws/src/my_robot_tf` + **실제 구현 위치** `Ch03/ros2_ws/src/my_robot_description`
- 판정: **BLOCKED AS WRITTEN** — Ch04에는 RSP·JointState 예제가 없고, Ch03의 `display.launch.py`가 없는 xacro 파일을 참조한다.
- 검증 수준: GitHub 파일과 경로의 **정적 대조**. colcon/RViz/joint GUI 실기동 **NOT RUN**.

## 1. 확인한 파일

- Ch04에는 `my_robot_tf` 하나만 있고 `my_robot_description` 패키지는 없다.
- Ch03에는 `my_robot_description/launch/display.launch.py`, `urdf/two_dof_arm.urdf.xacro`, `urdf/two_dof_arm.urdf`, `setup.py`가 있다.
- `Ch03/.../launch/display.launch.py`는 `robot.urdf.xacro` 경로를 설정하지만, **실제 `urdf/` 목록에는 이 이름이 없다.**
- 해당 launch는 `robot_state_publisher`, `joint_state_publisher_gui`, RViz를 포함한다. `ParameterValue(Command(['xacro ',urdf_file]),value_type=str)`은 이미 적용되어 있다.
- 실제 xacro 모델은 `base_link→link1→link2` 두 개의 회전관절 `joint1`, `joint2`를 정의한다.

## 2. 결함·수정 제안

| ID | 심각도 | 원인 | 조치 |
|---|---|---|---|
| 4.5-R1 | **High** | launch가 없는 `urdf/robot.urdf.xacro`를 호출 | 기존 Ch03 display launch의 파일명을 `two_dof_arm.urdf.xacro`로 정합화 후 빌드. |
| 4.5-R2 | **High** | 원고는 Ch04 workspace에서 `my_robot_description`을 빌드하도록 안내하지만 패키지는 Ch03에 존재 | Ch03 경로에서 독립 빌드하고 정확한 `install/setup.bash` source. 또는 Ch04에 독립 패키지를 명시적으로 복사/구성해야 함. |
| 4.5-R3 | Medium | RSP가 `/joint_states`를 발행하는 것으로 오해할 수 있음 | `joint_state_publisher_gui → /joint_states → robot_state_publisher → /tf` 데이터 흐름 명시. |
| 4.5-R4 | Medium | Ch03의 `display.rviz` RobotModel Description Source=Topic, Durability Policy=Volatile | 로봇 설명을 RViz 시작 전에 한 번만 발행한다면 늦게 수신되지 않을 수 있다. 실제 `/robot_description` QoS 확인 후 RViz를 Transient Local로 맞추거나 적절한 Description Source 지정. |
| 4.5-R5 | Medium | 실제 관절 상태 소스가 없음에도 /joint_states 값이 나타나는 GUI 실습 | GUI는 **가상** 관절값이다. 실물 인코더 상태·Gazebo 물리 센서와 구분. |
| 4.5-R6 | Low | Ch03 `package.xml`에 `xacro`만 의존성 선언 | launch 실행 종속성(`robot_state_publisher`, `joint_state_publisher_gui`, `rviz2`, `launch_ros` 등)을 정비할 것. |

## 3. 합격 기준

1. `xacro`가 `two_dof_arm.urdf.xacro`를 정상 확장함.
2. `robot_state_publisher`와 GUI가 정상 실행, `/joint_states` 메시지의 `name[]`와 `position[]` 인덱스 일치.
3. GUI 슬라이더 변경에 따라 `base_link→link1`, `link1→link2` TF 갱신.
4. RViz RobotModel이 표시되며 `view_frames`에 일관된 단일 부모 트리.
5. 로봇 설명과 TF가 없을 때 어떤 노드/토픽을 조사할지 설명 가능.

## 4. 검증 현황

| 검사 | 현재 |
|---|---|
| 두 패키지 및 실제 파일 경로 대조 | **정적 확인** |
| Ch03 xacro 이름 불일치 | **결함 확인** |
| `ros2 launch` GUI·RSP 동작 | **NOT RUN** |
| 설치 의존성, ROS KDL 경고 점검 | **NOT RUN** |

본 변경은 **문서만 추가**한다. Ch03의 원본 소스를 수정하거나 Ch04로 복사하지 않았다. 별도의 코드 수정 PR이 필요하면 4.5-R1~R6에 근거해 진행한다.

참조: [Ch03 display.launch.py](https://github.com/silverbjin/Pysical_AI_ROS2/blob/main/Ch03/ros2_ws/src/my_robot_description/launch/display.launch.py) · [RSP 문서](https://github.com/ros/robot_state_publisher).
