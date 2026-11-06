# v36 실제 실패 분석과 v37 최소 보완 명세

2026-11-06 KST. 단일 작업자. 원본 v36 source/FAIL/archive를 보존하고 새 구현 전에 명세를 작성했다.

## 실제 결과와 원인 분리

L3 d0611273-5f74-47a8-b108-12d189dbd523는 survey/최종 접근/find 뒤 pre-grasp 계획 실행까지 진행했으나 link3:world:PRE_GRASP 금지 접촉으로 engine ERROR다. trial 94.424sim/234.580wall초, child11개 정상 회수/잔여0이다. L2 40299e00-3e7a-4d6c-9311-a0f2b03de912는 survey deadline FAIL, 58.380sim/124.803wall초, engine/child12개 정상 회수/잔여0이다. 새 10회 기능 gate는 미통과다.

L3 마지막 저장 표본의 MuJoCo link3↔식탁 상판 거리는 실제 팔 1.001mm, 명령 팔 11.106mm였다. 계획 시작 몸체로 바꾼 대조는 각각 .720mm/10.796mm다. 이 표본에서는 몸체 변위보다 팔 추종 차이가 약10mm 여유를 소진했다. 표본은 실제 금지 접촉 직전이며 정확한 접촉 프레임 자체라고 확대하지 않는다. MoveIt의 기본 충돌 판정은 네 표본을 모두 valid로 보았으므로 표본 시점의 양 모델이 모순됐다고 말하지 않는다.

공식 MoveIt 2.12.4 PlanningScene diff의 link_padding과 moveit_msgs2.6.0 LinkPadding을 조사했다. 실제 모델의 이름 reuse/link3에 30mm 여유를 적용한 대조에서 위험한 실제/명령 중간 표본은 모두 invalid, 원래 계획 끝 자세와 시작 자세는 valid였다. 같은 시작→원래 끝 joint goal 경로도 기존2초 계획 budget에서 성공했다(계획 .278초, raw107.862sim초). 실제 추종 성공이나 정규화 후 실행 시간 PASS는 아직 아니다. 최초 link3라는 잘못된 이름은 모델이 거절했고 tool 실패로 보존했다. GetPositionIK의 exact-pose 시도는 -31이었으며, 원래 계획 끝 joint state의 유효성과 구분한다.

L2 survey 목표 최근접은19.134mm로 제어기의15mm 진입 조건을 충족하지 못했다. 이는 최종 귀환/물체 위치 점수와 별개인 관측용 중간 waypoint다. 3cm 최종 평가 목표나 native zero-base/수명/물리 안전 조건을 늘리지 않고 중간 관측용 goal checker를 분리한다.

## A. L3 링크의 계획 여유

- 기존 worker/Planner.call을 사용해 L3에서만 reuse/link3 padding .03m를 ApplyPlanningScene diff로 적용하고 실제 readback을 확인한다. 모르는 링크/실패/불일치는 계획 전에 거부한다.
- world/ACM/attach 외에 nondefault link padding/scale도 scene_hash에 포함한다. 기본 padding0/scale1에서는 기존 hash를 보존한다. 새 계획 revision과 증거에 적용 값을 기록한다.
- 기존 run_pick에서 world objects 적용 후, pose 계획 이전에 작은 opt-in hook으로 연결한다. 물리 모델·native PD·effort·속도/수명/action deadline·실제 접촉 판정을 변경하지 않는다. 다른 Level/기존13.6 실행에는 적용하지 않는다.
- RED→최소 구현→GREEN 및 실제 설치 readback/저장 상태 재판정, 필요한 전체 회귀·새 동결 후 실제 확인한다. margin 때문에 계획이 거부되면 실패로 기록하며 줄여 통과시키지 않는다.

## B. 관측 waypoint의 독립 goal checker

- L2/L3에만 survey_checker(SimpleGoalChecker, XY .06m/yaw .06rad/stateful true)를 추가한다. 기존 최종 goal_checker XY .015m/yaw .06rad와 3cm/120초/높이20mm 점수는 유지한다.
- 기존 navigate_no_recovery.xml을 재사용한 별도 survey XML에서 FollowPath.goal_checker_id를 survey_checker로 명시한다. 기본 XML의 goal_checker ID는 그대로다.
- survey의 NavigateToPose.Goal.behavior_tree에 설치된 survey XML을 지정한다. 같은 ROS owner·소유 goal·cancel/drain·실제 정착·이후 새 원본 RGB-D 관측/IK 권한은 그대로다. survey SUCCESS를 최종 3cm 도달로 표현하지 않는다.
- 실제 ROS parser에서 두 checker와 기존 최종 허용 오차가 함께 보존되는지 RED/GREEN으로 검증한다. XML goal checker ID와 실제 Action 메시지 경로를 확인한다. callback에서 sleep/nested spin을 추가하지 않는다.

## 근거와 실행 순서

- [MoveIt PlanningScene 2.12.4](https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/planning_scene/src/planning_scene.cpp), [LinkPadding2.6.0](https://github.com/moveit/moveit_msgs/blob/2.6.0/msg/LinkPadding.msg).
- [공식 FollowPath BT 1.3.13](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_behavior_tree/plugins/action/follow_path_action.cpp)의 goal_checker_id 입력과 기존 명시적 ID 선택 패턴을 사용한다. 새 action 종류/토픽 소유권을 만들지 않는다.

두 보완을 각각 부품 검증·보고/커밋한 뒤 분리 build/전체 회귀/실제 venv child/asset94·tested/runtime 전수 hash·새 freeze/사전 UUID를 확인한다. 실제 engine은 한 번에 하나씩 필요한 사례만 실행한다. 연속 기능 gate 뒤에만 새 고정10회를 수행하며 이전 실패와 수치 목표 미달은 그대로 보존한다. engine 중 build/pytest/대용량 분석을 병행하지 않는다.
