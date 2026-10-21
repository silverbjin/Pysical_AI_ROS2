> 2026-10-21 코드 수정 반영: Ch03의 `display.launch.py`를 수정하지 않아도 Ch04의 `display_ch04.launch.py`로 정상 파일명 `two_dof_arm.urdf.xacro`을 참조할 수 있다. 먼저 Ch03 워크스페이스를 빌드/source하고 이어 Ch04를 빌드/source한다. `ros2 launch my_robot_tf display_ch04.launch.py`가 권장 실행 경로다. 아래의 Ch03 원본 `sed` 수정법은 기존 코드 오류를 비교하기 위한 **대안**일 뿐 필수 단계가 아니다.

# 4.5절 실습 가이드: JointState → RSP → TF → RViz

**중요:** 현재 Ch04에는 `my_robot_description` 패키지가 **없다**. Ch03의 예제를 활용하며, Ch03 display launch의 잘못된 xacro 파일명을 수정하기 전에는 그대로 실행하는 명령이 성공한다고 보장할 수 없다.

## 1. 학습 목표·데이터 흐름

```text
two_dof_arm.urdf.xacro ──xacro──> robot_description ──┐
                                                    robot_state_publisher ──> /tf, /tf_static
joint_state_publisher_gui ──────────> /joint_states ───┘
                                                              └──> RViz TF·RobotModel
```

GUI는 실제 로봇 상태가 아닌 mock 입력이다. Gazebo와는 **동시에 같은 /joint_states를 발행하지 않는다.**

## 2. 파일/의존성 사전 검사

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2
ls Ch03/ros2_ws/src/my_robot_description/urdf
grep urdf_file Ch03/ros2_ws/src/my_robot_description/launch/display.launch.py
ros2 pkg prefix robot_state_publisher
ros2 pkg prefix joint_state_publisher_gui
ros2 pkg prefix xacro
```

원본은 `robot.urdf.xacro`를 요청하지만 실제 파일은 `two_dof_arm.urdf.xacro`다. 이 불일치를 해결해야 한다.

## 3. 최소 수정 후 실행(사용자 로컬 검증용)

**다음 수정은 Ch03 원고 코드에 영향을 주므로 로컬 diff 확인 후 별도 승인/커밋으로 관리한다.**

```bash
cd ~/Pysical_AI_ROS2
# 실제 경로가 맞는지 확인한 뒤 파일명 참조만 변경
sed -i "s/robot\.urdf\.xacro/two_dof_arm.urdf.xacro/" \
  Ch03/ros2_ws/src/my_robot_description/launch/display.launch.py
git diff -- Ch03/ros2_ws/src/my_robot_description/launch/display.launch.py
source /opt/ros/jazzy/setup.bash
cd Ch03/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select my_robot_description --symlink-install
source install/setup.bash
ros2 launch my_robot_description display.launch.py
```

여기서 명령은 **권장 재현 절차**이지 현재 원격 소스에 반영된 변경이 아니다. `sed` 대체 후, `xacro $(ros2 pkg prefix my_robot_description)/share/my_robot_description/urdf/two_dof_arm.urdf.xacro >/tmp/ch04_arm.urdf`로 URDF 확장을 별도 점검할 수 있다.

## 4. 검증 (새 터미널)

```bash
source /opt/ros/jazzy/setup.bash
source ~/Pysical_AI_ROS2/Ch03/ros2_ws/install/setup.bash
ros2 topic echo --once /joint_states
ros2 topic info /robot_description -v
ros2 run tf2_ros tf2_echo base_link link2
ros2 run tf2_tools view_frames
```

- GUI에서 `joint1`, `joint2` 슬라이더를 움직인다.
- `/joint_states`의 `name`·`position` 배열이 같은 순서인지 확인한다.
- RViz Fixed Frame은 `base_link`; RobotModel이 비어 있으면 `/robot_description` 수신 QoS를 점검한다.
- RViz에서 `Description Source: Topic` 사용 시 `Durability Policy: Transient Local` 필요 여부를 확인한다.
- `base_link→link1→link2` TF가 관절 입력에 따라 달라지는지 본다.

## 5. 고장 주입·원인 분석

| 고장 | 관측 예상 | 원인 |
|---|---|---|
| 원본 파일명 그대로 사용 | xacro 파일 없음·launch 실패 | 잘못된 URDF 경로 |
| GUI 노드 종료 | /joint_states 업데이트 중단 | 가상 관절 소스 부재 |
| Fixed Frame `world` 사용 | Fixed Frame 없음 가능 | URDF는 world→base_link 미생성 |
| RSP 중지 | /tf 갱신 중단 | 정운동학 노드 부재 |

## 6. 제출물

`xacro` 성공 로그, `git diff`(수정 필요 시), `/joint_states` 실제 출력, RViz 슬라이더 전후 캡처, `view_frames` 트리, 미해결 로그. 실습 검증이 끝난 로컬 Ch03 변경은 관련 Ch03 PR 또는 별도 변경 승인 없이 다른 장 브랜치로 섞어 Push하지 않는다.

[리뷰 보고서](SECTION_4_5_REPORT_KO.md)
