# LAB 3.2 — 2-DOF 로봇 팔을 RViz에서 움직이기

## 목표·관찰 계약
`base_link`(원기둥) → Z축 회전 `joint1` → 0.5m `link1` → Y축 회전 `joint2` → 0.5m `link2` → 고정 `end_effector_link`. 정적 URDF에 담긴 부모·자식 관계와 관절별 회전축을 시각적으로 확인한다.

## 1. 빌드
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
check_urdf src/my_robot_description/urdf/two_dof_arm.urdf
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 pkg prefix my_robot_description
```
같은 이름의 패키지를 다른 장에서 source하지 않는다. 패키지 prefix가 `Ch03/ros2_ws/install` 아래인지 확인한다.

## 2. 시각화
```bash
ros2 launch my_robot_description display.launch.py model:=two_dof_arm.urdf
```
- RViz에서 Fixed Frame `base_link` 확인, RobotModel 및 TF 표출
- `joint1`을 +1.0rad로 이동: 전체 위팔의 **Z축 선회**
- `joint2`를 +0.7rad로 이동: 아래팔의 **Y축 기울임**
- 두 조인트를 0으로 복구. `joint_ee`는 fixed라 슬라이더 없음
- `ros2 topic echo /joint_states --once`로 GUI의 가상 각도 확인

## 3. 관찰을 통한 추론
`link1` visual의 `rpy=0 0 0`과 collision의 좌표계를 비교한다. 회전 태그를 실수로 `0 1.5708 0`으로 바꾸면 겉보기 막대는 수평이지만 충돌 부피는 수직이다. **화면 정렬이 물리 검증의 충분조건이 아니다.**

## 4. 추가 과제
joint2의 `limit`을 좁힌 테스트 사본을 만들어 UI 범위가 변하는지 비교한다. 이후 반드시 `git diff` 확인 후 실습 전 모델로 원복한다.

## 5. 성공·실패 판정
- [ ] check_urdf exit 0
- [ ] colcon build exit 0
- [ ] joint_state_publisher_gui 및 rviz2 정상 시작
- [ ] 두 조인트에 서로 다른 회전축이 관찰됨
- [ ] TF/RViz 오류 로그와 화면 캡처를 보관

**실패 진단**: `xacro: No such file`일 때 `model` 경로 및 install tree 재빌드; 화면에 모형이 없다면 Fixed Frame·RobotModel·`robot_description` 확인; WSLg OpenGL 문제는 `rviz2` 단독 실행으로 분리. 관련 [리뷰 보고서](SECTION_3_2_REPORT_KO.md).
