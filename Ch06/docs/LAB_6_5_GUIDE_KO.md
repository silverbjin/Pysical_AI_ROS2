# 6.5절 실습 가이드 — Pilz LIN으로 사각형 경로 검증

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.5절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 배울 것
PTP와 Cartesian LIN의 차이를 **목표만 도달하는가**가 아니라 **말단의 중간 궤적이 직선인가**로 설명한다. 원고의 `compute_cartesian_path` 예제와 저장소 실제 `Pilz LIN` 구현은 구분한다.

## 시작 전 수정·확인 항목
`cartesian_path.py`의 로봇 URDF 경로는 설치본에 없어 오류 가능성이 있다. 또한 현재 코드는 40cm X-Z 사각형을 실행한다. 10cm Y-Z 사각형으로 설명하면 안 된다. `LIN` 플래너가 로드되고 안전 조건이 충족되기 전에는 **실제 하드웨어 실행 금지**.

## 사전 실행(ROS 터미널)
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws
colcon build --symlink-install --packages-up-to my_robot_control
source install/setup.bash
ros2 pkg executables my_robot_control
ros2 launch my_robot_moveit_config Rviz_Demo.launch.py
```
별도 터미널에서 준비가 확인된 후:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch06/ros2_ws && source install/setup.bash
python3 -m my_robot_control.cartesian_path
```
스크립트는 `setup.py`에 CLI가 등록되어 있지 않다. `ros2 run my_robot_control cartesian_path`는 현행 그대로는 사용할 수 없다.

## 단계별 실험
1. 현재 파일의 `target_pose=(1,0,1.1)`, quaternion 및 `link_wrist`가 실제 작업공간/충돌 제한에서 유효한지 GUI로 확인한다. 유효하지 않으면 실행보다 목표 재설계부터 수행.
2. `square_moves`의 네 이동을 표로 옮긴다: Z −0.4, X +0.4, Z +0.4, X −0.4 (m). 사각형 평면 X-Z, 변 0.4m.
3. 각 `arm.plan()`에서 `planner_id=LIN`과 Pilz plugin 로딩 여부 및 return state를 출력한다. 출발/끝 pose를 측정한다.
4. 성공 시 TF/FK를 시간별로 샘플링해 **각 선분과의 최대 수직거리**를 계산한다. OMPL PTP 경로와 비교한다.
5. 각 선분의 실행 완료를 확인하기 전에는 다음 선분으로 넘어가지 않는다. 경로의 joint velocity/acceleration 및 충돌 검사 결과를 첨부한다.

## 실패 재현/해결
- `urdf not found` → 6.3·6.4의 설치 경로 문제.
- `Planner config LIN not found` → Pilz pipeline/plugin/limits 설정 확인.
- `No IK solution` → 5축 로봇의 full pose 제한, reachable target·orientation 확인.
- `No controller` / 움직이지 않음 → action과 `ros2 control list_controllers` 확인.

## 중요한 교정
`jump_threshold=0`은 **점프 방지 OFF**를 의미하며 절대 '가장 안전한 설정'이 아니다. 연속 경로의 갑작스러운 joint 변화는 따로 감시한다. 원고 API 예제 `compute_cartesian_path()`는 현행 기본 Python 스크립트의 호출이 아니다.

증거: waypoint 표, 경로 최대 직선 편차, planning/execution 결과, 컨트롤러 액션 상태, RViz 스냅샷. [리뷰](SECTION_6_5_REPORT_KO.md).
