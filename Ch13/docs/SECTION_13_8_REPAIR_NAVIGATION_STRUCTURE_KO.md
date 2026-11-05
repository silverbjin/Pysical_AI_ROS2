# 반복 도달 실패의 구조 검토와 후속 설계

2026-11-05 KST. 단계4의v30/v31/v32실패를보존하고실제engine반복대신설치된Nav21.3.13의작은부품으로비교했다. 이문서는후속변경전설계와근거이며물리성공증거가아니다. 단일작업자로연속진행한다.

## 확인한 경계

v32 L3(02676843-e611-4161-89d0-16d71df94863)는52.562sim/124.543wall초, L2(9590b5a2-052a-49d3-9d54-e97fe7c1d374)는57.478sim/124.152wall초의surveydeadlineFAIL이다. 두engine정상종료/12child회수/잔여0이다. 같은실패계열에서작은설정보완뒤에도도달하지못했으므로경로의자세조건과지도수명경계를재검토한다.

기존NavFn은XY경로를만들지만마지막경로접선과목표yaw에약45도차이를남겼다. 설치된SmacHybrid는같은지도·footprint로SE2곡선을만들며원래L3survey(1.9,.4,.499)의접선오차약.001rad를보였다. 반경.4조건에서는추가접근후보가거부됐고,.3조건에서는원래survey와서쪽접근(2.4,1,0)이계획됐다. .3은계획조건비교이며실제동역학안전보장이아니다. 원래실측vxy/yaw에서약.333m궤적반경이관측됐으며실측안전.35rad/s는유지한다.

독립Python SAT/실제비용지도/공식C++GridCollisionChecker대조에서후보endpoint자체는충돌없음이었다. 오류문자열StartOccupied를실제접촉으로해석하지않는다. 공식SmacPlannerHybrid는검색실패시iteration1이면그오류를던지므로초기동작확장거부와endpoint충돌은다르다. 공식worldToMapContinuous도직접조회했고반셀오프셋추정은채택하지않았다. 직접C++검사는같은12,000byte비용지도·paddedfootprint를썼으며모두collisionfalse였다.

동일반경.3에서옛대상셀을그대로둔귀환은거부됐지만,파지후옛대상셀만제외한대조에서서쪽귀환5.093m경로가계획됐다. 따라서MoveIt attach와별개인Nav2정적대상자리수명이필요하다. 이대조에서live지도나실제물체를조작하지않았다.

L2의원래survey(1.7,.3,.494)는SE2경로가거부됐고,(1.6,-.3,.6)는1.738m경로와후속서쪽접근1.542m경로가계획됐다. 새지점은기존박스와의여유를검사하고실제RGB-D가시성을확인한후에만적용한다. L3survey는원래지점으로복원한다. 새정렬지점(1.9,1,0)은기존XY계획의큰회전을옮겼을뿐이므로기본으로추천하지않는다.

## 공식 참고

- [SmacHybrid공식테스트1.3.13](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/test/test_smac_hybrid.cpp): 설치플러그인configure/activate·actualcreatePlan패턴.
- [SmacPlannerHybrid구현](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/src/smac_planner_hybrid.cpp),[collisionchecker](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/src/collision_checker.cpp),[costmap좌표변환](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_costmap_2d/src/costmap_2d.cpp).
- [공식이슈5996](https://github.com/ros-navigation/navigation2/issues/5996)는다른ROS버전에서경로평활화와유효성불일치를보고한다. 이번Jazzy에서같은버그를확인했다는뜻이아니며경로서비스성공만믿지않고동일지도의경로유효성을추가확인하는근거로사용한다.

## 후속 최소 구현 명세

1. 새L2/L3만기존설치SmacHybrid의forwardDUBIN/반경.3/각도72bin/maxplanning2초를선택한다. reverse·정책·물리·충돌guard를추가/완화하지않는다. legacyNavFn은유지한다. 단일GridBased플러그인식별자는기존ActionAPI와같게유지한다.
2. 새survey지점과actualcamera가시성/footprint를검증한다. 위치IK와실제Nav2SE2경로비용후보검사를유지한다.
3. nativeEngineExtension상태의처음publisherGID/session을고정하고,fresh CARRY_ARMED·동일outbound/reservedgoal·실제양finger접촉·forceholdready·건강한nativelease에서만옛target셀제거를latch한다. WAITING/READY문자열만으로제거하지않는다. freejoint평가좌표는사용하지않는다.
4. 다른정적벽/다리/박스는변경하지않는다. 초기지도와대상제외지도는동일기하에서미리만들고같은publisher로갱신한다. 새Trigger는읽기전용확인이다. worker는같은ROSowner의비동기서비스poll로session/goal attestation과실제globalcostmap대상셀갱신을확인한뒤예약귀환goal을보낸다. BT update/terminate에blocking을추가하지않는다.
5. stale/owner교체/session교체/접촉누락/falsehold/잘못된goal/costmap미갱신은거부하고새motion권한을만들지않는다. 제거는해당engineepisode한번이며fault후자동재활성화하지않는다. 다음engine새WorldMap에서초기상태로시작한다.
6. RED→최소구현→관련및필요전체회귀·actualchild설치·새sourcefreeze→필수실제사례순서다. 기존v28총10회0/10과새실패는보존한다. 실제기능gate를통과하기전새10회로실패를덮지않는다.

## 비용과 한계

새일반객체인식·학습·WBC·실기드라이버·OS변경은없다. 공식플러그인이이미설치돼전역의존성설치는없다. 지도갱신은경로기하를바꾸며물리부착이나arm/navlease를대신하지않는다. 계획반경이실제정책의폐루프추종을보장하지않으므로실제속도·접촉·회수판정은계속필수다. 구현및실제결과는후속기록으로갱신한다.
## 2026-11-05 추가 구현과 작은 부품의 결과

`cache_obstacle_heuristic=true`에서는 같은 귀환 목표를 유지한 채 지도를 갱신해도 이전 장애물 탐색 정보가 남았다. 같은 publisher의 전체 지도 갱신은 실제 StaticLayer에서 대상 비용 254→70으로 관측됐지만 귀환 계획은 거부됐다. 캐시만 false로 바꾸자 계획이 반환됐다. [설치 버전 AStar::setGoal](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_smac_planner/src/a_star.cpp)의 목표 변경/캐시 조건과 일치한다. [공식 설정 설명](https://docs.nav2.org/configuration/packages/smac/configuring-smac-hybrid.html)은 캐시를 대체로 정적인 지도에서 사용하는 최적화로 설명한다. 최신 문서의 모든 새 매개변수를 Jazzy 1.3.13에 적용한 것은 아니다.

계획 성공만으로 실행 가능하다고 판단하지 않았다. 실제 반환 pose 전체와 원래 직사각형 footprint(+기존 1cm padding)에 대해 채워진 다각형 SAT 검사를 추가했다. 서쪽 귀환은 평활화 true에서 충돌 pose 10개, false에서도 2개가 남았다. 따라서 평활화만 원인이라고 단정하지 않는다. padding 2cm 비교도 2개가 남았고 4cm 비교는 계획 자체를 거부했다. 이 여유 변경은 제품 설정에 채택하지 않았다. 원래 footprint와 1cm padding을 유지한다.

반면 평활화 false의 북쪽 접근(3,1.6,-π/2) 및 대상 자리 제거 후 북쪽 귀환은 모든 반환 pose에서 채워진 footprint 검사를 통과했다. Ruling: L3 고정 교육 시나리오는 검증된 북쪽 접근 방향 하나로 제한한다. 일반 방향 탐색 성공이나 모든 접근의 강건성을 주장하지 않는다. 더 긴 경로와 제한된 접근 범위가 비용이다. 원래 L3 survey는 유지하고, 새 L2/L3 계획에서 평활화와 장애물 캐시를 false로 명시한다. 실제 폐루프 성공 여부는 별도 engine 사례로 판정한다.

북쪽 가상 배치의 MoveIt 검사는 과거 4개 실제 joint/tilt 표본을 회전·이동한 계획 전용 입력이다. 실제 북쪽 이동 증거가 아니다. pre-grasp/grasp 8개 모두 설치된 collision-aware IK와 GetStateValidity를 통과했다. 실제 Renderer의 survey 및 설정된 접근 방향 전체에 대한 알려진 원통 fit 검사도 통과했다. 실제 원고 관측 수명과 원본 capture는 그대로 유지한다.

지도 변경은 native 상태의 최초 GID/session, fresh CARRY_ARMED, 서로 다른 outbound/reserved goal, 실제 양 finger 접촉, force-hold ready와 capture health가 모두 있을 때 한 번만 허용한다. 읽기 전용 Trigger 응답과 실제 global costmap 갱신을 같은 ROS owner에서 비동기로 확인한다. 지도 갱신은 물리 부착이나 이동 권한을 만들지 않는다. 기존 정적 벽·다리·박스는 보존한다.

L2 비교에서는 대상 제거 후 중심 비용이 254→253이었다. 이는 주변 table leg의 inscribed inflation이며 대상 자체의 lethal 점유와 구분해야 한다. 지도 ACK는 `<254`를 확인하도록 회귀 검사에서 먼저 실패를 재현했다. 로봇의 경로/충돌 허용 임계값은 바꾸지 않았다. 그러나 서쪽 L2 귀환은 여전히 NO_VALID_PATH였다. L2 전체 연속 기능은 아직 통과하지 않았으며 새 10회 평가의 진입 조건을 충족하지 않는다.

부품 결과: 최초 지도 gate 18 PASS, 실제 WorldMap callback 추가 후 20 PASS, 비동기 worker까지 22 PASS. worker의 응답 전 시각을 재사용한 fresh 검사 오류는 응답 수신 후 시간을 읽도록 수정해 22 PASS(3.46초)했다. filled-route 2 PASS(3.32초), 캐시 수정 관련 28 PASS(24.52초), 북쪽/평활화·카메라·후보 8 PASS(22.18초). 실제 ROS parser 검사에서 캐시 2 FAIL, 평활화/북쪽 3 FAIL을 먼저 확인했다. 새 전체 회귀 및 실제 engine 결과는 단계4 보고서에 추가한다.

진단 도구의 XML `name` KeyError, Python 들여쓰기 SyntaxError, 잘못 전달된 root 경로와 L2 ACK 가정 실패는 각각 도구/계획 검증 실패로 보존한다. 이들은 실제 물리 실패 횟수에 포함하지 않는다. v32 실제 L3/L2 실패는 별도 raw archive와 정확한 376개 소스 바이트로 보존했고 원본을 삭제하지 않았다.