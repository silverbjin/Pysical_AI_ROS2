# 13.8 접근·탈출 후진 경로 및 목표 회전 구현 계획

> 단일 작업자로 superpowers:writing-plans / executing-plans를 적용한다. 질문 없이 연속 실행한다.

**Goal:** 같은 NavigateToPose 소유권 안에서 검증된 서쪽 접근과 파지 후 탈출 경로를 만들고 실제로 판정한다.

**Architecture:** 기존 Smac Hybrid를 REEDS_SHEPP로 선택하고 기존 RPP의 후진 추종을 사용한다. 마지막 방향 정렬은 설치된 공식 RotationShimController가 담당한다. 모델·정책·native 운반 lease·원본 관측 수명은 재사용한다.

**Tech Stack:** ROS2 Jazzy, Nav2 1.3.13, 기존 ch13_navigation_reuse/ch13_system_validation. 새 시스템 설치나 새 ROS 패키지는 없다.

**Spec:** SECTION_13_8_REPAIR_SEQUENCE_PLAN_KO.md, REPAIR_NAVIGATION_STRUCTURE 및 STEP4_VALIDATION 보고서의 실제 실패/정적 비교.

## 근거와 범위

v34 L3는 survey 실제 도달·정착 후 북쪽 접근을 계획하지 못했다. 5cm 지도에서 실제/이상 시작·목표 네 조합은 결과가 달랐다. 보간·padding·해상도 변경도 모든 조합의 filled-footprint 검사를 통과하지 못해 운영 설정에 채택하지 않았다.

반면 설치된 REEDS_SHEPP의 서쪽 L3 접근 네 조합과 대상 자리 제거 후 서쪽 귀환은 모두 경로 반환 및 filled-footprint 충돌 0이었다. L2 서쪽 귀환도 충돌 0으로 반환됐다. 이는 계획 부품의 증거이며 적재 후진의 물리 성공이 아니다.

[공식 Smac 1.3.13](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/src/smac_planner_hybrid.cpp)의 지원 모델, [RPP 구현](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/regulated_pure_pursuit_controller.cpp) 및 [parameter_handler](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/parameter_handler.cpp)를 확인했다. RPP의 allow_reversing와 use_rotate_to_heading를 동시에 true로 두지 않는다. 후진 추종의 목표 방향 정렬은 [공식 RotationShimController 1.3.13](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_rotation_shim_controller/src/nav2_rotation_shim_controller.cpp)을 조합한다. 해당 패키지 1.3.13-1noble.20260921.032338은 이미 설치돼 있다.

설치 ref의 shim은 plugin_name_를 name으로 대입하기 전에 PositionGoalChecker를 초기화한다. 따라서 실제 내부 checker의 매개변수 prefix가 `.position_checker`다. [PositionGoalChecker](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_controller/plugins/position_goal_checker.cpp)는 기본 stateful=true이므로 그대로 쓰면 최초 XY 통과 후 회전 latch 문제가 재발한다. 외부 소스를 수정하지 않고 버전 전용 YAML의 `.position_checker.stateful=false`를 실제 configure/동작 부품에서 확인한다. 정상 prefix `FollowPath.position_checker.stateful=false`도 명시하되 해당 설치에서 소비되지 않는 키를 소비됐다고 주장하지 않는다.

Upstream pinned deploy/console.py의 vx 감소 및 deploy/joystick.py의 signed 입력과 기존 safety.py의 ±0.2 명령 범위를 확인했다. 새 smoother의 후진 하한은 -0.10m/s로 제한한다. 후진 물리 안정성은 새 실제 사례가 필요하다. 기존 실제 vxy/wz/tilt guard와 모든 effort/수명/높이 판정은 유지한다.

## 구현과 검증 순서

- [ ] 실제 설치 controller_server를 엔진 없이 configure하는 부품 도구를 작성한다. shim/RPP 로드, 원래 회전 속도 .15·가속 .5, 실제 내부 stateful=false를 조회한다. 잘못된 prefix/누락 설정을 먼저 실패로 확인한다.
- [ ] 실제 PositionGoalChecker의 12mm 도달→20mm 이탈 재검사로 latch가 해제되는지 확인한다. 모의 객체로 대체하지 않는다.
- [ ] 실제 ROS parser 회귀를 먼저 RED로 확인한다. 새 L2/L3만 Smac REEDS_SHEPP, shim primary RPP, allow_reversing=true/use_rotate_to_heading=false, rotate_to_goal_heading=true, use_path_orientations=true, rotate_to_heading_once=true, 두 position_checker stateful=false를 선택한다. legacy/L1은 유지한다.
- [ ] 새 L2/L3의 smoother min vx=-.10을 적용한다. 기존 yaw cap(.10/.20), max vx .20, 가속도, 원래 footprint+1cm padding, 지도 5cm와 native guard는 유지한다. 시나리오 접근 방향은 검증한 서쪽 (bearing 0) 하나로 제한하고 비용을 기록한다.
- [ ] 관련 부품 → 분리 build/실제 venv child 설치·전체 회귀 → 새로운 v35 이상 동결 및 tested/runtime 전체 hash 대조 → source/case UUID를 실행 전에 고정하고 커밋한다.
- [ ] 단일 엔진 L3/L2 기능 사례를 순차 실행한다. actual signed command·속도·접촉·관측·정착·terminal·join·잔여를 확인하고 실패 원본/소스/보고서를 커밋한다. 엔진 중 build/pytest/대용량 분석은 병행하지 않는다.
- [ ] 연속 기능 gate가 통과하면 새 source/scenario/10UUID를 고정하여 새 10회를 실행한다. 높이·정밀도·시간 수치 실패를 그대로 보고하며 기존 v28 결과를 대체하지 않는다. 기능 미통과 시 새 평가로 실패 원인을 덮지 않고 원인 조사로 돌아간다.

## Review focus

모든 checker의 독립 latch, shim과 primary의 동일 namespace, 역방향 경로 cusp와 shim의 orientation 해석, 원래 first receipt/GID 유지, native goal/lease 변경 여부, 실제 음수 vx가 정책에 전달되는 경계, 대조 지도와 실제 costmap의 차이를 확인한다. 단일 작업자의 자체 검토로 기록하며 독립 리뷰로 표현하지 않는다.
