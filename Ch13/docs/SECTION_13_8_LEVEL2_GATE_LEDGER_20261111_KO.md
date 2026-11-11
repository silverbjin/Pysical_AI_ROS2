# Level 2 완료 gate 진행 원장

사용자 지시에 따라 RED→GREEN→REFACTOR→REVIEW→COMMIT→공개CI→Owner 인수 순서다. Owner 인수는 사용자의 명시적 판단이며 에이전트가 대신 완료 처리하지 않는다. 단일 작업자로 수행한다.

## 관측 waypoint 보완

1. RED: 새 지점 계약 실패1/기존 footprint 통과1,3.87초.
2. GREEN: L2 waypoint(1.75,-.2,atan2(1.2,1.25)), 기존 target/world/최종평가/120wall survey deadline 유지. footprint·L2/L3 실제 RGB-D 포함4 PASS/4.31초. 앞서 세 후보의 static Renderer 원통 fit도 통과했다. 이는 보행 성공이 아니다.
3. REFACTOR: 지도 관측 목표 방향 계산을 _survey_pose로 모아 L3 기존좌표/방향을 보존했다. 전체 native snapshot460 PASS/71.43초,component_source_d143637cf34d4c5fbe1ab046bee7c008.
4. REVIEW: 자체 diff/범위 검토. 목표 위치·기하·동역학·관측수명·goal checker·deadline·단일owner/회수 변경 없음. waypoint는 저장 실제30sim 부근에 근거한다. 기존 L2는 도달 전 우회와 마지막 큰 방향전환으로 wall budget을 소진했으므로 새 실제 gate에서 더 이른 정착과 fresh find를 확인해야 한다. git diff --check 이상 없음. 독립 검토자는 사용하지 않았다.
5. COMMIT: 이 문서와 변경을 함께 기록한다.
6. 공개 CI: 저장소 public 확인, 기존workflow 없음. GitHub 공식 Python CI 문서(https://docs.github.com/en/actions/tutorials/build-and-test-code/python)의 setup-python/pytest 패턴을 채택했다. portable workflow는 Python3.12/pytest8.3.5/NumPy2.2.6/SciPy1.15.3/MuJoCo3.3.7에서 waypoint·filled footprint2건을 검사한다. 로컬 실제MuJoCo3.13.0·ROS/물리460회귀와 같은 시험이 아니다. 공개 Job 실행·step·head SHA·결론을 후속 기록한다.
7. Owner 인수: 새 source freeze/설치감사/단일engine Level2 실제 임무 결과를 인수 자료로 제공한 뒤 요청한다. 현재 미완료.

## 장애 계층 구분

호스티드 실행 실패는 runner_id/steps/log/artifact로 별도 판독하며 내부 GitHub 원인을 단정하지 않는다. Scan rosbag RX gap과 monotonic callback 지터를 혼동하지 않는다. read-only 관측의 지터만으로 안전정지를 완화하지 않는다. 현재13.8은 native ground-truth localization profile이며 별도 Supervisor/localization manager45초 정지의 선행 증거는 없다. 사용자 지침을 그 문제가 여기서 발생했다는 진단으로 바꾸지 않는다. 해당현상 발생 시 발견/manager callback/node lifecycle/응답전달을 나눠 측정한다. executor/임계값 조정은 하지 않았다.

## v38 실제 실패 후 v39 경로 구조 재검토

공개CI run42940490924/head96f0a462/job130260857460/runner1000005163은실제steps8개와success를확인했다. v38source391/assets94 SHA bcce909f80f0dc9c461f0b9dc3526452808dfb5a7be24a992b4090102fc7b8d6로actual858e39ed-05d5-408d-ad42-8e2d3c21a211을실행했으나survey deadline FAIL/12child clean/잔여[]/lockfree였다. 기존 ACTIVE/fault빈값 뒤wall만료로cancel됐으며Supervisor/Scan/lifecycle 문제로전용하지않는다. raw12,186,909bytes/SHA350a4f00ea7c75bd7027b1bcd50a556e370f0646ebaec23e3f3d9a4c39f44a03,sourcearchive69d98d4a861274d86955259b34c144844cf2ac06375229633f5287e8ee9ff13d.

같은deadline재발로지점거리가아닌경로접선과최종방향의관계를재검토했다. 실제v38경로에서첫60mm진입은기존후보(1.75,-.2)가34.48sim/방향오차.533517rad,이전후보(1.65,-.3)는27.22sim/방향오차.001825rad였다. 두후보의RGB-D static fit은이미통과했다. 따라서위치와방향을함께충족하는후보를선택한다. 안전기준/120wall/yaw.06/XY.06/최종점수/동역학변경없음.

RED: 새후보계약1FAIL/3.11초. GREEN: native full460PASS/65.91초,snapshotcomponent_source_ca69f342ea7a4c1f976aec9fc3bcefec. REFACTOR: 기존_survey_pose추상화에좌표만전달하므로추가구조변경불필요로판단했다. REVIEW: 자체diff2행과회귀/filled footprint/렌더검사를검토했고원본target/world와L3불변을확인했다. 독립review를수행했다고쓰지않는다. 다음COMMIT→새head공개CI→새동결실제인수검증순서다. 아직Level2완료가아니다.

## v39 실제 실패 후 v40 시간 기준 수정

v39 actual930cbd2f-2d68-49ff-8cb4-625eeee10884도survey deadline FAIL/12child clean/잔여[]/lockfree다. 실제31sim초 무렵XY60mm에진입했지만120wall초를소진했다. cmd/vision/TF의정상ACTIVE·fault빈값상태에서작업deadline이먼저발생했다. 후보변경만으로호스트의실시간비율을보장할수없음을확인했다. 새raw11,173,809bytes/SHAa9afa174e74da876105024e85bb68b592dea83a39689ca002079d94702a2adc2,sourcearchive dbf3508061a4430ddaf94d5642b5fbd482ce253363351c4d57a97e3fd4fbcd61.

Ruling: 기존LEVEL23_EVALUATION_SPEC의개별action120sim/240wall계약을survey작업에도명시적으로적용한다. v37/v38명세에서유지하기로했던survey120wall단일제한을이번원인분리결과에따라대체한다. 이전실패의판정은바꾸지않는다. task예산의wall상한이120→240으로증가하는실제변경이며이사실을숨기지않는다. 120sim또는240steady중먼저도달하면실패/소유goal회수다. 엔진·runner한도와300ms수명/100msTF/안전정지·지터임계값·executor는변경하지않는다. Scan수신gap을이변경의근거로사용하지않았다. 동일survey를사용하는L3도이명시적action예산을사용하므로이단계의영향범위에포함한다.

근거: 공식ROS2 Clock and Time(https://design.ros2.org/articles/clock_and_time.html)은simulation/steady의진행속도와용도를구분한다. 예제존재를이로봇의성공증거로표현하지않는다. RED6FAIL/3.65초→관련GREEN28PASS/7.92초→REFACTOR(단일snapshot으로stop검사·예산시작event)→full466PASS/74.69초(snapshot3663295ec17a43abb75c6745197fc946). REVIEW에서정지sim의wall상한·clock역행거부·기존cancel/FAULT우선검사·finallydrain보존을확인했다. 미초기화/역행시간은예산연장의권한이아니다. 공개CI에이중예산6시험을추가한다. 다음COMMIT→공개CI→실제인수순서다.

## v40 기록 코드 실패·v41 회귀 경계 보완

actualc2939327-10d9-48c3-874a-430e17c3d54e는survey_budget_started의wall키가TaskPort.event의예약wall키와중복돼TypeError로중단됐다. 시간예산정책의실제성공/실패로집계하지않는다. 원본FAIL·12childclean/잔여[]/lockfree와source393/archive를보존했다. raw3,198,416bytes/SHA7415eee23dc06843b84875233e933a780221059ea4fda895e0c91597080f5d13. 에이전트가추가한기록결함이며기존물리·관측문제와구분한다.

RED: 실제TaskPort에동일wall전달TypeError를재현(1FAIL/2.74초),budget.record_start의budget_start_wall로분리했다. REFACTOR: 기록경계를작은메서드로모았다. 최초full은1FAIL/466PASS/76.63초였고기존wire시험기동중FUTURE_SOURCE:base였다. DDS발견과첫clock수신을동일시하던fixture의경계를분리했다. 결정적fixture RED1FAIL/3.19초→clock실제수신을기다린후상태발행으로수정. productiongateway·freshness·native C++는변경없다. 최종GREEN468PASS/85.90초(snapshot36c34308c6384cedbbf8b690dc10f6a7). REVIEW: 예약키분리·single-owner/cancel·negative clock/future/loss회귀유지확인. 기존CRLF/-text파일은CR-at-eol설정으로diff공백검사해통과했고원본바이트를줄바꿈만으로바꾸지않았다. 공개CI에실제TaskPort통합회귀도포함한다. 다음COMMIT→공개CI→새v41실제인수다.

## v41 실제 진행과 v42 최소 연결 보완

v41 기본 사례586327fb-5fd7-4280-bf0a-d3091fbceec1은survey를통과하고최종접근중VISION_EXPIRED로정지했다. capture36198000000의원래capture_wall7165.174774162에서state_publish161.774ms뒤offer,render_finished7165.359759529,healthvalidation7165.372463585,nativehealthreceipt7165.488845813,decision7165.489614044다. 원본촬영→native수신약314ms다. Scan RX gap이나Supervisorcallback으로해석하지않으며300ms/TF100ms와안전fault를유지한다.

동일v41소스의기존CH13_CAPTURE_OVERLAP=1단일진단5576989e-4e60-4556-bfe5-687a1419c48e는survey/최종접근/find와ramp실제접촉251.49N을확인한뒤normal warmup의20wall결과대기가먼저끝났다. 실제arm은59.888sim/7652.222wall시작,20.047wall뒤cancel ACK,약7.774wall뒤실제CANCELED였다.4sim경로가끝나기전에client가취소했다. DeferredClients5wall회수도미확정이므로정상action회수라하지않는다. engine은최종SIGINT로중단됐고11/12clean·최종OS잔여[]/lockfree다. 두사례독립FAIL/source/archive/config를보존했다. overlap1은명시적실험설정이며기본강건성증거가아니다.

v42 RED실제warmup호출자1FAIL/12.99초→GREEN1PASS/2.40초. carry_v1정상준비동작만기존server240wall상한내에서실제result를기다린다. legacy와cancel/loss20wall은유지한다. 원래4sim경로·PD/속도·접촉·실제terminal판정은유지했다. REFACTOR는arm/gripper대기예산공유와기록,legacy경계추가다. full470PASS/77.78초,snapshotf8f9f9aee21a496a8fee06306c966aae. REVIEW에서결과대기연결만변경함을확인했다. 준비시험삭제·새제어기·executor변경은없다. 다음COMMIT→공개CI→v42실제Level2이며명시적overlap1진단설정을기록한다.

## v42 준비 동작 통과·v43 기존 관측 처리율 연결

v42 actual d8d65f1a-a736-46ea-863b-bfe28ce45fd9는준비팔/양gripper정상terminal과PRE_GRASP계획까지진행했다. arm은62.536sim/3233.911wall시작→3255.627wall정상terminal로20wall을넘었지만기존경로/판정그대로성공했다. 이후arm실행거부의최초원인은OBSERVATION_EXPIRED다. 첫FAULT69968000000/3268.335954087에서원본capture69962000000/capture_wall3268.034249846의age301.704ms였다. 다음관측69964000000은3268.333010138에추론을마쳤다. 최종status에남은오래된관측을2.6초backlog라고오독하지않고최초fault event로원인을분리했다. 실제관측기수신은계속됐고기존faultlatch를해제하지않았다. 12child정상회수/잔여[]/lockfree. raw21,735,621bytes/SHA64d8cdadf7f7feb49ae620879aa6f6143e54856d5fe55d221832f07dfb5723f7.

도서범위최소보완으로새executor나인식기를만들지않고기존run_navigation_probe의지원값10/15Hz를기존session→worker에전달한다. Level2만10Hz를선택하고다른Level·13.7기본은15Hz유지,300ms/TF100ms·health·접촉기준은유지한다. 처리부하감소가실제상한을보장한다고주장하지않으며새실제gate로확인한다. scenario.record에실제선택처리율을남겨조건을숨기지않는다. CH13_CAPTURE_OVERLAP=1은계속명시적기존실험설정이다.

RED9FAIL/3.72초→GREEN9PASS/2.69초→REFACTOR기존worker인자구성함수로한정→full478PASS/71.49초(snapshot5822bf69b28247e79b75e66d7112d762). REVIEW: 지원값외거부·legacy15보존·동일owner/명령·시간/안전기준불변·인자전달경계를확인했다. 공개CI기존portable시험도새Level2처리율선택을검사한다. 다음COMMIT→공개CI→v43실제인수다. 전체성공/Owner인수는아직미완료이며물리기준이나도서목표를낮춰완료처리하지않는다.

## v43 위치 terminal 불일치·v44 기존 검사 정책 보완

v43 actualcba70217-f682-405b-9c92-e6cba4a46b50는실제10Hz로동작했고survey뒤최종Nav2성공terminal을받았으나실측위치106.107mm/방향.028453rad로기존probe100mm검사를통과하지못했다. 이번사례의최초실패는관측만료가아니다. 12child정상회수/잔여[]/lockfree,원본FAIL/source/archive보존. raw20,544,336bytes/SHAedbb9bedf95297abd5a237c698ffc7ba143a035e913fcdbd6e9ad2489a2c9a30.

공식Nav21.3.13 regulated_pure_pursuit_controller.cpp의shouldRotateToGoalHeading은stateful true에서XY최초통과를latch하고false에서는매번거리를다시검사한다. 공식원본을GitHub connector로읽고설치libnav2_regulated_pure_pursuit_controller.so의stateful지원도확인했다. URL: https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_regulated_pure_pursuit_controller/src/regulated_pure_pursuit_controller.cpp . 이기존설정패턴을사용하며새제어기·executor를추가하지않는다.

Level2기본NavFn/RPP에만goal_checker.stateful=false와FollowPath.stateful=false를적용한다. 기존실험SE2설정과독립시키고다른Level기본/XY.015/yaw.06/최종3cm기준을유지한다. RED실제ROSparser1FAIL/1PASS/4.72초→GREEN9PASS/3.69초→REFACTOR설정경계주석정리→full478PASS/79.76초. REVIEW에서플러그인·속도·충돌·기준불변과legacy보존을확인했다. 다음COMMIT→공개CI→단일v44실제인수다. 이보완도실제성공증거가아니다.

## v44 실제 gate와 도서용 Owner 검토

기본v44 b949c443-0529-415c-98cb-125d0eafb3ca는survey후최종접근240wall deadline FAIL(88.970sim/394.671wall)이다. 별도read-only노드로실제goal_checker/RPP statefulfalse와XY.015/.06을읽었다. 저장표본에서위치·방향동시통과0건이며12child정상회수·잔여[]/lockfree다. raw27,737,255bytes/SHA84d4b4d35afefe5912b6ec2efcf113d8b3bda1131a091adc0f33e756731749de.

같은v44소스의기존SE2실험설정단일대조3593fe57-b619-4ea7-a7bf-05374efb2651은survey중Failed to make progress/ABORT였다. 설정을기본채택하지않고FAIL/12child정상회수/잔여[]/lockfree를보존한다. raw9,302,728bytes/SHA841ab7e73404a1f7ce849eedb6446d647aca5b0c634cca99082d43b11aac0530. 새코드나제어기를추가한실행이아니며조건은execution_profile.json에기록했다.

도서용최소범위라는최신사용자지시에따라새제어기·WBC·executor개편을추가하지않는다. 정상완주gate는미충족이며Owner승인을대신하지않는다. 검토문서 SECTION_13_8_LEVEL2_OWNER_REVIEW_20261111_KO.md에부분별실제증거와미완료범위·결정사항을정리했다.

최종무실행점검PASS(boot4375c65d-8c7c-40ce-8daa-62dbf2f327f8). 디스크정책에따라11개닫힌사례의비추적대형중복86파일/764,073,110bytes를삭제했다. 각raw.tar.gz전체SHA와삭제파일의압축내부/로컬SHA를대조하고판정·manifest·sourcearchive·설정·raw압축본은보존했다. 원래manifest의raw_originals표현은생성당시기록이며현재상태는retention_level2_duplicates_20261111.json이갱신한다. 원본의완전한바이트는raw압축본에서복원한다.

## v45 Owner 결정·전진 경로 계획 분리

Owner는 정상 완주 기준 유지·인수 보류를 확정했다. 명세6efc71d1의 순서로 진행한다. 저장 v44 실제 survey 위치와 설치 Nav2 1.3.13 planner를 사용한 비교에서 최종 경로 진행 방향 오차는 NavFn .784540rad/DUBIN .122715rad였고, 보수적 filled footprint 위반은 두 경로 모두0이다. 초기→survey도 유효했다. 진단 planner exit0, lifecycle 정리 완료다. 새 실제 이동 성공을 뜻하지 않는다.

RED 실제 ROS parser: 1FAIL/1PASS/4.06초(기존 NavFn이 DUBIN 기대와 불일치). GREEN 관련 설정18PASS/4.33초. REFACTOR: planner-only YAML과 적용 조건만 추가하고 다른 구조 변경은 하지 않았다. 전체478PASS/67.94초, native snapshot e602230aea684a62899f7ff58680a6c7. REVIEW는 단일 작업자 자체 검토로, 실제 parser가 전진 RPP/역주행 금지/XY.015/yaw.06/stateful false/속도 상한 유지 및 Level3 기본·기존 SE2 opt-in 불변을 확인했다. package.xml에 이미 nav2_smac_planner 의존성이 있고 setup config glob에 새 YAML이 포함된다. 공식 1.3.13 구현의 DUBIN 기본 패턴과 대조했다.

이 변경은 가설의 최소 실험이다. 경로 계획 개선만으로 로봇의 도달·파지·운반·놓기 성공을 주장하지 않는다. 다음은 COMMIT→공개 CI 실제 runner/steps 확인→v45 분리 build/audit/freeze→단일 실제 실행이다. 기존0/10 평가와 과거 실패는 보존한다.

## v45 실제 결과 — 이동 통과, 관측 만료 반복

코드d2be10ae 공개 CI run42976398827/job130376388217/runner1000005679에서 모든 step success를 확인했다. 별도 build/audit71 및 실제 venv child 의존성 확인, source396/assets94 동결 SHA f212f439b4eb09f717fc228ae1ee80c131c71ca3e141d732632515d4d94c7721과 전체시험 snapshot/runtime 바이트 일치 PASS다.

UUID aebe4a05-2e76-4999-b46a-29a4d588928b는 실제 Smac DUBIN 선택을 launch 로그로 확인했고 survey→최종 navigate→find를 연속 통과했다. 최종 위치 오차14.847mm, 실제 ramp 접촉212.465N. 이후 팔 준비 중 OBSERVATION_EXPIRED로 FAIL(57.758sim/204.961wall초). engine COMPLETED/launch exit0, runner FAILURE, worker join/port closed/rosbag close와 잔여[]/공유lockfree를 구분한다. raw17,958,417bytes/SHA585862dc879c2d84353e515d8a3f127c9d0c83d50ea736777319dd8977b71a13, 정확한 source_v45 보존 PASS.

최초 fault decision7403.213691897의 사용 관측 capture58618000000/capture_wall7402.873216175로 실제 나이는340.476ms다. 다음 capture58622000000은7403.013220668에 촬영, 모든 원본·receipt 조합은 약7403.081에 도착했으나 10Hz cap 때문에 추론 시작7403.13308646, 종료7403.179966016이었다. 직전 관측의300ms 만료7403.173216175 이후다. 이 수치는 camera/추론/engine 수신 경계의 합성 지연을 보여 주며 rosbag RX gap이나 단일 callback 지연 하나로 단정하지 않는다. v42의301.704ms 실패와 같은 관측 만료 계열이 반복됐다. 15Hz도 과거 실패가 있으므로 단순 rate 재변경만으로 해결됐다고 하지 않는다.

다음은 기존 단일 executor를 유지한 채 monitor/관측 수신 callback의 내부 소요 시간을 계측하여 graph query·lock·DDS 전달 중 어느 경계가 추가 지연을 만드는지 분리하는 최소 진단이다. executor 재구성·수명/임계값 변경은 하지 않는다. Level2 정상 완주와 Owner 인수는 계속 보류다.

## v46 제한 계측 RED→GREEN→REFACTOR→REVIEW

명세5ca3c19e. 공식 Jazzy rclpy executors.py 원본을 확인하고 단일 executor/원래 callback을 보존하는 opt-in 계측만 추가했다. RED는 계측 모듈 부재로 수집 실패(3.56초). GREEN 관련5PASS/2.53초 후 실제 monitor 상태·소유권 검사 보존 시험을 더했다. REFACTOR에서 module docstring/미사용 import만 정리했다. callback의 반환·예외를 그대로 전달하며 꺼짐에서는 시계를 읽지 않는다. 기록은 최대4096건이고 원본 stamp/receipt나 수명을 갱신하지 않는다.

첫 full은480PASS/1FAIL(65.77초)였다. 실패는 test_platform_wire의 연결 준비 중 OLD_SOURCE:safe로, 첫 safe sample 전에 모의 시계가 진행한 시험 fixture 문제다. 기존 ROS wire fixture의 발견 대기 패턴을 참고했다. 고정 재현 RED1FAIL/3.23초(2.04s가2s 기대와 불일치) 후 첫 safe sample 수신까지 모의 시계를 유지하도록 수정했다. 이후 관련10PASS/1FAIL(34.33초)의 별도 실패는 초기 callback이3초 준비 시간 안에 실행되지 않은 경우이며, 앞의 시각 불일치 해결과 같은 원인이라고 단정하지 않는다. engine 없이 별도 작은 플랫폼 시험5PASS/4.28초를 확인했다. 모든 실패 출력은 prep에 보존하며 마지막 전체 재검증만 성공으로 보고한다.

최종 full482PASS/68.73초, snapshot aa628fc6c93742fe82efce53d880fa9b. 자체 REVIEW: opt-in 기본 꺼짐, 기존 executor/lock/graph 조회 횟수/제어/수명/회수 판정 불변, 실제 monitor 상태 발행 보존 확인. 독립 검토가 아니다. 공개 portable CI에는 계측 반환·예외/상한/꺼짐 계약2건을 추가해 총11건을 실행한다. 다음 COMMIT→공개CI 실제 Job 확인→동일 조건의 단일 계측 사례다. 현재 Level2 정상 완주/인수 보류 상태는 바뀌지 않는다.

## v46 실제 계측과 한계

공개 CI run42979408371/job130386009089/runner1000005720 모든 step success. 전체482PASS와 설치감사72, source398/assets94 동결 SHA971ba2f72643070a08b0bbd9885af690134eabbef69e554d038166908857589e/runtime 전수 일치 PASS.

첫 UUID9d5a5092-4987-480b-9f03-35a8821bdc90는 시작 survey 준비에서 gateway OLD_SOURCE:raw로 중단했다. 목표한 관측/파지 경계에 도달하지 못했고 engine monitor 최대10.456ms는 이 시작 실패의 원인 입증이 아니다. trial2.28sim/7.754wall, engine COMPLETED/launch0, 잔여[]/lockfree. raw3,422,730bytes/SHAcc6c47f7b3de3c08621b6c76460e3b488905433736f2568d90bc40b2fdbc7725.

목표 미도달에 한정해 동일 소스/10Hz/overlap1/SE2=0/계측1을 새 UUID09fda61e-5f05-4719-8f9b-9241409e74eb로 한 번 반복했다. survey 이후 최종 접근 중 VISION_EXPIRED, trial83.98sim/318.143wall FAIL. 최초 decision9113.515155677에서 capture_wall9113.196844728의 나이318.311ms였다. 마지막 상태의343.467ms를 최초 fault 나이로 쓰지 않는다. fault 직전1초의 platform monitor 최대26.222ms/manipulation monitor25.658ms/action monitor15.680ms였으며, 엔진 callback 지연 하나로 관측 만료 전체를 설명할 수 없다. 이 계측은 다른 프로세스인 vision callback의 대기 시간을 직접 측정하지 않았다.

renderer는 그 사이85440/85444/85450ms 촬영 자료를 실제 발행했으나 camera receipt 결합 기록은 세 프레임 모두 누락됐고 다음 건강 관측은85458ms에서 재개했다. 발행·native 수신·메타데이터 결합·inference·health 전달 중 원인을 추가 분리해야 하며 메시지 손실이나 executor 단독 원인으로 단정하지 않는다. controller/route의 정상 재현도 아직 미확인이다. 종료 시 engine ERROR/KeyboardInterrupt, clean child11/12였고 OS 잔여[]/lockfree다. 이 종료를 정상12child 회수로 표시하지 않는다. raw24,834,342bytes/SHA5dade22c5548197db3192881b85d1916bdc9e0f7457a6043ef47116e75030913, 두 사례 source_v46 보존 PASS.

v45 닫힌 사례의 해시 일치 대형 중복12파일83,756,349bytes를 정리했다. 원장retention_v45_duplicates_20261111.json, raw/archive/판정/소스는 유지한다. 기존 v28의0/10이나 Owner 인수 보류는 바뀌지 않는다. 다음에는 저장 자세의 별도 domain136 카메라 재현으로 vision callback을 조사하며 추가 전체 engine 재시도는 먼저 하지 않는다.

## v47 카메라 부품 대조·초기화 경계 보완

v46 저장 자세82~86sim초를 별도domain136에서 재현했다. physics/policy/action/lease를 실행하지 않았다. 최초 probe는 상대 root 경로 해석 오류로 모델 로드 전에 실패했고 ROS 자식은 시작하지 않았다. FAILED.json을 보존하고 resolve()로 도구 경계만 고친 새 출력으로 진행했다. 첫 tick347.445ms를 측정한 뒤 import 자체를 계측한 lazy 대조에서는 cylinder_vision import410.233ms/같은 tick413.631ms, health validation 최대간격421.734ms였다. preload 대조는 초기화232.883ms를 수신 전에 수행하고 tick 최대4.719ms/health 최대간격135.819ms였다. 각 프로세스 내부 monotonic 차이만 비교했다. 자세상 대상이 보이지 않아 기존 probe의 accepted>50 판정은 둘 다FAIL이며 성공으로 고쳐 쓰지 않았다. 이 결과는 시작 지연 원인의 부분 입증이며 장시간 v45/v46 만료 해결 증거가 아니다.

명세633f36fd. RED는 실제 ROS fixture 첫 frame의 cylinder import를 차단해1FAIL/30.41초. GREEN5PASS/2.92초에서 기존 capture/hash/TF 건강 판정과 원본 시각 보존을 확인했다. Ruling: 남은 경계가 다른 프로세스인 vision이라 기존 opt-in callback 계측을 그 노드에도 연결한다. 단일 executor와 수신 순서는 유지하며, 기본 꺼짐/4096건 상한이다. 이 경계 추가가 없으면 다음 실제 사례에서도 frame 결합 누락이 callback 내부 지연인지 분리할 수 없다. 새 callback 계측 계약 RED1FAIL/2.85초→GREEN6PASS/6.46초. REFACTOR는 stdlib 초기화 위치와 진단 dict 가독성만 정리했다.

최종484PASS/77.10초, snapshot d5fdc2e26c6a49a8b52f7f2134580178. 자체 REVIEW에서 기존 fit 함수를 그대로 준비/호출하고 fixture 기본/단일 owner/정책/제어/수명300ms/TF100ms/원본 시각·GID·hash·충돌·종료 기준을 보존한 것을 확인했다. module이 없으면 callback 전 초기화에서 실패한다. 별도 모델·인식기를 추가하지 않았다. 대조 요약·실패·개발용 재현 script/hash는 v47_camera_import_diagnosis에 보존했다. 다음 COMMIT→공개 CI→source freeze/build/audit→필요한 실제 사례다. 정상 완주와 Owner 인수는 계속 보류다.

## v47 실제 검증 — 초기화와 장시간 생산 지연 분리

35de775e 공개 CI run43016918196/job130510180983/runner1000005995 모든 step success. 별도 설치감사72/source398/assets94 동결 SHA7ae82c54d282c17912f3c6e5fdd73dec33c3121697227468c13538747cc283d1과 native484PASS snapshot/runtime 바이트 일치. 새 boot e68f5c48-8b58-435c-a1c3-03c4c0ecfb95에서 무실행/lockfree를 다시 확인했다.

실제 a581a30c-3a1a-45da-9392-709c21df9044는 survey 이후 VISION_EXPIRED로 FAIL(40.628sim/139.293wall). 최초 decision7792.104163454/원본 capture7791.789161775로315.002ms였고, 마지막 상태의395.342ms와 구분한다. 해당 구간 vision.tick 최대17.083ms, 마지막4096 callback 중 최대17.889ms로 초기 import 지연이 재발한 기록은 아니다. 최신 native health receipt는 fault 이후 다른 메시지일 수 있으므로 frozen sample과 같은 메시지의 지연으로 묶지 않는다.

다음 frame은7791.959185867에 촬영됐으나 Scan42.013ms를 마친7792.00122518에 renderer로 제출됐다. render 종료7792.04467845/publish 완료7792.088460057/health validation7792.106197675로 직전300ms 만료보다17.036ms 늦었다. 직전 state publish88.070ms와 촬영 간격170.024ms도 함께 기록됐다. 단일 callback/rosbag RX만의 문제로 단정하지 않고 생산→render→검증 누적 지연으로 분리한다.

engine COMPLETED/normal shutdown true,12child 정상 회수·worker/port/rosbag 완료·잔여[]/lockfree다. raw13,528,247bytes/SHAbaa1567a543cdfb736aacf7849d79879e49f2a2edf0a5e1f589c8f0bda3fbd26/source_v47 정확 바이트 보존 PASS. 정상 완주/Owner 인수는 계속 보류. 다음 명세7f569e52는 기존 overlap1 요청을 Scan 앞에 보내는 최소 순서 보완이며 임계값이나 executor 변경이 아니다.

## v48 촬영 요청 순서 보완 RED→GREEN→REFACTOR→REVIEW

명세7f569e52는 촬영 시각 치환 없이 기존 opt-in overlap1의 불변 snapshot 요청만 Scan보다 앞에 보낸다. 설치 MuJoCo3.13.0 공식 doc/python.rst의 내부 배열 직접 참조/필요 시 copy 패턴을 확인했고 기존 CameraWorker 계약을 그대로 쓴다. 기본 overlap0에서는 기존 Scan→state→요청 순서를 유지한다. Scan 비용을 요청 이전 전체 시간과 별도로 재는 측정 경계도 정리했다.

RED1FAIL/4.05초에서42ms Scan 뒤 제출하던 기존 순서가 재현됐다. GREEN9PASS/3.20초에서 원본 qpos copy/stamp/wall/Scan 주기와 기본 경로 불변을 확인했다. REFACTOR는 state publish 중복 분기만 합치고 추가 동작은 넣지 않았다. 전체485PASS/82.10초, native snapshot31150757de4b4461a0c170bca51b8fdb. 자체 REVIEW에서 같은 engine snapshot을 복사해 기존 worker에 일찍 전달하며 물리 상태/clock/관측 수명/TF/정책/PD/속도/성공/종료 기준을 변경하지 않은 것을 확인했다. 중복 state publish 제거 같은 별도 변경은 하지 않았다.

닫힌 v46/v47 사례의 대형 중복은 raw 전체 및 멤버/로컬 SHA를 검증한 뒤 retention_v46_v47_duplicates_20261111.json에 따라 정리했다. 원본 archive·판정·정확한 source·필수 진단은 유지한다. 다음 COMMIT→공개CI→v48 별도 freeze/build/audit→동일 조건의 단일 실제 검증이다. Level2 정상 완주와 Owner 인수는 보류이며 기존0/10을 대체하지 않는다.

## v48 실제 검증 — 촬영 선제 제출 확인, 추론 대기 만료

코드25a5688c/문서ecf9c255 공개 CI run43019268300/job130518062927/runner1000006005의 모든 step 성공을 확인했다. 설치감사72/source398/assets94 동결SHA9b3468c7ba9c1872988b5e95df8eecfd43dbd45fdadd02bbf6087e4d7833537e/native485PASS snapshot/runtime 전수 일치.

UUID4f4d4ce4-0d83-40f8-a0e2-4584b6e3097b는 최종 navigate11.311mm/정착/find/팔 준비를 통과한 뒤 PRE_GRASP 중 OBSERVATION_EXPIRED로 FAIL(66.192sim/220.521wall). engine COMPLETED/normal true/12child 정상 회수·worker/port/rosbag 완료·잔여[]/lockfree. raw20,037,484bytes/SHA7692bce9bc801b2a21821a396eb544b795eb02f21c634b83d15d7b0fc71697ff/source_v48 보존 PASS.

해당 구간 pre_offer는 약0.004~0.012ms로 Scan 이전 요청이 실제 적용됐다. 최초 fault8757.348507426에 사용한 원본 capture8757.046126638은302.381ms였다. 다음 capture8757.229389063의 네 native/metadata는8757.273662까지 도착했지만 inference 시작8757.329831725/종료8757.354383926으로 직전300ms 만료8757.346126638를 넘겼다. 10Hz cap이 앞선 inference8757.212981876 이후100ms를 기다리는 구간이 있다. 원래15Hz 지원값의67ms 간격을 이용하는 저장 deadline 재현을 다음 단계로 좁혔다. 과거15Hz 실패와 이번 개선된 생산 경계를 섞지 않으며 전체 성공으로 선언하지 않는다.

PRE_GRASP 첫 후보의 execution duration67.234sim초도 기록했다. 전체120sim초 목표에 부담이 되는 별도 항목이며 아직 실행 완료하지 않았다. 이번 관측 처리율 작업과 함께 팔 속도나 물리/경로를 바꾸지 않는다. 정상 완주·정식10회 재평가·Owner 인수는 계속 미완료다.

## v49 원본 처리율 복원 RED→GREEN→REFACTOR→REVIEW

명세ea4a054b. v48 저장 native/metadata 완료 시각과 실제 관측 소요24.552ms를 사용한 실제 VisionObserver fixture가10Hz에서 새 frame 처리0건으로 RED1FAIL/4.37초였다. 지원15Hz로 복원하면 같은 원본 frame을 옛 관측300ms 만료 전에 처리하고 기존 Lease의 freshness 검사를 통과한다. 원본 capture/TF/first receipt/GID/hash를 바꾸지 않는 시험이다. 과거v42의15Hz 실패를 삭제하거나 이 부품 시험을 실제 성공으로 표시하지 않는다.

Ruling: 검토 중 Scenario.record의 Level2 기본 navigation_profile이 v45 이후에도 baseline_navfn으로 기록되는 메타데이터 오류를 발견했다. 실제 launch는 DUBIN이며 launch 로그와 execution_profile로 확인했다. 과거 JSON/hash는 수정하지 않고 이 원장으로 해석 한계를 남긴다. 새 기록을 baseline_forward_dubin으로 바로잡는 계약 RED1FAIL/3PASS/4.30초→관련 전체7PASS/4.48초였다. 기록의 정정은 planner/geometry/권한을 바꾸지 않는다. 기존 portable 시험도15Hz와 새 기록 이름을 확인하도록 보완했다.

GREEN 후 REFACTOR에서 별도 추상화나 추가 속도/경로/모델 변경 없이 Level2의10Hz 특례만 제거했다. 전체487PASS/72.43초, snapshot43f69030ee5a4b0ab9930fca5ec7b685. 자체 REVIEW에서 native CLI가 이미 지원하는15Hz를 사용하고 다른Level/원본stamp·300ms·TF100ms·단일 owner·제어·접촉·종료 기준을 유지하는 것을 확인했다. 다음 COMMIT→공개CI→새 freeze/build/audit→15Hz 실제 사례다. 성공과 CPU/시간 목표는 아직 검증 전이다.

## v49 실제 검증 — safe 입력 receipt 만료, 관측과 구분

0a9ee86b 공개 CI run43022260798/job130528087652/runner1000006006 모든 step 성공, native487PASS/source398/assets94 동결SHAb79bbc48f7a93d32001abf823b7fa11c5df0ed299cad716804f9449047c2d572/설치감사72/실행 원본 일치 PASS. 실제 UUID0e7456d4-adcd-4ffc-873b-4ab4a054afa4는 survey 이후 INPUT_OR_CLOCK_TIMEOUT의sample_wall_expired:safe로 FAIL(38.246sim/119.298wall)했다. 최초 decision9794.111659792/원본 safe receipt9793.810324414로301.335ms. 당시 저장 navigation 상태는ACTIVE/vision age166.520ms로 관측 만료가 아니다. Nav action CANCELED5를 정상 SUCCEEDED4로 바꾸지 않는다. engine COMPLETED 및 source_v49 보존/원본 raw12,651,416bytes SHA9a4a84d86af64ea30d5f072fec24d5773810ff689e6759952aa0cee19adf6a51을 보존했다.

직전 sim39.706/.708/.710의capture_sensor100.954/108.620/172.863ms와 Scan124.571ms가 확인됐다. 별도 단일-thread executor membership 비교는 효과가 일관되지 않아 기각했다. 공식 MuJoCo3.13.0 batch ray와 알려진 이슈를 조사했고 저장 자세30개/5430 rays는scalar와0m오차로 일치했다. JSON thread 경합에서 batch5.505~10.880ms/scalar36.985~64.321ms였다. 이 부분 측정만으로 전체 안전 정지 원인을 해결했다고 하지 않는다. 다음은 eligibility guard와 scalar fallback을 갖춘 최소 batch 경계의 RED→GREEN 및 기존 안전 회귀다.

## v50 batch Scan RED→GREEN→REFACTOR→REVIEW

명세2d389790. 공식3.13.0 MultiRayEqualsSingleRay 테스트와 engine_ray 구현, 이슈3731/3736을 먼저 확인했다. RED3FAIL/7PASS/17.32초에서 지원 모델의 batch 호출이 없던 경계를 재현했다. GREEN13PASS/17.87초로 동일181 거리/회전 centred primitive/qpos 불변/near·4m 필터/offset 위험 모델 scalar fallback/다른 profile scalar 보존/원본 sensor 모델을 확인했다. 실제 Level2 모델의world0 및 inertial 원점[0,0,0] centred cylinder body26도 batch 적격이다. REFACTOR에서 모델 eligibility와 기존 scalar fallback을 분리하고 sensor summary에 backend를 기록했다. 새 executor/thread/권한/안전 수치를 바꾸지 않았다.

첫 full496PASS/1FAIL/208.96초의 실패는 test_launch_lifecycle의6초 기한이 실제 플랫폼의 SciPy import 중 끝난 시작 fixture 문제였다. 물리 모델이나 engine은 시작하지 않았다. Ruling: 기존35초 bootstrap 한도와 실패 report 이후6초 shutdown gate를 분리한다. 공식 Jazzy OnProcessExit는 프로세스 종료 뒤의 handler이므로 cold import를 종료 처리 시간에 포함하지 않는다.7초 cold bootstrap을 시험에만 주입한 RED1FAIL/17.16초→GREEN1PASS/20.94초로 경계 구분과 실제 owned children 회수를 검증했다.20.94초는 준비를 포함한 총 시험 시간이고 shutdown gate는6초 그대로다. 실제 runtime timeout이나 안전 기준을 늘린 것이 아니다.

최종 전체497PASS/158.14초, native snapshoted8397ab1a1646019dee0da1a3d809fc. 자체 REVIEW에서 기존 mass/actuator/robot policy/Scan stamp·원점·group/static 필터·범위·단일 owner·cancel/종료 계약 불변과 known offset bug 회피를 확인했다. 복사한 개발자 ray probe는 소스 변경 후 비교가 순환하지 않도록 재현판의 scalar 기준을 직접 고정하고 원실행판도 보존했다. 공개 CI의 portable11건과 native497건을 구분한다. 다음 COMMIT→공개CI→source freeze/build/audit→단일 실제 사례다. Level2 정상 완주와 Owner 인수는 보류다.

재현판 probe를 현재 source에서 다시 실행해30자세/5,430 rays의0m오차를 확인했다. 새 경합 측정은 scalar1.557~82.977ms/batch6.724~18.097ms로, 일부 scalar 최단치는 batch보다 빨랐다. 따라서 일률적 가속이나 모든 실행의 지연 상한을 보증하지 않는다. 두 비교 결과를 모두 보존하며 실제 안전 수신 개선 여부는 다음 live case에서 판정한다.

## 2026-11-12 재개 — v50 실제 결과와 v51 제한 명세

v50 실제 UUID990fa443-b46e-4790-9dce-a2f9515a8dec의 입력/관측 수명 초과는 없었으나 최종 이동240wall초 기한으로 FAIL했다. trial73.93sim/450.356wall/CPU55.214%, engine COMPLETED/normal true/12child 정상 회수/잔여[]/lockfree. 최소XY2.085mm에서yaw.355077rad, 최소yaw.088746rad에서XY25.633mm로 저장 표본 공동 목표 통과0건이다. 마지막256 생산 기록의Scan37건 최대18.365ms이며 전구간 상한은 아니다. v50 freeze399/assets94 및 정확한 실행 source/raw/archive를 보존했다. 공개 CI43040197736 실제runner1000006007/모든step 성공과497 native PASS는 별도 증거다. 전체 정상 완주/정식10회 재평가/Owner 인수는 여전히 미완료다.

명세34676130은 기존Nav2 1.3.13 RPP의fixed curvature+끝점 보간만 Level2 기본 경로에서 조사한다. 설치 라이브러리 getLookAheadPoint의 저장 자세9개 재구성 비교는 기하 동작 확인이며 정확한 timestamp 연결된 제어 replay가 아니다. 최초 개발 도구는 자유 함수를 멤버로 오해해 build 실패했고 로그를 보존한 뒤 수정했다. 실습 소스에는 영향이 없었다. smoother scale_velocities는 절대 각속도 포화의 직접 해법이 아니라 기각했다. 수명300ms/TF100ms/목표오차/속도/정책/단일owner/종료 기준을 변경하지 않는다.

RED1FAIL/4PASS/4.39초로 실제 ROS launch 파라미터의 보간 미적용을 확인했다. Level2 기본 경로에만use_fixed_curvature_lookahead=true/curvature_lookahead_dist=.25/interpolate_curvature_after_goal=true overlay를 더해 관련7PASS/2.90초였다. .25m는 기존 최소lookahead를 재사용한다. 일반lookahead.45/목표회전/충돌검사/stateful false/전진만 허용은 유지한다. REFACTOR 검토 결과 추가 추상화 없이 기존 overlay 구조가 충분해 별도 구현 확장은 하지 않는다. 다른Level/실험SE2 경로 비적용을 실제 ROS parser로 확인했다. 전체 회귀와 COMMIT/공개 CI/새 실제 사례는 각각 별도 기록한다.

v51 최종 전체502PASS/73.97초, native snapshot9ef9668ee0dc44b8a7cafb57d7ab1f7c. 단일 작업자 자체 REVIEW에서 원래 RPP/충돌검사·일반 목표carrot·지속XY검사·최종 수치와 caps/다른Level·실험SE2 경로 불변을 확인했다. 별도 독립 검토자 검증은 아니다. 공식 path_handler의 마지막 두 점 보존과 단일점 거절 조건을 확인했으며 라이브러리를 패치하지 않았다. 부품 PASS를 물리 정상 완주로 확대하지 않는다.
