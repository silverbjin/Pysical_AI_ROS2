# 6.4절 실습 가이드 — MoveItPy로 Named State → IK 목표 제어

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.4절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 목표
코드로 `arm_group`의 named `ready`와 포즈 목표를 계획하고, **계획 성공 / 액션 실행 성공 / 실제 도달 오차**를 각각 확인한다.

## 선행 게이트(필수)
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-up-to my_robot_control
source install/setup.bash
ros2 pkg executables my_robot_control
P=$(ros2 pkg prefix my_robot_moveit_config)
find "$P/share/my_robot_moveit_config" -maxdepth 3 -type f | sort
```
현 코드의 `hello_moveit.py`가 요청하는 `urdf/my_robot.urdf`가 MoveIt config 설치 폴더에 없다. **이 BLOCKER를 고치기 전에는 정상 실행을 기대하지 말 것.** 권장 변경은 `MoveItConfigsBuilder.robot_description`에 실제 존재하는 Xacro/URDF 경로를 전달하고 SRDF와 root 충돌을 검사하는 것.

## 실습 순서(수정 및 readiness 검증 후)
터미널 A:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws && source install/setup.bash
ros2 launch my_robot_moveit_config Rviz_Demo.launch.py
```
터미널 B:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws && source install/setup.bash
ros2 control list_controllers
ros2 action list -t
ros2 topic echo /joint_states --once
ros2 run my_robot_control hello_node
```
위 `Rviz_Demo.launch.py`는 mock hardware 환경이다. GUI 실행 자체는 재검증되지 않았고 controller/TF 이슈가 남아 있을 수 있다. 저장소에 `ros2 run my_robot_control hello_moveit` 명령은 등록되어 있지 않다.

## 코드 읽기 · 수정할 목표
1. `build_moveit_config()`: 실제 설치 경로, `robot_description`, `ompl`, planning scene monitor 설정을 확인한다.
2. `arm.set_goal_state(configuration_name="ready")`: SRDF의 `joint3=1.5708`rad를 기준으로 관절 목표를 검사한다.
3. Pose 목표: 현재 파일의 (0,0,2.1)은 실습 성과를 보장하지 않는다. 먼저 RViz에서 충돌 없는 도달 가능한 위치를 선정하고 각 목표의 orientation을 명시한다. **5축으로 6D 목표의 해가 없을 수 있다**.
4. `plan_result`가 유효해도 별도로 `execute` 반환 상태와 joint_state/FK 도달 오차를 기록한다.
5. `os._exit(0)` 제거 후 `try/finally`, 실패 시 비영(非0) 종료 코드 등 정상적인 자원 정리로 수정한다.

## 제출할 evidence
패키지 경로 출력, controller state, planning/execution 로그, 기준 목표/최종 FK 오차, 성공·실패 각각의 종료 코드. 실패 원인(URDF 없음, IK 해 없음, 충돌, 액션 미기동)을 구분해야 한다.

**주의:** 이 절은 리뷰 기반 실습 가이드이며 수정 코드를 이미 적용/검증했다는 문서가 아니다. [보고서](SECTION_6_4_REPORT_KO.md).
