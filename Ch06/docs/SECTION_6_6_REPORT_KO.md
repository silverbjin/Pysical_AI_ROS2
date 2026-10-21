# 6.6절 코드 리뷰 — Gazebo Harmonic × MoveIt2 × ros2_control

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.6절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 실제 구성
`Ch06/ros2_ws/src/my_robot_moveit_config/launch/Gazebo_moveit.launch.py`(정확한 대소문자), `my_robot_description/urdf/my_robot.ros2_control_gazebo.urdf.xacro`, `my_robot.ros2_control_gazebo.xacro`, `config/ros2_controllers.yaml`, `moveit_controllers.yaml`. 원고 명칭 `demo_gazebo.launch.py`는 현 저장소 tree에 없음.

## 결함 및 위험
| ID | 수준 | 정적 근거와 조치 |
|---|---|---|
| IK66-01 | BLOCKER | 원고 `ros2 launch my_robot_moveit_config demo_gazebo.launch.py`는 존재하지 않는 파일. 실제 런치는 `Gazebo_moveit.launch.py`. |
| IK66-02 | HIGH | Gazebo 시작·모델 스폰·spawner를 한 `LaunchDescription`에 병렬 등록하고 서비스 준비 이벤트 게이트가 없다. controller_manager가 뜨기 전 spawner 실패하는 race 위험. 이벤트/상태 기반 순서 제어와 timeout 재시도 필요. |
| IK66-03 | HIGH | Gazebo wrapper 모델과 RViz demo 모델·SRDF 및 5축 제어 계약의 일치 검증이 없다. 동일 `robot_description`을 소비해도 두 모델의 TF·조인트 이름·root를 비교해야 함. |
| IK66-04 | HIGH | `moveit_controllers.yaml`의 그리퍼는 2개 joint의 `GripperCommand`를 선언하지만 ros2_control의 gripper 액션은 단일 joint 값으로 설정. gazebo launch는 arm_controller와 joint_state_broadcaster만 spawn; gripper는 spawn하지 않음. |
| IK66-05 | HIGH | `hello_moveit.py`는 `use_sim_time`이 launch node에서 상속된다고 보장할 수 없는 독립 MoveItPy 프로세스. `/clock`, joint_states freshness, robot_state_publisher TF 시각 동기 확인 필요. |
| IK66-06 | MEDIUM | 스폰 위치/모델 고정 여부에 대한 확인 없이 '서 있다/물리 엔진이 살아 있다'라고 판단. Over/under-shoot 관찰만으로 제어 계약을 검증할 수 없음. |

## 검증 체크포인트(실행 미수행)
1. gz server의 실제 모델 `my_robot` 존재 및 gz_ros2_control plugin 로딩.
2. `/clock` 증가, `/joint_states` 갱신·타임스탬프, TF base→link_wrist 정상.
3. `ros2 control list_controllers`에서 broadcaster·arm active, `/arm_group_controller/follow_joint_trajectory` 액션 존재.
4. `ros2 action info`로 서버 확인, 궤적 송신·action 결과·최종 관절 오차 확인.
5. RViz/ Gazebo 두 화면 모델 자세 일치, 의도된 속도·관절 제한 및 접촉·중력 조건 확인.

**판정: 통합 런치 구조는 있으나 의존관계 게이트와 실행 검증 부재. BLOCKED / 실물·물리 연동 성공 미확인.**
