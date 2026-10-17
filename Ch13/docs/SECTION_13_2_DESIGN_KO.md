# 13.2 통합 로봇 모델링 설계

기준 커밋: `1451f54a64374f2ff150a39429cc89e9e3b07696`  
대상: ROS 2 Jazzy, Gazebo Harmonic, MuJoCo 3.x

## 완료 기준

- `Ch13/ros2_ws`만으로 `integrated_robot_description`을 빌드하고 설치한다.
- 4족 12축, 팔 6축, 평행 그리퍼 2축을 포함한 단일 Xacro/TF 트리를 만든다.
- 팔의 모든 링크와 관절에 `arm_`, 그리퍼에 `gripper_` 접두어를 적용한다.
- `base_footprint -> base_link -> arm_mount -> arm_base_link -> ... -> arm_tool0`가 끊기지 않는다.
- 모든 동적 링크에 형상과 일치하는 양의 질량·관성을 둔다.
- 단일 `ros2_control` 블록이 20개 가동 관절을 이름으로 선언한다.
- Gazebo와 MuJoCo용 하드웨어 플러그인을 Xacro 인자로 선택하며 동시에 활성화하지 않는다.
- Xacro 전개, URDF 구조, 관절 축·한계, TF, 명령 인터페이스와 실제 엔진 로드를 검증한다.
- Ch05~Ch12는 변경하지 않고 재사용 출처와 기준 커밋을 문서화한다.

## 원고 교정

1. `trunk`는 현재 Ch11 모델에 없는 이름이다. 실제 결합 부모는 `base_link`이며, 별도 `arm_mount` 링크를 둔다.
2. 다리 12축과 팔 6축만 세면 18축이지만, 물리 그리퍼 2축까지 포함한 가동 관절은 20개다.
3. 현재 Ch12.8 정책은 effort가 아니라 위치 잔차를 절대 위치 목표로 변환한다. 따라서 검증 기준 구성은 20개 모두 position 명령으로 통일한다. effort 정책은 구현·학습·안전 검증 전까지 제안으로 남긴다.
4. MuJoCo 공식 플러그인 클래스명은 `mujoco_ros2_control/MujocoSystemInterface`이다. 원고의 `mujoco_ros2_control/MujocoSystem`은 사용하지 않는다.
5. SRDF의 collision disable은 MoveIt planning collision용이며 물리 엔진 충돌을 끄지 않는다. URDF에는 단순 충돌 형상과 간섭 없는 home pose를 두고, 엔진별 접촉 설정은 별도로 검증한다.
6. 임의 관성값 `0.001`을 반복하지 않고 상자·원기둥 근사식으로 계산한다. 장착 위치는 “최적”이라고 단정하지 않고 검증한 기본값으로 표현한다.

## 패키지 구조

```text
Ch13/
  ros2_ws/src/integrated_robot_description/
    CMakeLists.txt
    package.xml
    urdf/
      materials.xacro
      inertial_macros.xacro
      quadruped_base.xacro
      manipulator.xacro
      system.ros2_control.xacro
      robot_system.urdf.xacro
    config/controllers.yaml
    launch/
      view_robot.launch.py
      gazebo.launch.py
      mujoco.launch.py
    mujoco/robot_system.xml
    rviz/robot_system.rviz
  tests/
  scripts/
  docs/
  evidence/section_13_2/
```

## 모델과 제어권

- 좌표계는 REP-103(+X 전방, +Y 좌측, +Z 상방)를 따른다.
- Ch11의 4족 치수·관절 순서·축·한계를 필요한 범위만 복사한다.
- Ch08의 Z-Y-Y-X-Y-Z 6축 개념을 축소·경량화해 사용한다. 원본 0.5 m × 4 링크와 10 kg 베이스는 결합 모델에 그대로 사용하지 않는다.
- 장착점 기본값은 `base_link` 상면 중앙의 `0 0 0.095 m`이다. LiDAR는 뒤쪽으로 이동해 장착판과 겹치지 않게 한다.
- `joint_state_broadcaster`, 다리 `forward_command_controller`, 팔 `joint_trajectory_controller`, 그리퍼 `forward_command_controller`가 서로 겹치지 않는 command interface를 claim한다.
- 같은 관절에 대해 Gazebo 개별 JointPositionController와 `gz_ros2_control`을 함께 넣지 않는다.
- Gazebo backend는 `gz_ros2_control/GazeboSimSystem`, MuJoCo backend는 `mujoco_ros2_control/MujocoSystemInterface`, RViz backend는 `mock_components/GenericSystem`을 사용한다.

## 검증과 주장 경계

- 정적 테스트: Xacro 구조, 20관절 유일성, 단일 루트, 축·한계, 양의 관성, 단일 `ros2_control`, backend별 플러그인, controller 관절 집합의 정확한 분할.
- RViz: `robot_state_publisher`와 GUI joint-state publisher 실행 가능 여부. GUI를 실제 화면으로 확인하지 못하면 미검증으로 기록한다.
- Gazebo: 실제 서버에서 spawn, controller 활성화, 20개 joint state와 작은 팔 명령 반영, 정지 상태 유한성, 정상 종료를 확인한다.
- MuJoCo: 공식 plugin을 소스 빌드해 실행을 시도한다. 의존성/호환성 때문에 실패하면 native MuJoCo 모델 로드·step 결과와 ros2_control 미검증을 서로 대체하지 않고 나눠 기록한다.
- MoveIt 2, collision-aware planning, 안정 PPO 보행, whole-body control, 물리 파지 성공은 13.2 완료 주장에 포함하지 않는다.

