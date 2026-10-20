# SECTION 3.2 — 2축 매니퓰레이터 모델·RViz 실행 코드 리뷰

- 원고: 3.2.1~3.2.5 (원고 본문에서 3.2 상위 제목 누락, 3.2.1부터 시작)
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20 KST
- 상태: **정적 수정 완료 / ROS 2·RViz 통합 실행 미검증**

## 발견 사항
| ID | 수준 | 실제 소스 근거 | 조치 |
|---|---|---|---|
| 3.2-01 | High | `two_dof_arm.urdf`의 `link1` visual에만 Y축 1.5708rad 회전, collision은 Z방향 직립 | visual rpy를 0 0 0으로 교정하여 길이 0.5m 링크가 수직 정렬 |
| 3.2-02 | High | `display.launch.py`에서 존재하지 않는 `urdf/robot.urdf.xacro` 하드코딩 | 기본 `two_dof_arm.urdf`, `model` 런치 인자로 선택 가능 |
| 3.2-03 | Medium | `package.xml`은 `xacro`만 의존하고 GUI/RSP/ros_gz 및 제어 노드의 실행 의존성이 미선언 | 장 전체 사용 런타임 의존성 명시. ROS Jazzy에서 `rosdep` 사용 가능 |
| 3.2-04 | Info | 원고는 base를 '바닥에 고정'이라고 설명하나 URDF 자체는 고정을 보장하지 않음 | RViz의 가상 고정 좌표와 Gazebo 중력 하 자유 베이스를 구분 |

## 검증 기준
- **PASS (소스 정적)**: `base_link -> joint1 -> link1 -> joint2 -> link2 -> joint_ee -> end_effector_link`의 4링크/3조인트 체인 확인. joint1 Z, joint2 Y, joint_ee fixed.
- **PASS (수정 가드)**: 잘못된 파일명·link1 visual 회전값 교체, 런치 인자 정의 및 의존성 선언 포함 확인.
- **NOT RUN**: `python3 -m compileall`, `check_urdf`, `colcon build`, `ros2 launch`, RViz GUI. 이 세션에는 ROS 2 실행기 없음.

## 재현 명령
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
python3 -m compileall -q src/my_robot_description/launch
check_urdf src/my_robot_description/urdf/two_dof_arm.urdf
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description display.launch.py model:=two_dof_arm.urdf
```

**예상**: Joint State Publisher GUI 슬라이더 2개, RViz RobotModel 2개 가동축; `joint1` 회전 시 link1이 베이스 Z축 주위 선회, `joint2` 변경 시 link2만 Y축 굽힘. TF는 GUI의 가상 관절각에서 계산되며 Gazebo 센서로 검증한 결과가 아니다.

## 통합·PR 주의
3.1 브랜치의 관성 수정은 독립 파일이므로 선택적으로 병합 가능. 3.3 Xacro로 진행하면 `two_dof_arm.urdf` 정적 모델과 Xacro 모델의 차이를 명시하라. `package.xml` 의존성을 이 브랜치에서 일괄 정리하므로 **3.2 병합 후 다른 절의 런타임 검증**을 권장한다. Acceptance: `PENDING_RUNTIME_VERIFICATION`.
