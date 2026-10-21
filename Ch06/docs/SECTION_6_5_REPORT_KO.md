# 6.5절 코드 리뷰 — 데카르트 사각형 경로

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.5절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 대상
`Ch06/ros2_ws/src/my_robot_control/my_robot_control/cartesian_path.py` (기본 실행본). `.draft/.gem/.gpt`, `cartesian_path_rev.py`는 대안 파일로 실습 기준과 구별한다. 원고에는 `compute_cartesian_path(waypoints,eef_step,jump_threshold)` 예제가 있으나 실제 실행본은 **Pilz LIN planner를 반복 호출**한다.

## 핵심 결함
| ID | 수준 | 코드/원고 확인 | 수정·검증 방법 |
|---|---|---|---|
| IK65-01 | BLOCKER | `cartesian_path.py`는 `.robot_description(file_path="urdf/my_robot.urdf.xacro")`를 요구하지만 MoveIt config CMake install 대상에 `urdf/`가 없음. | 원본 모델 경로를 통일하고 빌드 후 설치본 파일 확인. |
| IK65-02 | HIGH | `planning_pipelines`에 Pilz 이름과 기본 파이프라인만 설정; 실제 Pilz plugin, cartesian limits 및 planning 설정이 일관되게 제공되는지 불명. | 로드된 pipeline 플러그인과 `LIN` planner_id를 로그로 확인. `pilz_cartesian_limits.yaml`의 로딩도 확인. |
| IK65-03 | HIGH | 코드는 `compute_cartesian_path`를 호출하지 않으며 4개 Pose를 4회 각각 `plan → execute`한다. 하나의 연속·완성된 사각형 궤적을 산출하거나 fraction을 검사하지 않음. | 하나의 직선 구간씩 성공률/시작상태·종료상태, 궤적 Cartesian 직선 오차 기록. 필요 시 별도 Cartesian service 구현. |
| IK65-04 | HIGH | 콘솔/주석은 '10cm', 'Y-Z plane', '0.5m'를 주장하지만 `square_moves`는 X-Z 평면의 0.4m×0.4m (40cm)이다. | 수치·평면을 40cm X-Z로 정정하거나 변위를 0.1m로 변경. |
| IK65-05 | HIGH | 원고의 `jump_threshold=0.0`이 '관절 점프 완전 금지'라는 설명은 반대: 일반 MoveIt Cartesian interpolation에서는 **0이 jump check 비활성화**다. | 위험한 안전 지침 삭제. joint-space jump 제한과 샘플링·충돌 검사를 별도로 활성화/검증. |
| IK65-06 | MEDIUM | 스크립트는 `setup.py`에 `cartesian_path` console entry point가 없고, 성공 시 `os._exit(0)`으로 종료. | `python3 -m my_robot_control.cartesian_path` 방식 또는 정식 entry point 등록; 결과/자원 정리 수행. |

## 검증 계약
- 목표 pose 4점 각각의 position/orientation, `LIN` 계획 성공, FK가 목표 위치로 움직이는지 확인.
- 매 구간 실행 성공 후 실제 현재 관절 상태에서 다음 구간 계획. 계산 fraction이 없으면 fraction이라고 부르지 않는다.
- 경로 모든 샘플에 대해 목표 직선에서 최대 수직거리(m), 관절 점프(rad), 충돌 여부, 속도/가속도 한계를 기록.

**판정: BLOCKED. 원고·코드가 서로 다른 API를 다루고 있고 모델 경로도 유효하지 않을 가능성이 높음. 실구동 미검증.**

권위 근거: [MoveIt 2 Pilz LIN](https://github.com/moveit/moveit2_tutorials/blob/main/doc/how_to_guides/pilz_industrial_motion_planner/pilz_industrial_motion_planner.rst), [MoveIt Cartesian tutorial](https://moveit.readthedocs.io/en/latest/doc/pr2_tutorials/planning/src/doc/move_group_interface_tutorial.html) (jump threshold 0 disables check).
