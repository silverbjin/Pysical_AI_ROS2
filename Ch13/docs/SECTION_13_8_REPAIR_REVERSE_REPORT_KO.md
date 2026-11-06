# 13.8 후진·목표 회전 적용 보고

2026-11-06 KST. 중단된 회귀 RED 단계에서 단일 작업자로 재개했다. 명세는 SECTION_13_8_REPAIR_REVERSE_PLAN_KO.md다.

## 적용 내용

새 L2/L3만 Smac REEDS_SHEPP와 공식 RotationShimController(primary RPP)를 선택한다. RPP는 allow_reversing=true/use_rotate_to_heading=false로 구성하고, shim의 rotate_to_goal_heading/use_path_orientations/rotate_to_heading_once를 true로 둔다. 별도의 ROS owner나 새 native goal API는 추가하지 않았다.

설치 1.3.13에서 실제 소비하는 `.position_checker.stateful=false`를 YAML로 지정한다. 정상 prefix인 FollowPath.position_checker.stateful도 false를 명시하지만 현재 버전에서 그 키만 설정하면 내부 latch는 유지된다는 것을 실제 configure/동작으로 확인했다. 회전 속도 .15rad/s·가속 .5rad/s²·목표 XY .015m/yaw .06rad와 native guard를 유지한다.

두 시나리오는 부품 경로 검사를 통과한 서쪽 접근만 사용한다. 일반 방향 선택의 강건성을 주장하지 않는다. smoother 후진 하한 -0.10m/s, 기존 yaw cap L2 .10/L3 .20rad/s, max vx .20과 가속도는 유지한다. native 입력의 원래 ±.2 한계나 정책·모델·effort·관측 수명·footprint/지도 해상도는 바꾸지 않았다. legacy/L1의 제어기와 전진 설정도 유지한다.

## 실제 부품 검증

- 설치된 PositionGoalChecker 기본값은 12mm 도달 후 20mm로 이탈해도 도달로 유지했다. 실제 YAML의 내부 stateful=false 후 이탈을 false로 재판정했다.
- 실제 controller_server configure/cleanup에서 잘못된 prefix만 지정한 경우 FAIL, 내부 키를 지정한 경우 PASS였다. 공식 shim/RPP 로드와 원래 회전 속도/가속도를 조회했다. 이는 엔진 없는 구성 검증이다.
- CLI `-p`로 leading-dot 키를 주는 방식은 ROS 인자 문법에서 거부됐다. 이 도구 실패를 보존하고 실제 YAML 방식으로 검증했다. 외부 라이브러리를 수정하지 않았다.
- 중단 시점 회귀 7 FAIL/5 PASS → 설정 반영 후 관련 14 PASS/45.70초. 실제 ROS parser·legacy 격리·카메라 가시성 검사를 포함한다.

공식 ref와 채택/기각한 대조는 REPAIR_REVERSE_PLAN 및 STEP4_VALIDATION에 있다. 실제 적재 후진, 연속 임무, 관측/health 만료 재발 여부와 높이 목표는 아직 별도의 실제 사례로 확인해야 한다.

## v35 실행 전 검증

분리 build 5개/21.2초, navigation 38·manipulation 24·BT 6 및 실제 venv child 69 module 감사 PASS. 전체 437 PASS/83.46초. source 383개/외부94자산, tested/runtime source 전수 hash 일치 PASS. manifest SHA256 ac5894e0c059dbbc12008c2ef820b86934cbce99168497c72986cdec54101942. 실제 L3/L2 UUID와 기능/엄격 수치 판정 구분은 step4_preflight_v35/case_plan.json에 실행 전에 고정했다. 숫자 목표를 못 맞추면 원래 strict FAIL을 보존한다.
