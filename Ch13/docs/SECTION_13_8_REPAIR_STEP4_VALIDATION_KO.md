# 단계 4 — 수정 소스의 실제 검증과 새 평가 gate

2026-11-05 KST. 이파일은실제사례의종료후최종갱신한다. 이전단계의부품PASS를물리성공으로표현하지않는다.

## 실행 전 동결

- 단계별커밋:계획eaadea27,Level3 d4c9a1d3,촬영a843ce85,운반명령f045a111,실행전동결c50727b8.
- v30 source376/assets94,manifest SHA256 `816e0d8cfa2385d9080bc4c2082bb2ce2f4032227d28fa3d683ab13ef6522298`.
- 분리build20.5초,실제venvchild설치67모듈/기존94자산감사PASS. navigation설치자료35개(새YAML포함),manipulation24,BT6감사PASS.
- 전체399 PASS/70.33초. 동일376소스hash전수일치. Level2추가YAML source/install SHA256 `0a4ab3c88c20dcbd4521f0d9857a1e252b53110582bb5d36d270d0983e7ee41f`.
- 관측/물리/취소·회수threshold는유지했다. Level2 yaw명령상한만낮췄으며시간목표에유리한튜닝은아니다.
- 현재WSL boot `c5eba66c-cb54-4639-852b-ad9fc2d2aa5b`;실행전소유잔여0/공유lockfree. 과거boot의잔여PASS를현재증거로대체하지않았다.

실행전증거는`../evidence/section_13_8_repair/step4_preflight/`에있다. 두후속UUID/source를실행전에보존했고Level3→Level2순서로한engine씩실행한다. 기존v28 총10회와이후v29실패는보존한다.

## 실제 사례

|시나리오|UUID|상태|
|---|---|---|
|Level3 v30|673e9986-5f34-430d-b695-973feb6da98d|FAIL: survey120wall초,최종접근/팔미시작|
|Level2 v30 계획|97fad3a0-9660-432b-94ae-a300c0363ef4|미기동:대조소스v31로분리예정;본10회아님|

## 새 총10회 gate

두기능의실제접근·fresh관측·파지·연속운반·놓기·종료가통과한뒤새동결/source/scenario/10UUID를고정한다. 실패/시작실패도분모10에남긴다. 필수기능이남으면같은실패를10번반복해통계로덮지않고미충족gate와저장재현과제를명시한다. 기존0/10을지우거나다른조건의사례로교체하지않는다.
## v30 실제 실패와 촬영 제출 대조 조건

L3 v30은trial elapsed6.446sim/133.757835wall초,successfalse/complete true였다. 지도관측이동의기존120wall초deadline에서중단돼최종접근·새pre-grasp까지도달하지못했다. 새기하학수정의실제성공을주장할수없다. engine은ownedlaunch회수중KeyboardInterrupt로ERROR,정상종료요청false,자식11/12clean·engine1exit1·잔여0/공유lockfree였다. 이실패를정상종료로바꾸지않는다.

실행당시8CPU/메모리여유/스왑0을읽기전용으로확인했다. 마지막256capture의statepublish평균41.367ms/최대146.958ms,pre-offer평균7.693ms였다. 조기제출은직렬대기는줄였지만현재실행의전체성능성공을입증하지못했다. 같은설치함수의offline100회/no-opDDS profile은.59146wall/.59139CPU초였다. 이대조는liveDDS/부하가없어실제지연상한이나overlap인과증명이아니다. SciPy1.18.1/NumPy2.5.4/Torch2.9.0+cpu이며과거보고와같은SciPy버전이므로업그레이드탓으로단정하지않는다.

Ruling: v30의미통과상태에서조기제출을기본추천하지않는다. 원래직렬순서로되돌리고carry_v1+CH13_CAPTURE_OVERLAP=1에서만실험적으로사용하게한다. 수명/TF/상태발행빈도/속도/OS설정을바꾸지않는다. 이대조의새freeze v31로한번더확인하고,성능실패가반복되면계층경계를재검토하며동일실패를새10회로덮지않는다. v30의모델제외raw/source archive와hash를보존했다.
## v31 대조와 두 개의 XY 상태 경계

v31(source376/assets94 SHA256dba3874e7ac7cf1adc3a3cac4a06e5008c8347d54f2b411a1e64539c7eeef3f0)은전체402 PASS/59.57초·동일sourcehash·설치감사뒤CH13_CAPTURE_OVERLAP=0으로실행했다. L3 UUID1d76511d-810d-41bb-a3c4-1db69ecb15bc는elapsed53.2sim/128.866wall초로진행속도는회복됐지만같은survey120wall초deadline에서FAIL이었다. engine정상종료·12child정상회수·잔여0/lockfree. v31계획L2 86f26a07-e692-483a-88d4-0754be975dc1는이경계진단때문에아직기동하지않았다. 후속계획이지본10회slot이아니므로성공으로대체하거나숫자를섞지않는다.

저장궤적에서survey목표(1.9,1,0)의최초XY통과는오차14.379mm/yaw1.590514rad,최소XY오차5.502mm/yaw1.579378rad였다. 이후최종yaw회전중오차303.301mm로이탈했다. 앞선진행해석중최종접근이라고했던구간은survey였고원본event로정정했다.

[공식Nav21.3.13 RPP controller](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/regulated_pure_pursuit_controller.cpp)의shouldRotateToGoalHeading과[parameter_handler](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/parameter_handler.cpp)를읽었다. RPP의FollowPath.stateful도별도로기본true여서최초XY통과후방향회전에머문다. 앞선goal_checker.statefulfalse만의수정은불완전했다. 목표판정기는XY복귀를요구하지만제어기는방향회전에latched되어XY를복구하지않는조합이다.

Ruling: 같은도달/회전계열이최소수정후에도남아두상태경계를함께재검토했다. 새L2/L3에서만FollowPath.statefulfalse도명시한다. goal_checkerfalse·XY.015/yaw.06·속도/충돌검사/수명/물리안전한계는유지한다. 두실제ROSparam의일치시험2 FAIL/3 PASS(4.19초)를확인했고새동결v32로별도검증한다. 현재원인이설치원본과실제궤적에맞는다는것과실제수렴성공은구분한다.

짧은sleep0/.5/1/2ms20회씩계측은각평균.058/.537/1.061/2.054ms였다. OS대기정밀도저하가이번문제의확정원인이라는가설은지지되지않았고OS시간/우선순위설정을바꾸지않았다. v30/v31의성능차이만으로overlap인과를확정하지않는다.

## v32 및 구조 보완 진행

v32의 L3 02676843-e611-4161-89d0-16d71df94863와 L2 9590b5a2-052a-49d3-9d54-e97fe7c1d374는 각각 survey deadline FAIL이다. 두 engine 정상 종료·12 child 회수·잔여 0이다. source 376개를 실제 native snapshot과 hash 대조해 보존했다. L3 raw 13,952,561 bytes, L2 raw 14,582,029 bytes이며 원본은 유지한다. 구조 원인과 후속 구현은 [경로·지도 수명 보고서](SECTION_13_8_REPAIR_NAVIGATION_STRUCTURE_KO.md)에 기록한다. 새로운 10회 평가의 기능 gate는 아직 통과하지 않았다.

### v33 실행 전 동결

분리 build 5 packages/15.4초, 설치 감사 navigation 38·manipulation 24·BT 6 및 실제 venv child 모듈 감사 PASS. 전체 432 PASS/57.25초이며 모든 테스트 소스가 v33의 382개 소스와 일치한다. 외부 94 자산 및 공유 lock 실제 경로를 확인했다. manifest SHA256=05eb3e8ac12be65d568e63a2f56c608899dfba3eb5ef2b201f7c9ee966269b24. L3 UUID=99a9e20e-1713-42b7-8dd3-24379f9b6812 를 실행 전에 고정했다. 아직 실제 성공 주장이 아니다.

### v33 실제 시작 실패와 콜백 경계 보완

L3 UUID 99a9e20e-1713-42b7-8dd3-24379f9b6812는 실제 실행을 시작했지만 world_map 콜백의 KeyError: publisher_gid로 시작 단계에서 실패했다. trial 11.15sim/23.949wall초, BT runner 37.173wall초다. engine은 정상 종료했으나 지도 노드가 비정상 종료하여 11/12 child 정상 회수이며 실제 잔여는 0이다. 파지·운반 기능 성공이나 경로 실패로 해석하지 않는다.

직접 콜백을 호출한 기존 검사가 실제 rclpy 메타데이터와 중계 메타데이터의 차이를 놓쳤다. 실제 DDS→WorldMap 재현 검사에서 먼저 1 FAIL/432 deselected(21.11초)을 확인했다. 기존 C++ ingress의 rclcpp::MessageInfo/get_rmw_message_info 패턴을 재사용해 native GID·원래 첫 receipt·변경 없는 CDR을 전용 latest-only 채널로 전달한다. Python callback 정보에 publisher_gid를 새로 만들거나 현재 시각을 원래 receipt로 치환하지 않는다. relay 최초 소유자도 고정하고 교체·stale 패킷은 거부한다. [ROS2 공식 C++ MessageInfo](https://github.com/ros2/rclcpp/blob/jazzy/rclcpp/include/rclcpp/message_info.hpp)를 참고했다. Jazzy Python 문서는 접근 차단, 7.1.12 소스 URL은 조회 실패였으며 그 실패를 설치 API 확인으로 꾸미지 않는다. 실제 송수신 회귀와 새 동결 v34로 재확인한다.


v34는 전체 433 PASS/62.72초. 검사/실행 소스 383개 hash 일치, 외부 94 자산, 실제 venv child 69 module 감사 PASS. L3 UUID=9e160887-cc8a-4f1d-a4e7-83aae4f77818 를 실행 전에 고정했다. manifest=0faa40478e47270fb2c3f298b1c16511902612dbf7c682668bc72fd55b0dce4c。

### v34 실제 결과: survey 통과, 접근 계획 거부

UUID `9e160887-cc8a-4f1d-a4e7-83aae4f77818`은 실제 survey 도달과 정착을 통과했다. 실제 base 표본은 약 (1.899597, 0.394613, yaw 0.558953)이며 목표 yaw 0.499347과 다르다. 이후 실제 관측점 기반 북쪽 접근 (3.000101, 1.599997, -π/2)의 ComputePathToPose가 status 6 / error 208 NO_VALID_PATH를 반환해 파지 전에 실패했다. trial 16.890sim/42.282wall초다. engine 정상 종료, 자식 12개 정상 회수, 실제 잔여 0이다. DDS 수정 성공과 접근/파지/운반 미성공을 구분한다.

원래 v34 소스 383개를 native snapshot에서 hash 검증해 보존했고 raw archive 6,821,790 bytes를 추가했다. 원본과 과거 v28 0/10은 그대로다. 새 10회 평가는 아직 실행하지 않았다.

실제 정착 표본과 실제 관측 목표를 설치된 planner에 넣는 정적 지도 부품 대조를 수행했다. 실제/이상 시작과 실제/이상 목표의 네 조합에서 5cm 지도 기본 설정은 두 계획 거부·한 filled-footprint 충돌·한 통과였다. 각도 보간만 켜면 계획 반환은 늘었지만 충돌이 남았다. padding 4cm는 더 보수적이지만 접근 자체가 거부됐다. 2.5cm 지도는 실제 정착 입력 두 조합의 충돌 없는 경로를 반환했으나 이상 시작 두 조합은 거부됐다. 보간을 더한 비교도 모든 입력을 통과하지 못했다. 이 비교들 때문에 운영 설정을 바꾸지 않았다. 실제 live costmap과 정적 대조 지도는 같다고 주장하지 않는다.

반복 양상은 단순 파라미터 하나의 누락보다 전진 전용 SE2 도달/탈출과 좁은 통로의 격자 민감성이다. L2도 지도 갱신 뒤 서쪽·북쪽 전진 귀환 계획이 거부됐다. 원래 safety guard는 vx를 ±0.2로 제한하고 upstream joystick/console은 음수 vx를 전달하는 경계가 있지만, 이는 적재 후진의 물리 성공 증거가 아니다. 공식 Smac REEDS_SHEPP / RPP reversing 패턴을 먼저 작은 부품으로 비교하고 별도 설계·회귀 뒤에만 실제 적용을 판단한다. 기존 물리 guard, 관측 수명, effort와 목표 수치는 유지한다.
