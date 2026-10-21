# 4.5절 코드 수정·정적 테스트 보고서 (2026-10-21 KST)

- 브랜치: `feat/ch04-section-4-5`; 변경 SHA: `0c60ca1101b3707cb12cdfeef214c4223a0ab7a8`
- 기존 리뷰: [SECTION_4_5_REPORT_KO.md](SECTION_4_5_REPORT_KO.md)
- 판정: **STATIC_CONTRACT_PASS 7/7, ROS GUI/RSP NOT_RUN**

## 원인 및 수정

Ch03의 기존 `display.launch.py`는 실제 없는 `robot.urdf.xacro` 경로를 사용했으며, 원고의 Ch04 workspace에는 `my_robot_description` 패키지가 없었다. **Ch03 코드를 직접 훼손하지 않고** Ch04 `my_robot_tf/launch/display_ch04.launch.py`를 신설했다. 이 launch는 사전에 빌드/source된 Ch03 패키지의 실제 `two_dof_arm.urdf.xacro`를 찾아 Xacro를 문자열 `ParameterValue`로 RSP에 전달하고 GUI 관절 상태 발행자·RViz를 실행한다.

`rviz/display_ch04.rviz`는 Fixed Frame을 `base_link`로 하고 `/robot_description` Topic의 Transient Local durability를 사용한다. `test_section_4_5_display.py`에서 Xacro 경로·RSP/GUI 역할·RViz 설정을 정적으로 검사하도록 했다.

## 원격 코드 기반 정적 검사

| 항목 | 결과 |
|---|---|
| source xacro confirmed | PASS |
| exact filename | PASS |
| typed robot_description | PASS |
| RSP | PASS |
| GUI | PASS |
| RViz QoS | PASS |
| test cases | PASS |

이 검사 결과는 **GitHub 소스 텍스트와 참조 Xacro 내용의 계약 대조**다. Xacro 실제 변환, GUI 조작, RViz 성공을 의미하지 않는다.

## 로컬 재현 명령

```bash
source /opt/ros/jazzy/setup.bash
cd Ch03/ros2_ws
colcon build --packages-select my_robot_description --symlink-install
source install/setup.bash
cd ../../Ch04/ros2_ws
colcon build --packages-select my_robot_tf --symlink-install
source install/setup.bash
ros2 launch my_robot_tf display_ch04.launch.py
# 별도 터미널에서 동일 순서로 source:
ros2 topic echo --once /joint_states
ros2 run tf2_ros tf2_echo base_link link2
```

```bash
cd Ch04/ros2_ws/src/my_robot_tf
PYTHONPATH="$PWD" python3 -m unittest discover -s test -p 'test_section_4_5_display.py' -v
```

| 시험 | 상태 |
|---|---|
| 정적 계약 | **PASS 7/7** |
| `unittest`·`xacro` 실제 해석 | **NOT_RUN** |
| colcon / GUI 슬라이더 / RViz | **NOT_RUN** |

제약: Ch03 ROS 패키지를 먼저 설치하고 올바르게 source해야 한다. Ch03 이외 워크스페이스의 동명 `my_robot_description`이 overlay에서 우선될 위험이 있으며, `ros2 pkg prefix my_robot_description`로 실제 경로를 확인해야 한다. Gazebo와 GUI를 동시에 통해 `/joint_states`를 중복 발행하지 않는다.
