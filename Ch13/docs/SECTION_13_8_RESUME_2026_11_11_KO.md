# 13.8 개발 재개 기록

로그 정리 이전 마지막 개발 커밋은 e3efae2b다. v36 실제 L3 금지 접촉·L2 survey deadline 실패를 보존하고 v37 명세를 작성한 상태였다. 미추적 test_planning_clearance.py만 있고 구현 모듈은 없었다. 사용 한도 중단의 정확한 시스템 시각은 이번 파일 조사만으로 확인하지 못했으나, 재개 가능한 코드 지점은 v37 A의 RED 시험 직전이다.

2026-11-11 A 재개: 실제 WSL venv·native source snapshot으로 8 failed/3 passed/440 deselected(4.47초)를 재현했다. Level3만 reuse/link3 30mm padding을 ApplyPlanningScene diff로 설정하고 GetPlanningScene에서 확인한다. 적용 실패·누락·불일치는 계획 전에 거부한다. nondefault padding/scale을 scene hash에 포함하고 기본값에서는 기존 hash를 유지한다. run_pick의 world objects 적용 직후 opt-in으로 연결했다. 관련 시험 11 passed/440 deselected(2.68초). 이는 실제 물리 성공 증거가 아니다.

공식 MoveIt2 2.12.4 planning_scene.cpp의 diff 및 padding 처리 패턴을 재조회했다: https://github.com/moveit/moveit2/blob/2.12.4/moveit_core/planning_scene/src/planning_scene.cpp . LinkPadding 2.6.0 웹 조회는 cache miss였으므로 이전 명세와 실제 설치 메시지에 의존하는 시험을 구분한다. 시험은 실제 ROS 메시지와 fake service port를 사용하며 실제 MoveGroup readback·build·새 freeze·engine 확인은 후속 gate다.

다음 순서는 v37 B(관측 waypoint용 별도 goal checker와 XML·Action 연결)의 RED/GREEN, 전체 회귀, 분리 build/실제 설치·자산 감사·새 source freeze, 필요한 L3/L2 실제 기능 확인이다. 기능 gate 통과 전 새 고정10회에 진입하지 않는다. 과거 10회 0/10과 새 개발 사례를 합산하지 않는다. 로그 정리 커밋 4개와 이전 FAIL/source freeze를 보존한다. 단일 작업자로 진행한다.

v37 B 재개: 실제 ROS parser 시험 2 FAIL/Action 연결 1 FAIL을 먼저 확인한 뒤 관련 3 PASS(3.58초). 새 L2/L3만 controller_server에 survey_checker(.06m/.06rad/stateful true)를 추가하고 survey Goal의 behavior_tree를 설치된 navigate_survey.xml로 지정한다. 최종 goal_checker(.015m), 기본 XML, 기존 소유 goal·cancel/drain·정착·관측 권한은 유지했다. Nav2 공식 1.3.13 FollowPath 입력 패턴은 기존 v37 명세의 조사를 재사용했다. 이번 raw GitHub 재조회는 cache miss였음을 구분한다.

전체 native snapshot 회귀 454 PASS/65.39초. 첫 잔여 점검은 회귀 실행 중 시험 ingress가 잡혀 FAIL이었으며, 회귀 종료 후 재점검은 잔여[]/lockfree/PASS였다. 타 프로세스 강제 종료는 하지 않았다. 분리 build 5 packages/18.5초, 설치70모듈·원본94자산·실제 child NumPy 감사 PASS. v37 source389/assets94 SHA256=1b08448846e3f9b280ed770e0a6c04e86a4cee89d9e9d216f64b042f78d24642. full454의 source389와 새 freeze 전수 일치, 설치된 두 새 설정 파일 바이트 일치 PASS. Level3 실제 사례 UUID6612d326-ae6c-4847-abe6-993e05150ec5를 사전 고정하고 실행을 시작했다. 이 문단 시점에는 물리 결과 미확정이다.
