# 6.2절 코드 리뷰 — MoveIt 2 솔버·플래너

> 기준: 2026-10-20 KST · GitHub main 1b9e8215e213 · 원고 6.2절 · ROS 2 Jazzy / Ubuntu 24.04 기준
> 범위: 저장소 소스 및 원고 정적 검토. 현재 세션에 ROS 2/Gazebo 실행 환경이 없으므로 실제 빌드·GUI·물리 시뮬레이션 결과는 **미검증**이다. 성공·PASS를 추정하지 않는다.
> 검토 대상: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 연결되는 실제 파일
- `Ch06/ros2_ws/src/my_robot_moveit_config/config/kinematics.yaml`: **KDL 활성화**, `arm_group`, 해상도 0.005, timeout 0.005s.
- `config/ompl_planning.yaml`, `config/my_robot.srdf`, `my_robot_control/hello_moveit.py`: 그룹·기획·실행 경로에 관련.

## 발견 사항
| ID | 수준 | 실제 근거 / 수정 방향 |
|---|---|---|
| IK62-01 | HIGH | 원고는 Trac-IK 설치·교체만으로 성공률 향상을 확정하지만 저장소는 KDL이다. 성능은 같은 로봇·seed·목표·timeout 조건에서 벤치마크 전까지 알 수 없다. |
| IK62-02 | HIGH | `arm_group`는 `joint1, joint2, joint3, joint4, joint_wrist`의 5개 구동 관절이다. 6D 위치+자세 목표를 임의로 만족시킬 수 있다고 가르치면 안 된다. 접근 가능 포즈/position-only IK를 별도 검토한다. |
| IK62-03 | MEDIUM | `kinematics_solver_timeout: 0.005`는 매우 짧을 수 있다. 실패/속도/해 오차를 계측해 조정한다. 원고의 70% 대 99.9% 비교 수치는 해당 로봇 측정 근거 없음. |
| IK62-04 | MEDIUM | RRTConnect는 관절공간 경로를 계획한다. IK 솔버 단독으로 충돌 없는 완성 궤적·최적 에너지를 보장하지 않는다. `planning_pipeline`과 `planner_id`가 실제 로딩되는지 확인한다. |
| IK62-05 | MEDIUM | 원고 6.7의 Trac-IK가 곧 DLS라는 설명 및 '무조건 교체' 처방은 구현과 결과를 동일시한다. 알고리즘·패키지 버전 문서와 실측값을 구별한다. |

## 검증 설계(실행 미수행)
1. `ros2 pkg prefix moveit_kinematics` 및 `ros2 pkg prefix trac_ik_kinematics_plugin`으로 설치 상태 확인.
2. `kinematics.yaml`의 solver, timeout을 변수로 하여 동일 seed의 목표 포즈 20개 이상에 대해 성공률, P50/P95 시간, FK 오차, 관절 한계 위반을 기록.
3. `arm_group`의 실제 액티브 조인트 수 및 SRDF 체인 루트를 확인하고 위치 전용 IK 설정은 별도 실험한다.
4. OMPL 계획은 동일 장면에서 무충돌·joint limits·time parameterization을 별도로 검증한다.

**판정: KDL 기본 구성 확인. 다른 솔버의 우위 및 실 구동은 미검증; 성능 주장 교정 필요.**

근거 문서: [MoveIt kinematics 설정](https://moveit.picknik.ai/main/doc/examples/kinematics_configuration/kinematics_configuration_tutorial.html), [MoveItPy 튜토리얼](https://github.com/moveit/moveit2_tutorials/blob/main/doc/examples/motion_planning_python_api/motion_planning_python_api_tutorial.rst).
