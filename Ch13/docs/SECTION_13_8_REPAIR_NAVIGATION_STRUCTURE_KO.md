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