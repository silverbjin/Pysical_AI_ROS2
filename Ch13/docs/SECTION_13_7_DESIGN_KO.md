# 13.7 BT 미션 오케스트레이션 설계안

2026-11-04 KST. 상태: **범위 선택 완료, 상세 설계 승인 대기**. 단일 작업자 조사·자체 검토. 구현·설치·물리 인수 완료 문서가 아니다.

## 목적과 승인된 범위

첨부 원고 「13.7. 미션 오케스트레이션: Behavior Tree(BT)를 활용한 임무 관리」의 13.7.1~8을 학생이 실행할 수 있는 ROS 2 패키지와 한국어 가이드로 연결한다. 사용자는 이번 대화에서 **기존 기능의 실제 BT 통합 + 확장 동작 모의 실습**을 선택했다.

실제 실습은 기존 Go2+Piper의 동일 엔진에서 BT가 Nav2 접근 → 정착 → 새 RGB-D 관측 → 기존 MoveIt 파지·lift·hold → 권한 회수·정상 종료를 관리한다. 기존 run_pick 프로세스 전체를 잎 하나로 감싼 뒤 세 기능을 통합했다고 표현하지 않는다. 이동·관측·파지는 서로 다른 잎이며, 각 시작·완료는 실행 기록으로 구분한다.

원고의 부엌/콜라는 교육 장면의 접근 지점/20g upright 원통에 대응한다. YOLO 일반 객체 인식으로 표현하지 않는다. 귀환 운반·기립·충전은 별도 모의 프로필이며 실제 로봇 제어 엔드포인트와 연결하지 않는다. 배터리 값 역시 기존 플랫폼에서 검증한 센서가 아니므로 교육용 주입값임을 명시한다. 실제 저전력 주입 시험은 정책을 바꾸지 않고 BT의 취소·안전 정지 선택만 확인한다. 실제 넘어뜨리기·기립은 하지 않는다.

## 기준과 격리

- 개발 기준 commit: f9957a5535ff56b321db334a241cd689b4f3e583, v14 source freeze의 소스251·외부94자산 일치 확인.
- PR #115는 현재 병합됨. merge commit 956919aef2a9732cc7be4c311fa2789f17a43945. 이 설계는 계속 지정된 f9957a55에서 시작한다. 새 PR은 최종 main과 diff를 확인하여 13.7 범위만 게시한다.
- 새 작업 경로 후보: work/Pysical_AI_ROS2_13_7, branch feat/ch13-section-13-7. 사전 조회 시 둘 다 없음. 기존 13.6 linked worktree를 재사용하지 않는다.
- 새 build 후보: /home/jinho/ch13_reuse_13_7_build. 실존·realpath 확인 후 사용. 기존 R2/R5/13.6 개발·다운로드 검증 경로 및 그 하위 경로를 새 build 도구에서 거절한다. 13.6 env.sh의 기본 build를 그대로 쓰지 않는다.
- 새 패키지 제안: ch13_mission_orchestration. 새 scripts/reuse_13_7, dependencies/section_13_7_*, evidence/section_13_7_bt를 사용한다. 기존 freeze·FAIL·사용자 파일·sources 및 Ch01~12는 보존한다.
- 공유 engine lock은 기존과 같은 저장소 상위 경로를 사용한다. 새 worktree 전용 lock으로 바꿔 중복 엔진을 허용하지 않는다.

## 접근 비교와 선택

1. **기존 실행 경계에 작은 세션 hook + BT 비동기 어댑터**: 기존 정책·장면·물리·수명을 재사용한다. 기존 blocking 함수를 BT 바깥의 단일 소유 실행자로 격리하고 시작·결과·취소 경계를 추가해야 한다. 권고 방식이며 사용자의 기존 기능 실제 통합 선택에 대응한다.
2. **새 mission에서 모든 ROS 클라이언트와 실행 수명 재작성**: BT 코드는 직접적이지만 기존 gateway admission·planner 회수·join 로직을 복제하고 회귀 범위가 커진다. 채택하지 않는다.
3. **run_pick 전체를 subprocess 잎으로 실행**: 변경은 작지만 이동·관측·파지가 BT 내부에서 제어되지 않고 단계별 중단도 불투명해진다. 기본 실제 실습으로 채택하지 않는다.

구체적 세션 API/패키지명은 구현자의 제안이다. 부품 조사에서 더 작은 동일 계약의 구현이 확인되면 설계 변경 기록에 근거와 영향을 남긴다. 단일 작업자 요청에 따라 별도 검토 에이전트는 사용하지 않았다.

## 실행 구조와 연결 경계

BT의 initialise/update/terminate는 대기·sleep·nested spin을 하지 않는다. update는 작업 요청 또는 완료 snapshot 조회만 수행하며 RUNNING을 반환한다. ROS 액션의 goal 전송 future와 get_result_async future를 분리한다. accepted는 SUCCESS가 아니다.

기존 run_navigation_probe와 run_handoff/run_pick의 opt-in 경계를 조사해 **하나의 소유 세션 어댑터**를 둔다. BT가 이동/관측/파지의 시작을 명령할 때까지 해당 단계는 시작하지 않는다. 원래 13.5/13.6 호출에서는 새 hook이 비활성화되어 기존 실행 순서를 유지한다. 기존 probe/bridge/보행 loop 전체를 복사하지 않는다.

기존 blocking 실행은 한 소유 worker에서 순차 수행하며 그 worker만 기존 robot ROS node를 spin한다. BT는 별도 mission node에서 100ms 틱을 수행한다. 양쪽은 bounded 요청 큐와 immutable 상태 snapshot으로 연결한다. worker의 기존 until 루프에서 취소·종료 요청을 짧게 확인한다. ROS future나 mutable 메시지를 두 spin 실행자가 동시에 다루지 않는다. ROS context 초기화/종료와 node 생존 책임을 명시하며, BT node를 먼저 파괴해 취소 완료를 놓치지 않는다.

소유 세션의 최소 경계:

| 경계 | 요청과 완료 조건 |
|---|---|
| 준비 | 단일 launch/engine 및 session 확보, startup/admission 조건 확인 |
| Navigate | 기존 실제 관측 기반 접근 goal 선택, Nav2 async goal/result, actual pose와 정착 확인 |
| FindObject | 도착 후의 새 capture 확보, 원래 capture/TF/receipt/GID와 cylinder fit·workspace 검사 |
| Pick | 같은 engine/session의 live lease 발급, 기존 계획·그리퍼·접촉·lift·hold 절차 재사용 |
| Cancel/Stop | 현재 소유 goal에 취소 요청, 실제 terminal·물리 정착·권한 회수까지 별도 상태로 추적 |
| Close | 살아 있는 시계에서 planner 회수 → engine 정상 종료 → worker/RX/renderer/자식 join·잔여 검사 |

worker 예외는 명시 FAIL snapshot으로 전달한다. 취소 중인 작업의 늦은 수락·늦은 결과는 세대 ID로 구분한다. 잎이 INVALID가 돼도 어댑터는 pending send/goal의 책임을 유지하고 늦게 수락된 goal을 취소한다. cancel ACK, action terminal, 실제 정지, 프로세스 종료를 각각 기록한다. 취소 timeout/강제 종료는 정상 종료 PASS로 세지 않는다.

파지 중에는 기존 안전한 감속·force hold를 유지한다. 임의 gripper open/수납/torque0을 하지 않는다. 불필요한 새 Nav goal을 보내 lease를 깨거나 종료한 pick 뒤 다시 engine을 붙이지 않는다. 기존 lease REVOKED는 terminal이며 재활성화하지 않는다. 정상 mission terminal은 한 번만 확정하고 이후 틱으로 이동/파지를 재시작하지 않는다.

## 트리와 Blackboard

실제 프로필의 root는 memory=False Selector다. 최우선 가지는 StopRequired 조건 → CancelAndSettle → mission abort latch이며, 그 아래 Main Mission은 memory=True Sequence(CheckBattery, Navigate, FindObject, Pick, Finish)다. StopRequired는 사용자 취소·교육용 저전력 주입·플랫폼 fault/비정상 상태를 다룬다. fault는 engine의 기존 latch가 최종 권한을 가진다. BT의 10Hz 검사로 300ms watchdog을 대체하지 않는다.

Main의 배터리 검사는 시작 조건이다. 실행 중 저전력은 최우선 가지에서 매 tick 확인한다. 원고처럼 FAILURE를 반환하는 BatteryCheck만 Selector 첫 자식에 두면 다음 이동 가지가 선택되므로 올바른 preemption 구현이 아니다. stop 가지가 완료돼도 abort latch를 유지하여 다음 tick에 mission이 자동 재개되지 않게 한다.

Blackboard는 mission/session/goal ID, target 관측 payload, current task, cancel 상태, terminal과 실패 원인을 보관한다. target_pose와 함께 capture_ns, capture_wall, tf_stamp_ns, first_receipt_wall, source_gids 및 내용 hash를 보존한다. 저장된 Blackboard가 새 lease/권한이 되지 않으며 Pick 진입·계획 실행 직전에는 live 원본 관측을 다시 검증한다. 새 임무에는 별도 key namespace/세대 ID를 사용해 이전 결과가 섞이지 않게 한다.

모의 프로필은 같은 기본 트리 구조로 Recovery와 Return/GoToCharger를 추가한다. 모든 출력·증거에 profile=mock와 simulated 행동을 명시한다. 모의 완료가 실제 파지/운반/기립 성공 증거에 합산되지 않게 한다.

## API와 시각화

py_trees와 py_trees_ros를 사용한다. WSL의 시스템 Python 조회에서 둘 다 미설치이며 apt 패키지도 미설치였다. 구현 시 apt 후보 버전과 설치 API를 먼저 확인하고 필요한 BT 패키지만 설치한다. 전역 pip3 install은 하지 않는다. ROS CLI는 시스템 Python, 시뮬레이터는 기존 venv라는 경계를 유지한다.

공식 API 문서는 버전별 차이가 있으므로 실제 설치된 BehaviourTree.setup/node 소유권·tick_tock/shutdown signature를 확인한다. 런타임 라이브러리와 Python 경로를 기록한다. https://py-trees-ros.readthedocs.io/en/release-2.4.x/modules.html 및 https://py-trees.readthedocs.io/en/release-2.6.x/modules.html 은 참고 자료이며 이 버전이 설치됐다는 증거가 아니다.

정적 DOT/PNG는 트리 구조 자료다. render_dot_tree 호출만으로 실행 중 상태가 자동 갱신된다고 설명하지 않는다. 실제 tick별 visited/status/active leaf·Blackboard 변경 요약을 JSONL과 텍스트로 기록하고 설치 버전의 ROS snapshot 기능을 연결한다. Graphviz 유무에 따라 DOT와 텍스트를 기본 출력으로 보장한다.

## 검증과 완료 조건

작은 부품 → 모의 반응성 → 필요한 실제 사례 순서다. engine 실행과 build/pytest/대량 분석은 병행하지 않는다.

1. 작은 시험: SUCCESS/FAILURE/RUNNING, memory 동작, 원본 관측 만료·세션 불일치 거절, goal 거절/abort·예외, 늦은 수락 후 취소, cancel ACK와 terminal 분리, 중복 tick의 goal 재전송 방지, abort/정상 terminal 뒤 재시작 방지.
2. 모의 실습: 정상 fetch·return, 이동 중 저전력→충전, fallen→recovery, 객체 없음과 실패 전파. tick 이력에서 실제 우선순위와 INVALID 중단을 검사한다.
3. 실제 정상 한 회: 같은 engine/session에서 BT가 시작한 Nav2 → 새 관측 → 기존 물리 pick. 실제 상승≥9cm, hold≥2sim초, 상대 변화≤2cm, HOLD 양 finger 접촉≥90% 등 기존 판정을 유지한다. 기존 verifier와 BT 순서/동일 session 검증을 결합한다.
4. 실제 중단 한 회: BT의 저전력/사용자 취소 주입으로 진행 중 소유 Nav goal을 중단한다. 주입 전 실제 운동, cancel 요청/ACK/terminal, 실제 정착, 후속 Pick 미시작, 정상 회수·잔여 없음을 확인한다. 실제 배터리 센서 검증으로 표현하지 않는다.
5. 파지 중 BT 취소 경계는 기존 held_cancel의 물리 결과·취소 계약과 부품 시험으로 우선 확인한다. 구현이 기존 파지 취소 경계를 바꾸면 새 held-cancel 실행을 추가한다. 단순히 과거 PASS를 새 13.7 실행으로 재표기하지 않는다.
6. 변경된 공통 hook에 해당하는 13.5/13.6 회귀만 추가한다. 전체 16개 matrix 반복은 기본 요구가 아니다. 같은 실패 계열이 두 최소 수정 후에도 남으면 구조를 검토한다.

새 13.7 freeze는 실제 필요한 기존6개+새 패키지·실행 도구·계약·설치 데이터(Ch13/config 포함)를 명시하고 자산94 hash를 재사용한다. 기존13.6 v14 freeze는 수정하지 않는다. source/install/model/정책 감사와 새 UUID 증거, 실패 기록·모델 제외 archive/manifest를 남긴다. 반복 강건성·실기·일반6D/YOLO·운반/WBC 검증으로 확대하지 않는다.

가이드는 다운로드→의존성→분리 build→각 터미널 환경→13.7.1~8 명령→BT 상태/Blackboard/실패·종료 판독을 포함한다. 학생 기본은 모의 반응성 + 실제 정상 mission이며 전체 unit/matrix는 개발자용이다. 설치·build·분석과 engine 실행 시간은 구분한다.

## 자체 검토와 다음 단계

검토 결과, 기존 pick 종료 후 이어 붙이기·accepted를 성공 처리·BT update에서 blocking 호출·low-battery Selector 오류·stale Blackboard 권한·취소 ACK만으로 정지 판정·모의 행동을 실제 검증으로 표시하는 경로를 설계에서 배제했다.

상세 설계 승인 후 superpowers:writing-plans로 단계별 실행 계획을 작성하고, 사용자 요청의 superpowers:executing-plans로 단일 작업자가 구현한다. 새 branch의 게시 지시는 최종 범위와 remote SHA를 확인하여 처리하며 기존 PR #115를 수정하거나 main에 직접 병합하지 않는다.
