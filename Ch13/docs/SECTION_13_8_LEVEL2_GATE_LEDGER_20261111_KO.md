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
