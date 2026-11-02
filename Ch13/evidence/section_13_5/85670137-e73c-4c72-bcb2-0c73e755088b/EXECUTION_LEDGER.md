## 2026-10-29 — 52c0 원본 중단과 별도 복구 관측

고정137소스4c355b9a의 G1 1420473e/cb7ac521/2a6ad536는24/24 각각 PASS, G2 429d51b0/9cb8920c는31/31 각각 PASS와 정상 종료·회수를 확인했다. G2 b7cedb29는 전진 중 환경이 끊겼고 결과 RUNNING/teardown없음으로 남았다. 실패/중단을 제외한3성공으로 세지 않는다. 부모52c0의 원래 restored/foreground close는 미확인 상태 그대로다.

복구09baf614는 옛 커널 종료·현재 Ch13 잔여 없음·새 두 시간 서비스 active/enabled를 읽기 전용으로 확인했다. 옛 lease를 새 인스턴스로 retarget하지 않았다. 원본137소스와 메타데이터를 복사했고 CDR326681332bytes/SHA4e676a74f00a4f30d3a217affa869a443a07f0bc0ec874c5e05463bbf873dc46는 native 원본 위치에 보존했다. 정상 닫힌 기록이라고 주장하지 않는다.

공백만 줄이는 후속 JSON 변경은 RED10.95→20PASS10.78초다. `bulk-json-benchmark-a542802f`의 실제 기록 일부에서 원래/변경/변경/원래를 비교했고 정규화 SHA b40504da1b7bad18dd166fed5d379dbe3765678092da1dbe83dcfcd88f3c272c가 동일했다. 인코딩 용량52.16%·평균CPU63.45% 감소이며 전체 인수 성공을 대신하지 않는다. 입력 원본과 기존 결과는 변경하지 않았다.

## 이전 원본 결과 — 38ce7f26 종료 확인

- 고정 source135 manifest4cd75cb87689c59e5ff159eb2ddd88c420ad798df96b603670aa5025a66c82c9: MuJoCo G1a104a38d PASS24/24, G2a9e062c5 첫 FORWARD SHIFT FAIL.3회 사전 선언 중 첫 G2 실패에서 중단했다. 성공 실행만 골라 연속 계수에 넣지 않는다.
- G2 원래 ROS41.120→44.748초, 참조2.159142752초/곡선2.625초,100ms settle 미시작. terminal/runtime/engine/reap/noForce/residual[] 모두 확인. 부모 session.json restoredtrue·foreground_sessions_closedtrue·final_related_runtimes[] 확인. 현재 엔진/서비스 임시 변경 없음.
- G2 controller SHA156221886614cde90741463088493e41280be1794a2095232385fc5d781bc7ef, 원본CDR29869931bytes/SHA8d21c1c73993783520d38846fb1aec8f9e41e5e2715b34253399cdfc96762e85. 새 요약ZIP4028273bytes/SHA60670422f79f28d68dd8dd9fc6494e4b009290e9bbc2ef56786d25ddfd885ab4. 기존 실패/종료 기록은 그대로 보존했다.
- ACK 분석a56d9743은 마지막16개 원래 ACK 모두 첫 적격 판단에서 허용됨을 확인했다. 미래 촬영 대기는 계약대로 유지한다. scalar 후보ac8b3972/fa545ffd 및 실제 DDS A/B b09a020f는 큰 개선을 보여 주지 않아 production 미적용이다. 재생입력4948804b는4.220865291초/1353메시지이며 엔진 인수 자료가 아니다.
- 00202b96 파생 proxy의 G2 cap20ms 사용 오류는 ec8c3759의 원래 max_step40ms로 정정했다. 원본 인수 실패 결과는 변경하지 않았다.

## 이전 고정본 결과 복원

G1 eed57b87 24/24 PASS, G2 6a7d1a30 LEFT SHIFT timeout FAIL. 소스133 manifest88e556fa. 액션 terminal·engine/runtime 정상 종료·reap·잔여 없음 확인. 부모 d1b4의 서비스 복원·두 foreground 종료 true. 첫 실패에서 중단했고 성공 연속 계수에 포함하지 않았다. 후속 판별 계획은 SECTION_13_5_INGRESS_CAPACITY_KO.md 참조.

# 13.5 실행 원장

## 2026-10-28 배포판 수명 경계 결함의 판별

수정 stderr producer의60PASS25.93초·8패키지 감사 뒤 clockbb8b781a는 원본 시계·19시동/종료34.32초까지 통과했지만, CPU/RPC 검증 중 원본offset899,656,095ns 점프 때문에 엔진0회로 중단했다. 모든 자식 회수·두 서비스 복원true·잔여[]다. 변경 없이 같은 실행을 반복하지 않았다.

`clock-lifetime-8df8c287-ac4a-4afc-9a54-e67c3ea932ac`의 원본 호출 구간은3,000/2,200ns다. Ubuntu22 journal은 같은 boot에서 systemd startup15.659803/400.868572초를 보이며, 정지19.048159초 뒤 서비스가398.973609초에 다시 시작하고399.472854초에 NTP 최초 동기화됐다. 원본점프399.440578210~399.460785511초와 약12ms 차이다. 관리 chrony syscall 발신으로 확정하지 않는다. 커널 boot와 개별 배포판 init 수명을 혼동한 기존 소유권 경계가 빠진 사실을 확인했다.

같은boot/새init거부 RED0.29초와 일반 세션 부재/서비스 명령 경계 RED를 보존했다. 소유 일반 사용자 foreground 세션·nonce/UID/PID/부팅/init tick/machine 검증·기존rollback/수렴31PASS0.51초다. 실제 두 배포판70초 read-only 세션1d845cd6도 상태 유지·close ACK·회수PASS이며 서비스 변경0회다. 다음 비교는 세션을 먼저 열고 기존 승인 서비스만 guard된 stop/start로 다룬다. 서비스 복원 확인 후 소유 세션만 정상 종료한다. 드라이버/chrony/영구설정/기준/Robot 제어 변경은 없다.

## 2026-10-28 native CDR 첫 실제 G1 종료와 증거 생산자 수정

clock eba9541e는 수렴107/QPC60/추가150초·원래preflight40초quiet0jump·19시동/종료25.02초·N10.6초/8감사를 통과했다. source133 manifest9374f13eecf6df1e05d41e4fb1509e64b0a183191e4ca65dc2b262af910ac4e3의 실제 G1cdcc24c2-886d-4ad4-a28c-434be66417c5는24검사 모두true·실제terminal·관측/엔진/runtime 정상 종료·회수/noforce/residual[]·finalizationtrue다. C++27562수신 레코드/CRC/footer/원본SHA8af6626b·JSONSHA1285dfd9·정상exit0도 확인했다. 그러나 `native_observer.stderr.log`의0바이트가 공통 증거 검사에서 거부돼 전체FAIL이다. CDR 파일명은 원인이 아니었다. G2시작0회·첫FAIL중단·두서비스복원true다. ZIP20,912,153bytes/SHA008d565a401972ced5a0a932f439c7d333382774fe241fde7d414ad5c8cbe154를 보존했다.

실제 수신기 최소 정상 종료를 기존 EvidenceRun에 넣어 같은 RED17.81초를 확인했다. producer가 명령/SHA·시작/종료·실제PID/exit·원래stderr offset/bytes를 기록하도록 고쳤다. 공통 size>0·required_checks는 변경하지 않았고 payload 원본을 보존한다. 관련60PASS25.93초다. S/C++·모터·시계·gain·물리·나이 기준은 이 수정에서 바뀌지 않았다. 기존FAIL을 성공으로 변경하지 않고 새고정본 실제한쌍을 판별한다.

## 2026-10-28 최신: CF 실패 확정·수신 경계 수정·용량 정리

최종 준비 결과: S빌드58.7초/큐3시험, N빌드14.3초/8패키지 감사, 관련163시험183.61초 PASS. 준비 스크립트의 S/N 로그 이름 중복으로 한 번 중단한 기록과 당시 방법을 보존했고, 성공한 S를 반복하지 않고 N부터 이어갔다. 새 실제 검증은 소스·설치본·방법 동결 뒤 기존 시계/시동 검사와 G1/G2 한 쌍으로 진행한다.

- clock99789a33은 종료·두 서비스 복원true·잔여[]다. source129/fb10의 G1462d6ed4는24/24 PASS, G2cf1fad26은 우회전1174.908초의 ACK 확인 실패로 전체 FAIL이다. 정상 runtime/engine 종료·실제 terminal·회수·강제정리 없음·원본/ZIP641,850,596bytes/SHA37b29042a84d1611bea99fa761aa8eac3389733c751296394017e691dd67a103/9분할을 보존했다. 아래의 조건부 첫회 재사용 규칙은 이 FAIL로 성립하지 않는다. 연속 성공 계수0이다.
- 원본 목표12개는 CM에서 발행 후5.5185ms, native prestep에서15.9757ms에 확인했다. client ACK 첫 수신은 기존 로그에 없어 미확정이다. `applied-timeout-cf1fad26`에 원본 해시·분석 방법·결과가 있다. 별도로 전체57,166프레임에서 몸체 촬영 하나의 ROS age208ms가3회 확인됐다. `interrupted-freshness-f20c3dbe-1eb2-4c4c-a095-debaee503602`의 직접 연결은 source→RMW1.4675ms, RMW→Python callback163.514201ms다. packet 부재나 모터 미실행으로 단정하지 않는다.
- ACK 후보를 보기 전에 처리 시각의 마감을 먼저 선언하던 순서 결함을 재현했다. 기한 안에 촬영·첫 수신되고 현재도 유효한 후보를 먼저 검사하며 capture/first-receipt/current ROS·wall 각200ms를 유지한다. late/future/duplicate/stale 거부와 실패 ingress/credit snapshot까지 관련32PASS35.30초다. 실제 CF의 ACK 수신이 미확정이므로 단독 해결로 주장하지 않는다.
- 같은 관측 지연의 구조를 반복 덧대지 않고 C++ 직접 CDR 수신·유계 worker·원본 ROS20ms frame prefix·종료 후 기존 Python 정규화로 경계를 분리했다. 기본 Python backend는 유지하고 native_cdr를 명시한다. 독립 ACK receipt는 controller receipt/credit이 아니다. TF GID·stage·fault·부모 손실·CRC/footer·미래/오래된 프레임 보존·실제 DDS 새17회귀16.84초 PASS, 기존 관련33회귀103.35초 PASS다. 최초 reader/process/선택/부모손실/ACK해석 RED도 보존했다. 네 발 고정 배열을1개로 잘못 만든 시험 입력의 SIGSEGV/RuntimeError는 fixture 오류로 분리해 수정했다.
- 사용자 용량 정리 요청으로 검증된 중복286파일3,692,695,699bytes와 ignore/미추적 생성 캐시30폴더625,628,861bytes를 제거했다. 원본/ZIP와 복원 목록 storage-compaction-9e30843e 및 cache-cleanup-86b15231을 남겼다. C 여유 약27.2GB, 기존 장/외부 원본/사용자13.4 교육 문서 보존이다.
- 현재 prepare-native-cdr-candidate.sh가 S/N 설치·8패키지 감사·관련 관측/ACK/runner 회귀를 진행한다. 새 실제 엔진 시작은0회다. 통과 후 source/설치/방법을 동결해 기존 원본 시계/19시동·종료→실제 G1/G2 한 쌍을 첫FAIL중단 규칙으로 판별한다. native 모터 보간·기준 완화·자동 재활성화는 없다. 최종3회·양 엔진·Nav2·commit/push는 미완료다. 아래 LIVE 표현은 당시 이력이다.

## 2026-10-25 G2 재개: 허가 시계·누적 이력·합성 가속도

- 착지 끝점 수정 후 G1 `3542bc49`23/23 PASS, G2 `3299043b`는 보행 전 guard ROS age FAIL.
  G2 허가 서비스가 직렬 원본 clock dispatch를 막는 구조를 실제 DDS RED1로 재현했고,
  별도 service group/기존 Draining2 적용 뒤 관련25PASS40.83초. 기본/G1 Events 경로 유지.
  원본 ZIP7,362,816bytes SHA `a897bf88699cb32c910b2180c8975d8d099539667f15ccb7232f1b68d7df90b8`.
- 수정본 G1 `cb81269f`23/23 PASS 뒤 G2 `6cee0671`: 실제 허가157.15ms 동안 원본 clock156ms
  갱신, 네 발 첫 이동 진행. 이후 명령235.535ms/프레임240.250ms 공통 간격으로 FAIL.
  ZIP37,058,740bytes SHA `877b15ac360ba3c08e8e325ea49ac7186d42b0e4b4b08d78c4cfea7b25452eae`.
  누적 관측 JSON 할당 재생에서 gen2 GC129.31ms, live128개 비교3.924ms. 오프라인 근거이며
  실제 모든 지연이 GC였다는 확정은 하지 않는다. G2 live cache/journal 전량 복구 분리,
  새 모드 RED→관련30PASS20.46초 및 종료/명령24PASS11.73초. GC 정책 변경 없음.
- 수정본 G1 `1132a704`23/23 PASS 뒤 G2 `206ac77a`: 최초 carry 실제 손가락 속도
  ±0.00507195m/s>기존0.005로 FAIL. 팔 관절 범위 정상. 후속 binding 실패와 구분.
  모든3,659frames/3,667controls 복구, live각128, 실제GCmax12.297ms.
  ZIP27,261,055bytes SHA `eb3f8b4270f4a56a780af20a26a06a42979c2aadb2a2d4fcd4cbc1adba026f08`.
- 세 실행 모두 engine/parent 정상 회수·강제 없음·잔여[]이나 G2 실제 STOPPED 인수 FAIL 유지.
  성공만 선택하거나 이전 소스 G1을 새 소스에 승계하지 않았다. 새 G1별 ZIP/manifest 별도 보존.
- 일반 CRAWL 합성 몸체 가속도0.487366m/s²>기존0.1을 RED1FAIL9.24초로 재현.
  G1 명령0의 offset 검사만으로 일반 travel을 보증했던 빈틈이다. 총 변위·기존 제한값 유지,
  입력 ramp/회전 항을 포함한 연속 quintic 시간 법칙으로 수정. 관련43PASS41.26초,
  전후진/회전/복합·ramp8PASS20.04초. Nbuild10.4초·8패키지 감사PASS.
  다음 새 고정 소스 G1/G2에서 실제 효과를 판별한다. Nav2/전체 최종회귀/push 미완료.

## 2026-10-25 첫 실제 G2 FAIL·착지 참조 결함 판별

- 사용자 Gazebo G2 전용 프로필 확장 승인 반영. N/R600PASS335.92초·N설치10.7초·감사8PASS.
  실제 G1 증거133MB 검사는1,143.9ms라서 제어 중 모드 서비스에서 시동 admission으로 이동했다.
  캐시 허가 뒤에도 파일 identity 변경은 실패하며 자동 재허가하지 않는다.
- 현재 추가 구현 포함118소스 manifest SHA
  `b75af9c06d1692d394ab560f09d4e9cba6f629dc1491cf13f990c05c25226e08`에서
  새 G1 MuJoCo `8d9364b7-42be-44dd-b0b0-ec89b1a9dfe1`23/23 PASS.
  ZIP `task8-g2-seed-mujoco-8d9364b7.zip`9,580,418bytes SHA
  `ec84ed4861d2b44f2e8d72686cadf3f0644552b61d41a873b506ade4d06eb6df`.
- 동일 소스/설치/장면의 G2 `99ee5235-7e1d-4d7f-80c1-c817b3b6b9e7`은 첫 forward 중
  FL/RR 뒤 FR의 참조+10mm에도 실제 하중20.258N이 남아 FAIL. 실제 지지 여유17.675mm,
  실제 발 높이 변화0.581mm, FL 미완성 착지 참조+7.388mm를 구분했다.
  부모/엔진0·회수·forced_cleanup=false·residual[]지만 실제 STOPPED 인수는 FAIL로 보존한다.
  ZIP `task8-g2-first-mujoco-99ee5235.zip`21,015,127bytes SHA
  `6db8cf1443c4555f46ecad5d6491b937ebbd7eb4de3614b10e9bc87d573bfa28`.
- 별도 `unload-derived-postmortem.json`은 원본을 바꾸지 않은 오프라인 유도 계산이다.
  SWING 접촉 즉시 중단으로 중간 참조가 anchor에 남는 결함을 RED1FAIL9.27초로 재현했다.
  기존0.02m/s 계획 곡선의 끝점 완료로 수정 후 관련46PASS36.67초.
  접촉 반동/참조 점프 방지·G1 전용 복귀·모든 기존 물리 인수 기준은 유지한다.
  이 변경의 물리 효과는 새 일치 G1/G2 실행으로 판별해야 하며 아직 G2 성공을 주장하지 않는다.

## 2026-10-25 G1 양 엔진 3회 연속 PASS·독립 감사

- Gazebo series `58c7013c-863d-469a-8ff6-1863be26a9d1`: `9a84b6f2`, `02c5c7e1`,
  `af6da055` 모두25/25 PASS. MuJoCo series `4838bfd2-55fc-43d9-8ead-b515ece094c5`:
  `db816a78`, `8df657f3`, `99bfdd00` 모두23/23 PASS. 첫 FAIL 중단 규칙의 새 고정 series다.
- 공통114소스 manifest SHA `34f193697acb681c8d741999149785b3a49cab0f2b0b164afcbcad9a42e4bd92`.
  6회 부모/엔진 정상 종료·회수·forced_cleanup=false·residual[]다. 실제 G1 10wall초·
  lift/재접촉/원래 참조 복귀/1wall초 안정화·carry terminal·센서/소유권을 모두 유지했다.
- `task8-current-g1-audit-7a9766b9-3c99-43e4-9a1d-89fc29b56e29.json`: 별도 검증기가
  6회 required_checks·현재114소스·모든 등록 artifact 크기/SHA·압축본 크기/SHA를 대조해 PASS.
  결과/실패 원리/재현 위치는 `Ch13/docs/SECTION_13_5_G1_RESULTS_KO.md`에 정리했다.
- Gazebo 실험은 여전히 G1 전용이다. G2 보행·Nav2·최종 legacy/matrix·게시를 완료하지 않았다.
  현재 task 종료 뒤 남은 성공사례를 먼저 조사했으며 결과는
  `SECTION_13_5_RESEARCH_DECISIONS_KO.md`다. 실제 schema/물리/설정/소유권 차이를 먼저 검증한다.

## 2026-10-25 고정 검증 중단 및 공식 event 실행기 비교

- `task8-calibration-events-remaining-regression.log`:73통과29.62초. 앞선460개와 합쳐
  변경된 navigation/runtime 전 범위를 확인했다. 시험 fixture/옛 G1 계산 수 기대값의 두 실패는 보존했다.
- 고정 series `ebb5ab24-50fe-48d0-a03f-671eed7264f7`: case1 `0a1068d6` **25/25 PASS**,
  case2 `f1b9b848` **23/25 FAIL**. 두 실행 모두 물리 G1/carry/센서/소유권 통과지만
  case2는 launch 부모 종료가 실패해 정상 종료 두 항목 false다. 세 번째는 실행하지 않았다.
  엔진/runtime/relay/TF 관측기 exit0, 부모는 최종-15/forced_cleanup true, 잔여[]로 기록했다.
  실패 ZIP29,054,880bytes SHA `df5a8c4a9ce2b39ee07100bb46543b1d311ab20cfc81547fb7e4e9dc26b01aa1`.
  해당 series 원본의 status RUNNING은 cleanup assertion에서 중단된 상태이며 성공/진행으로
  해석하지 않는다. 실제 종결은 **두 번째 FAIL에서 중단**이다. 원본 JSON을 덮어쓰지 않는다.
- 실패 system.log: 엔진 clean exit 뒤 부모 SIGINT, 종료된 gazebo action의 timer가 남아
  SIGTERM/SIGKILL escalation이 발생했다. 공식 설치 ros_gz_sim은 `on_exit_shutdown` 시
  `ExecuteProcess(on_exit=Shutdown())`을 사용한다. direct navigation launch에서 그 수명
  연결이 빠진 차이를 확인했다. 외부 launch는 읽기만 했으며 Ch13 navigation 경로만 수정한다.
- 작은 실제 launch 자식 재현 RED1실패17.81초 → 종료 이벤트/신호 없는 bounded parent wait
  및 장면·감사·실패 보존 **22통과11.82초**. timeout은 FAIL로 남기고 별도 소유 정리를 수행한다.
  G1 물리 10초/안정화/센서 및 모든 required_checks는 그대로다. 새 launch로 다시 고정검증해야 한다.

- series `4f1059f3-e748-4363-a160-ae63d3754856`는 첫 `5bdbaded-069f-4110-ac2d-aa03f2bd8468`에서
  원래 10wall초 실패로 중단했다. 3회 중 성공을 골라 세지 않는다. 정리/잔여[] 확인,
  85소스 ZIP28,321,640bytes SHA `c5210e90fba7ba029f76c468dc5587d42e72c4c6e59dca57fa5abc5e8f664d41`.
- 설치 rclpy7.1.12 공식 EventsExecutor 비용 비교: 동일 실제 DDS1,600개 모두 순서대로 수신,
  CPU345.036→196.143ms. 기존 직렬 navigation 역할에만 재사용하며 crawl2worker와 팔
  독립 receiver는 제외한다. 물리/시간 인수 성공으로 해석하지 않는다.
- 첫 관련 시험 `task8-calibration-events-action-shutdown-related` 전 단계는20통과/8setup오류였다.
  원인은 공식 EventsExecutor가 MessageInfo callback에 원본 tuple 하나를 전달하는 차이였다.
  `task8-calibration-events-message-info-red.log`: 실제 DDS1실패8.88초.
  Ch13 자체 호환 경계는 원본 두 객체·required signature·동기/비동기 형식을 보존한다.
  `task8-calibration-events-message-info-green.log`:14통과22.47초. 외부 SDK 수정 없음.
- 설치 의존성 source binding 부재 RED1실패6.81초→
  `task8-calibration-runtime-dependency-green.log`:6통과4.23초. runtime/vision 변경·누락·
  외부 prefix·symlink 이탈을 거절한다. 파일 SHA는 실행 PID 매핑 증거라고 부르지 않는다.
- `task8-calibration-events-action-shutdown-related.log`: 실제 액션 취소·terminal drain·
  실행기/worker 수명·메시지 이벤트 관련 **19통과139.75초**.
- `task8-calibration-events-rn-native-build.log`: runtime/navigation 설치20.8초 성공,
  8패키지 감사 및 별도 strict runtime/vision/navigation byte 감사 통과.
  SDK version/wrapper/extension fingerprint는 `task8-calibration-events-rn-native-runtime-audit/`에 있다.
- 첫 전체 회귀는 공유 Guard Rig가 CrawlRig에도 event factory를 사용해 setup거절,
  **7통과1오류10.84초**에서 중단했다. 제품의 병렬 crawl 차단을 약화하지 않고
  시험 Rig에 factory를 주입해 실제 make_control_executor를 사용하도록 수정했다.
  원래 실패 로그를 보존했다. 후속은460통과 뒤 오래된 G1 후보1개 기대값에서 실패했다.
  G1만4개/일반CRAWL1개라는 현재 설계를 각각 확인하도록 매개변수화했다. 이는 안전/물리
  인수 한계 변경이 아니다. 통과460개를 반복하지 않고 해당 파일 이후 및 runtime 전체를
  `task8-calibration-events-remaining-regression.log`로 검증한다. 아직 새 backend의 물리 인수는 없다.

## 2026-10-25 첫 물리 G1 통과·종료 경합 재현·고정 검증 계획

- `58b9e263-4c7f-49df-b42c-8568932578ab`:원래가속도복귀뒤에도10초deadline FAIL.
  들기시작까지4.586ROS초로직전4.596과거의같아SHIFT만빠르게하는방법으로는
  느린가상참조하중해제의직렬비용을없앨수없었다. 전센서/접촉/lift는PASS.
  실제native/launch/relay0·회수·강제없음·잔여[]. 85소스ZIP28,422,360bytes/SHA256
  `8c3518cfbc821bd1001ae921aacd97466483cdef4763906ba537cfb82af3f4a5`.
- 고정소스의판별실험`2d92e769-671d-403b-b5ed-6a657f18e8cb`, result
  `e12f0c7f-69f0-46f2-8ed1-608d034ca538`:전체 **FAIL**. 물리G1/실제carry terminal/
  모든관절·TF·센서·힘검사는TRUE, first_fault/stop모두null이다. 실제STAND후보후1초
  실측확인까지원래10초안에끝났으나crawl 종료의unretrieved Destroyable예외로
  normal_runtime_exit/normal_engine_exit는FALSE다. 실제모든종료코드0/회수/잔여[]와구분한다.
  이실행은처음부터스레드CPU판별로지정했고연속인수성공으로골라세지않는다.
  85소스ZIP25,540,270bytes/SHA256
  `f384d264b6f4487b86992c9cfa9b5f2d07b126bf870a5627bea6107e887f2689`.
- 실제소유native PID47276/start3607094/PGID47273의39회CPU표본을읽었다.
  STAND의main ruby53.46%, llvmpipe두스레드합19.93%로renderer하나가전부라는가설은
  지지되지않는다. 이름/CPU는함수stack/단일원인증명이아니며affinity를바꾸지않았다.
  현재공개CPU정보는i7-1185G7/4물리8논리코어, DART는OpenMP에링크되지않았다.
- 실제종료RED`task8-calibration-executor-drain-red.log`:1실패8.46초. worker콜백실행중
  guard파괴를실제pool/guard의경계관찰로재현했다. 기존Ch13 DrainingExecutor를재사용한
  관련14PASS12.78초/설치15초/8패키지감사PASS다. 외부rclpy/기존공통코드수정없음.
- 이제같은동결소스/설치본/물리설정으로Gazebo3회연속을미리계획한다. 각실행은새UUID,
  결과/소스일치/실제회수/잔여[]/원본압축보존후에만다음실행을시작한다.
  **첫FAIL에서중단**하며재시도/성공만선택/원래25개검사완화는없다.

## 2026-10-25 G1 우회 조치의 구조 재검토

- `025d4b84-1972-46d9-8f82-8c89313d3881`, result`199e374a-a9c7-4328-949f-139711f8c045`:
  계산batch후에도원래deadline FAIL. 요청22.028ROS초, SWING26.624/TOUCHDOWN27.124/
  STAND후보28.308, 남은wall1.19549초, fault28.984ROS초였다. freshness는이번PASS이나
  이전scan실패해결증거로취급하지않는다. 실제native/launch/relay0·reaped·noforce·잔여[].
  85소스ZIP27,091,495bytes/SHA256
  `18858dc953cacdd1f9c664eab590049294c98883213d09a299d00246f8220467`.
- 더많은작은보정을쌓는대신실패했던임시G1절반가속도배율을재검토했다.
  `legubiao/quadruped_ros2_control`실제API git tree의고정커밋
  `5434c5810d1a7fe223bcfd04550e9d3bfdd4b458`에서controller update/FSM/README를읽었다.
  공식native update의단계분리원칙만참고하고KDL불안정주의·다른5종명령인터페이스·
  팔하중미검증·시간기반FixedStand전이를확인해소스/게인/완료판정은가져오지않았다.
- 수치접촉0에서는절반가속도가접촉충격을해결하지못했고50µm후실측4건은모두들기/복귀
  뒤deadline이첫fault였다. G1의내부배율.5만제거해기존설정max.1m/s²로복귀한다.
  상한/일반CRAWL/목표/게인/30Nm/실제속도·하중·1wall초·10초는유지한다.
  RED2실패/1통과10.60초→관련53PASS43.87초. 새로운실제실행전이며원인해결확정은아니다.

## 2026-10-25 착지 후 안정화와 G1 계산 대기 예산

- `f086a6a1-9f3c-4dc7-906b-42a352c7ee27`:프로파일러없이실제G1 **FAIL**.
  SHIFT→SWING26.484→TOUCHDOWN27.004→STAND후보28.248ROS초,
  후보시남은wall1.67864초, 원래deadline29.544ROS초에fault.
  실제세번착지와원래rest복귀를확인했으나연속1wall초정지확인은미완료다.
  endpoint기준오프라인분해에서는모든표본관절오차<.03, 마지막오차.023247rad,
  마지막관절속도.000868rad/s였다. 몸체v가.003경계를다시넘어마지막연속healthy
  probe구간은.880644wall초였다. 이는정확한owner callback/lease재현이아니다.
  `stand-readiness-postmortem-v2.json`에분리기록했다. 최초분석의NumPy bool직렬화실패
  불완전파일도원본그대로보존했다.
- 독립sensor_freshness도FAIL1건: scan capture16.300/판단16.410ROS초,
  원래receipt34536395373144/판단wall34536724600789ns, wall age329.228ms>300.
  `planner-and-age-postmortem.json`에원본실패를보존했다. 시간예산과다른실패이며
  아직수정됐다고주장하지않고타임스탬프변경·허용치확대·행제외를하지않는다.
- 실제crawlCPU79.02%(직전93.39)/contact44.18%(51.88), STAND RTF.6724로
  STAND물리속도자체가획기적으로개선됐다는뜻은아니다. 실제native/launch/relay0·
  reaped·강제없음·잔여[]. 최초fault로전체normal_exit 실패를유지했다.
  85소스ZIP28,314,133bytes/SHA256
  `31f395c931ea7f29d5a4c32a2f453217ed6522c43f4c8b5f5acef4bc18f69fdd`.
- G1의비구동계산은후보1개마다50Hz의다음tick을기다렸다. 실제저장입력으로후보4개
  계산50회측정은p95 5.173ms/max6.058ms였다. 물리곡선/가속도/게인/접촉을바꾸는대신
  G1만tick당최대4개의순수후보계산을묶는다. 정상보행은1개유지, 계획중참조hold,
  각tick실측안전검사/동일endpoint/동일duration/.05가속도/원래deadline은유지한다.
  `task8-calibration-planning-batch-red.log`:1실패/1통과8.62초로불필요한대기를재현했다.

## 2026-10-25 실제 소유 노드 계측과 QoS 대기 항목 수정

- `787361fb-f68b-4389-a719-47811bfbd10e`: 실제motion_guard만공식launch prefix/filter로
  계측했다. G1은원래10wall초deadline FAIL, 추가`unprofiled_acceptance=false`도유지했다.
  실제native/launch/relay0·회수·강제없음·잔여[]. 84소스ZIP27,943,096bytes/SHA256
  `5a407be277fbbc97df8c9d2511b09c7a5e664c8558e13e32e43869f2faa34ca0`.
  `main-profile-analysis.json`은실제명령과프로파일SHA/호출수를보존한다.
  main-thread wall계측이며watchdog/전체CPU로해석하지않는다. coroutine호출의중첩시간보다
  동기대기항목열거407,976회와후속실제DDS측정을근거로사용한다.
- `task8-calibration-qos-waitables-cost.json`:8토픽50Hz로각각1,600메시지전수신,
  기본경고이벤트34waitables/454.139ms CPU→경고없음2waitables/330.754ms CPU.
  초기fixture의숫자로시작하는토픽명오류는명칭만수정하고엔진/제어소스는건드리지않았다.
- 신규`dispatch_node.py`는공개rclpy API로기본QoS/타입경고전용waitable만제외한다.
  QoS·메시지·명시적event container·주기·원본촬영·소유권·200ms/watchdog는유지한다.
  RED3실패7.52초→실제ROS/시동/carry terminal/시계/종료관련48PASS148.59초.
  지정matched callback실행과양종류Node의메시지전수신도확인했다.
  새실제엔진의RTF/G1은다음실측으로판정하며국소CPU개선을성공으로세지않는다.

## 2026-10-25 압축 여유 실측과 CPU 가설 판별

- `bd8ad3ae-4d3b-4ce5-950b-da61eebd4df2`, result`beb18a76-d9ae-4d09-945b-366a782a0e44`:FAIL.
  요청21.528ROS초/wall33433742130591, SWING26.268(요청후7.359wall초),
  TOUCHDOWN26.818(8.195wall초), 원래10초deadline에28.054ROS초fault.
  마지막참조는원래rest.016705m/속도0까지복귀했고실제FL중심.019798m/하중28.902N,
  착지고유표본28.004/28.024두개였다. 고유세번째+1wall초안정화전이라FAIL유지한다.
  전센서/힘/지원/lift/설정/실제lib계약PASS, carryterminal수신TRUE.
  native/launch/relay실제0·reaped·noforce·잔여[], 물리STOPPED/전체normal_exit는FAIL.
  84소스ZIP26,259,297bytes/SHA256
  `6e133507813a6fd9c19e6b97f5a08ec0dd424423ae0366c5b80e4a379ef435b5`.
- STAND실측RTF.6773, crawlCPU93.39%/17threads, contact adapter51.88%/15threads.
  `task8-calibration-kernel-{default,blas1}.json`:동일저장입력500회수치계산만측정했다.
  기본1.958ms/회와BLAS1지정2.284ms/회, 출력동일. NumPy1.26.4는Netlib BLAS3.12.0,
  계산프로세스3threads였다. OpenBLAS과다스레드가설은지지되지않아환경변경을하지않았다.
  이수치는실제ROS dispatch나물리인수가아니다. 선택도구threadpoolctl은설치돼있지않았고
  추가설치대신실제로매핑된라이브러리와기본cProfile을읽었다.
- 다음판별은공식ROSlaunch의실행파일prefix/filter로소유motion_guard하나만부모cProfile
  아래시작하는것이다. 외부원본/시스템/드라이버/관리자설정은변경하지않는다.
  원래모든required_checks에`unprofiled_acceptance=false`를추가해계측실행은G1승격불가다.
  main-thread계측이므로watchdog별도스레드의비용을측정했다고해석하지않는다.

## 2026-10-25 승인된50µm 첫 실측과 시간 예산 판별

- `5b1854b7-9696-409c-b1c8-001a32ba2d12`, result `6cabc4df-ab1c-4761-9c85-92b2dcaad1c7`: **FAIL**.
  실제DART설정계약1,540건과같은PID라이브러리4개SHA검증PASS. 실제lift PASS.
  요청20.698ROS초/wall16633698646474ns, SWING26.476(요청후8.671wall초),
  TOUCHDOWN27.024(9.613wall초), 최초fault27.246/16643712218484ns는원래10초deadline.
  실제FL중심마지막.028441m, 원래rest.016705m/참조.035148m로복귀미완료다.
  STOPPED·전체normal_exit FAIL보존. deactivate/typedterminal/consumer/relay종료TRUE,
  실제native0/launch0/relay0/reaped/noforce/residual[]. 84소스ZIP26,550,601bytes SHA256
  `b16e144f57403be36a330550e1efc3472ffbe496e7d90441c2999d9b3bc68363`.
- S전체50PASS11.1초/감사8PASS. N설정/라이브러리/종료/시계관련62PASS9.94초,
  장면관련29PASS19.69초. 현재새소스N전체는아직미실행(이전432PASS와구분).
- `precondition-plateau-postmortem.json`: 실제명령source_input FK와동일native촬영의
  원시하중을대조했다. 22.402–23.482ROS초참조.019705142m에서55표본/1.08ROS초정지,
  FL최소18.529N(전발최소동일). 가상참조를물리floor로상한설정한내부3mm조건이지연원인.
  이는실제발높이또는owner재실행이아닌오프라인명령분석임을명시했다.
- 회귀 `task8-calibration-precondition-envelope-red.log`:2실패/9통과16.10초.
  단순상한제거는관련10실패/54통과45.78초로강체모델조기접촉소실을검출해폐기했다.
  원래rest+10mm/.002m/s/10N/전발2N/10wall초는보존하고측정관절의추종압축여유절반을
  추가상한으로사용한다. 새API RED11실패/1통과11.42초→관련1실패/64통과49.53초.
  남은한건은압축없는완전이상추종에진행을요구하던전처리시험이다. 강체에서는
  조기해제를금지하도록바꾸고다른기존안전회귀/실측인수기준은유지했다.
  첫green명령은없는파일명으로미실행, 한차례WSL실행은자동승인검토사용량한도로
  미실행이었다. 원본로그를보존하고서비스허용확인후재개했다.
  `task8-calibration-precondition-compression-green.log`:65PASS47.18초.
  추가`precondition-compression-postmortem.json`은같은측정관절FK의남은여유1.30–1.50mm를
  확인했다. 최초postmortem은덮어쓰지않았다. 설치감사후새실제실험으로판별한다.

## 2026-10-25 접촉 경계 실측·가설 판별 (Task8 미완료)

- 전체navigation `task8-calibration-reference-ramp-full.log`:432PASS309.90초.
  post-step관측회귀후 S전체49PASS11.1초/감사8PASS,
  `task8-calibration-contact-event-post-native-{build,test}.log`, `...-install-audit.json`.
  앞선진단창만의S49PASS와구분한다. 이전strictreader는PostUpdate에서Physics가비운
  명령을필수로요구할위험이있어실제실행전에수정했다. compile REDtooManyArguments를
  기록한뒤기본pre-step명령검증은엄격히유지하고debug post-step만null을허용했다.
- `15aaca4a-0333-4f16-a46f-abcf2e8bc93f`, result
  `7f18d4dc-9bbd-4a7d-bc96-2cfd29021cc4`:FAIL. 20ms연속참조는실제native16,776개
  다리참조기록에서입력-적용차이최대0.00166527rad/힘계산오차0으로확인했으나,
  carry최초fault ROS25.150/wall12681324325088ns,선택arm4속도0.0333227>0.02.
  SHIFT/vertical=null. 전센서/IMU444고유·누락0은PASS. 정지·deactivate·terminal·
  소비자/relay종료확인/native0launch0relay0/reaped/noforce/residual[]. 전체normal_exit
  실패유지. 80소스ZIP21,298,121bytes/SHA256
  `e6e6254cb1cb0ef80c5c8be5778d2279356eeb9df33a16a8aaa8b311c32d4197`.
- 원시이벤트추가 `3d830070-5d58-47c3-9db1-4a15c0835319`, result
  `06086e6c-f09d-4cab-9948-3da3f2105d9f`:FAIL. 31개2ms이벤트를확보했다.
  carry최초fault ROS25.912/wall13734345549422ns,선택joint25.910초가원생post상태의
  모든관절속도와정확히일치했다. 팔최대속도는0.02미만이나그리퍼0.00550265m/s가
  기존0.005를초과했다. 직전25.908초에는팔2/4의짧은속도충격도남았다.
  모든실패를팔4나callback원인으로통일하지않는다. 센서freshness/contact/IMU/stability
  통과와carry/lift/최종소유권/normal_exit실패를그대로보존했다. 실제정지·deactivate·
  terminal·소비자/relay단계성공/native0launch0relay0/reaped/noforce/residual[].
  81소스ZIP21,273,931bytes/SHA256
  `7a525fe3788114fba7efe62b7b8773c0227bf30887f50b4102a5c8f9a4707569`.
- 보조분석은원본수정없이각실행폴더에별도JSON으로보존했다.
  `contact-event-postmortem.json`(원시wrench/깊이/관절상태),
  `phase-contact-postmortem.json`(정적5,000촬영gap0/교정640촬영gap4),
  `event-body-fit-postmortem.json`(네발실측중심+실측관절FK로root rigid fit,
  최대잔차1.337e-15m/2ms위치2차차분최대2.52586m/s²),
  `contact-gap-transition-postmortem.json`(모든발의직전구바닥0.7–3.1nm위/다음pair0/
  0.19–0.36mm침투/다음step복원). nativeIMU나runtime pose를만들어내지않았다.
- source DART6.13.2의기본ErrorAllowance0을확인하고,별도vendor공개getter 조회도0.
  `task8-calibration-dart-contact-default.json` 및CMake/ldd/바이너리SHA기록.
  최초pkg-config두시도는vendor경로/eigen별칭의존문제로실패했다. 외부설정이나파일을
  고치지않고기존gz_dartsim_vendor/DART CMake target으로조회했다. 엔진설정변경없음.
  실제G1접촉허용오차0→50µm비교는2026-10-25사용자가승인했다. 이checkpoint에는
  아직구현하지않았으며후속테스트우선수정·실측을진행한다. 실제값조회/실험필수검사를
  추가하고원래모든required_checks를유지한다. 일반보행승인·3연속·최종인수는미완료다.


## 2026-10-24 재개: 원래 지지 참조 미복귀와 진단 전송 설정 판별

- 실제 MuJoCo `293d0ff3-1321-4de9-997e-5069b7fde889`, resultUUID
  `ac3a8fe9-a3ff-4b9b-8c1e-566ea24a0ee3`: **G1 23/23PASS**. 원본 preload
  복귀·실제carry settle·실제terminal·관절/TF소유권·센서·엔진/runtime정상종료 확인.
  native/launchexit0·parent_reaped·probejoin·noforce·residual[]였다. IMU712고유촬영/
  누락0/최대gyro오차0.0079749173rad/s, lift15고유촬영. Gazebo/G2/Nav2통과가아니다.
  새plannedreturn 전체navigation **425PASS282.69초**(`task8-calibration-preload-return-full.log`).
  당시79runtime소스/evidence ZIP `task8-preload-return-mujoco-293d0ff3.zip`
  9,921,948bytes/SHA256`6af9b6e86db4bfc9aea961f259da7d77738b029a74ae4781e6ce80562b5c3748`.
- 사용자승인후 G1 검증모드에만20ms연속참조비교를구현중이다. 실제기존 PositionPDSystem
  추가최소회귀는 RED3FAIL/4PASS→GREEN7PASS136ms. 기본gain/힘상한/위치·속도쓰지않음/
  소유권시험도함께통과했다. 중간새목표는당시적용참조부터시작하고 비활성화는적용중참조를
  유지한다. rollback은원래stickyfault/힘0이다. 팔·그리퍼/ramp.01/명시적flag없음은거부.
- G1장면 RED5(옵션미구현)/8.17초→관련13PASS10.78초; metadata위장과일반launch
  진입 RED2/5PASS8.92초→관련23PASS17.99초. 기본장면·게인/감쇠·전체물리link/joint
  동일성을검사했고 opt-in생성값12관절/.02와실제modelhash바인딩을확인했다.
- 실제적용참조진단 REDmissingheader54.5초→GREEN native7PASS131ms.
  Ch13전용컴포넌트는입력/적용참조/기간/write시각을저장한다. physics가소비하는
  위치/속도명령컴포넌트가아니다. 기존observer에서읽는JSON과전체S검사·8감사는
  후속고정설치검증중이다. 아직새Gazebo실행성공이나일반CRAWL승인증거가없다.

- 원본preload복귀 Nbuild15.1초/감사8PASS 후 실제Gazebo
  `e2cb2cc1-96ca-4689-8c6f-439975d3c2c4`, resultUUID
  `648600ba-08b5-476b-9fae-aac41f2f4061`: **FAIL**. 새수직복귀 전 SHIFT에서
  carry 최초fault ROS22.902/wall11116585075450ns. 선택joint22.898초의
  arm_joint_4 속도0.03319615rad/s>기존0.02. Crawl first_fault=null,
  first_stop ROS22.928 `calibration_carry_not_ready`, vertical=null.
  따라서 복귀 경로 수정의 실제 성공/실패 판별까지 도달한 실행으로 세지 않는다.
- 2ms원생 접촉 후분석:22.896초 RL pair0/힘0/중심z0.0197366m,
  22.898초 FL pair0/힘0/중심z0.0197458m, 다음22.900초 네발pair1로 복원.
  이때3발은하중을유지해 축약summary만있으며 fullpair상세가 있다고 주장하지 않는다.
  정규화50Hz 접촉/support검사는 통과했다. 네발50Hz기록만으로 원생2ms단절을
  부정할수없고, 시각적으로 바닥에가까운 발을공중/정상접촉으로 임의대체하지 않는다.
  물리 접촉/저주기참조 적용의 상관은 후보이며 인과/단일 root cause 확정은 아니다.
- 물리STOPPED/deactivate/typedterminal/소비자/relay단계는 모두성공,
  native/launch/relay 실제exit0/reaped/noforce/residual[] 확인. 그럼에도 초기fault로
  전체normal_runtime/engine 판정false·sensor_freshnessfalse·contact_liftfalse 등
  기존 required_checks 실패를 그대로 보존했다. IMU453고유촬영/누락0/최대gyro오차
  0.000007263634rad/s다. 원본79runtime소스 ZIP
  `task8-control-clock-e2cb2cc1.zip`18,941,062bytes/SHA256
  `892f903a10488ed0b1cb05e5719e80c943bf547cfb42d4d69748f2a2c652b8be`.
- 별도 통신 결함: 두engine 프로필로 확장한 실제DDS QoS 최소회귀는
  `task8-calibration-native-reference-qos-red.log`1FAIL/1PASS6.44초.
  설치bridge의실제RELIABLE 제공에 맞춰 진단기록기만 양engine depth100/RELIABLE로
  수정했다. 실제Gazebo DDS fixture도관측된제공설정으로맞췄다. 제어센서 QoS/시각/age,
  누락fail기준은변경없다. 관련17PASS11.64초(`...qos-green.log`). 드문누락의후보를
  제거하는수정이며 모든유실원인해결이나 접촉/팔충격원인수정으로과장하지않는다.

- 일반 landing fixture 수정 후 `task8-calibration-full-after-landing-fixture.log`:
  전체 navigation **419PASS298.44초**. 이는 새 planned-return 구현 전 고정본이다.
- 사용자가 G1 원본 preload까지 유계 복귀 재설계·검증을 승인했다. 별도 새 branch나
  전체 계획을 다시 만들지 않고 현재 Task8에 적용했다. 신규 최소 회귀
  `task8-calibration-preload-return-red.log`:3FAIL/1PASS8.18초로 접촉 시 참조속도
  불연속·측정 안정화 전 소유권 해제를 재현했다. 최소 수정 후4PASS6.70초.
- owner 연결 RED(`task8-calibration-owner-settle-red.log`):4FAIL/13PASS15.08초.
  실제 owner의1wall초 판정이 끝나도 소유권을 해제하지 않는1건과, 승인 전 접촉 즉시
  느린 seek/참조 endpoint 전 완료를 전제한 G1 전용 시험3건이었다. 일반 CRAWL
  assertion은 유지하고 G1 시험에 원래 endpoint·원래 하중/고유촬영 확인을 반영했다.
  `task8-calibration-preload-return-related.log`: **65PASS53.59초**.
  정상 CRAWL 조기접촉 정지·연속성, 별도0.002m/s 탐색, 교정 서비스, 원본deadline,
  endpoint에서 속도0·기존 속도/가속도 상한·중복촬영 거부·소유권 유지/실제owner확인을 포함한다.
  새 실제 Gazebo 판별 전이며 해당65건을 전체 인수 성공으로 세지 않는다.

- 실제 Gazebo `bea603b2-d810-42c5-8612-eb992da14d0c`, resultUUID
  `3ced1bf3-d831-4042-bba2-1c4a95965c18`: **FAIL**. 요청wall8505512887062ns,
  deadline8515512887062ns. SWING wall8512721591874ns, TOUCHDOWN
  wall8513381115145ns, STAND 후보 wall8514998469272ns(9.486wall초).
  실제 lift와4N/고유3촬영 재접촉은 통과했으나 후보 참조z0.024328724m는
  원래rest0.016755124m에 돌아오지 않았다. 첫 STAND ROS32.740의 FR calf 오차
  0.03954502157rad>0.03, 속도0.0007829rad/s; native 힘 -29.7272946Nm/상한30.
  전체 sensor/IMU/contact/lift/stability 통과와 최종 carry settle 실패를 구분한다.
- 물리STOPPED/runtime_exit=false를 보존했다. deactivate/typedterminal/소비자/relay
  정리는 성공, 실제native0/launch0/relay0/reaped/noforce/residual[]였다.
  원본79runtime소스 ZIP `task8-control-clock-bea603b2.zip`28,544,869bytes,
  SHA256 `1e277072ff551b99cecb2698a9d90f29fd5a20c8cfa580ae81d6a5c64e7459d7`.
  `calibration-stand-feasibility.json`은 첫 STAND 실측 및 제한된25개 오프라인 IK
  후보 분석이다. 일반적 불가능성 증명이나 실제 새 엔진 실행으로 취급하지 않는다.
- `task8-calibration-full-checkpoint.log`: 전체 navigation 416PASS/3FAIL238.82초.
  3건 모두 `test_landing_continuity.py`가 G1을 요청한 뒤 일반 CRAWL의
  `_swing_duration`을 읽은 fixture 오류다. 실제 작은 CRAWL 명령으로 경로를 고쳐
  원래 조기 접촉 정지·연속성·0.002m/s assertion을 그대로 유지했다.
  `task8-calibration-normal-landing-fixture-green.log`: 관련37PASS27.59초.
  전체 재검증은 별도 로그에 남긴다. 실패 로그를 덮어쓰지 않았다.
- 최초 `task8-calibration-bridge-qos.json/log`: explicit rclpy Context와 global
  spin_once 혼용으로 진단 helper 실패. 자식 PID8777 정리가 누락됐다.
  `task8-calibration-bridge-qos-cleanup.json`: UID/정확한 명령/실행파일 해시를
  대조한 뒤 해당 PID에만 SIGINT, /proc 부재 확인. 직접 자식이 아니므로 returncode나
  정상 회수를 만들어 기록하지 않았다. 엔진 정상 종료 PASS로 취급하지 않는다.
- 새 `task8-calibration-bridge-qos-context-fixed.json/log`: 자신의 Context의
  SingleThreadedExecutor 사용, finally에서 항상 직접 자식 SIGINT/wait 보장.
  PID8881의 실제 설치 bridge 진단: publisher 1개, RELIABLE/VOLATILE,
  discovery depth0은 unknown. exit0/owned_exit_confirmed=true. 실제 엔진/모터 명령 없음,
  helper·자식만 domain163, 정상 시스템 domain159 유지. bridge executable SHA256
  `c913a164072ee795bad4f7598d2a8b945e24723e20461cc2941fbbb091980c80`.
  BEST_EFFORT 기록기와의 차이를 다음 최소 회귀로 검사하며 누락 원인 확정은 아니다.

## 2026-10-24 승인된 G1 전용 교정 구현·첫 실제 실패

- 전처리 N설치14.0초/8감사PASS 후 실제Gazebo `db492b97-d4db-4551-9a5a-673d3f14522c`,
  resultUUID `1d800be7-c113-48bb-9b5a-56e6f6b81791`: **FAIL**이지만새경로에서
  실제contact_lift검사통과/TOUCHDOWN도달을확인했다. 요청ROS24.968/wall8054469850151ns,
  SWING30.792/wall8061541316810ns(7.071wall초),TOUCHDOWN31.330/wall8062222829678ns
  (7.753wall초). helper의실측6mm/고유3촬영은31.284/31.304/31.324초였다.
- 원래deadline8064469850151ns에서최초faultROS33.226/wall8064481103460ns.
  마지막FL실측중심z.0199812/하중2.69719N,내부4N복원확인이안됐고landingcaptures=[],
  참조z.0253903/속도-.002/rest.0167551. 최종1wall초settle은아직시작하지않았다.
  접촉·센서·IMU·stability검사들은이번실행에서통과했지만전체인수로과장하지않는다.
- physicalSTOPPED/runtime_exit=false,그외deactivate/typedterminal/소비자/relay정리성공,
  native0/launch0/relay0/reaped/noforce/residual[]를그대로보존했다. 원본79runtime소스ZIP
  `task8-control-clock-db492b97.zip`27,632,812bytes,
  SHA256`5c8448994ed86d03d37c795cecb3d11f83ea85f4b7d65dbabb8af3000d2a5b2e`.
- 다음병목은공중의floor+2mm근접도접촉seek속도로줄이던내부조건이다. RED1/5.70초:
  하중0인데복귀속도.002에묶였다. 높이조건만제거→관련32PASS24.98초. 기존공중
  최대.02/동일slew·원본restbound는유지하고실제2N하중에서즉시fastdescent를멈춘다.
  접촉후.002/4N/고유3촬영/owner1wall초/원래10wall초를바꾸지않았다. 다음실제검증전이다.

- G1만peak가속도를.05로낮춘관련41시험PASS68.52초/N설치20.3초/감사8PASS 후
  실제Gazebo `1823b29e-189e-4768-8210-fab3affe7540`, resultUUID
  `d6f7c56f-ec84-4775-a6b6-b35f5fdccc62`: **FAIL**. 초기SHIFT접촉/팔자세상실이
  먼저발생하지않았고duration2.4861856ROS초/본unload24.600초까지진행했으나,
  요청ROS21.710/wall1827200294096ns의10wall초deadline에서실패했다.
  최초faultROS28.618/wall1837210858419ns,FL목표z.0248431/rest.0167551로8.088mm,
  verticalhelper는아직진입전이다. 간헐접촉문제해결확정이나G1성공으로세지않는다.
- IMU기준촬영25.840초1건누락/전체sensor freshness실패도보존했다. carry최초fault는
  ROS28.640의`crawl:model/fault`로Crawl deadline후였다. physicalSTOPPED/runtime_exit
  false,그외deactivate/typedterminal/소비자/relay정리성공/native0/launch0/relay0/
  reaped/noforce/residual[]확인. 소스79고정ZIP `task8-control-clock-1823b29e.zip`
  24,657,082bytes/SHA256`b97dbf07efa82608439c973b8702d7922cdda39b53a64bb7f96e9066afa74efc`.
  사용자작업재개시ZIP전체바이트해시를재확인했다. 기존실행기세션ID는이미닫혀있었다.
- 다음은네발하중유지중기존압축참조를SHIFT와겹치는전처리다. RED10/8.75초→
  관련48PASS46.91초(일반보행/PythonMuJoCo구성요소/ROS포함). FL10Nreserve/네발각2N/
  기존.002m/s/원본rest+3mm와초기floor-.2mm중작은상한을유지한다. 조기접촉손실은
  실패이며본unload의tripod·정지100ms와전체10mm예산은원본rest에서검사한다.
  이전보행index가남아도명시적G1은FL을선택하도록매핑회귀도추가했다.
  실제안전성·10wall초성공은아직검증하지않았다. 일반CRAWL/게인/한계완화없음.

- 진단축약 REDcompile→GREEN4/45ms, 최종S+N빌드1분37초/S전체45시험14.6초/
  8패키지감사PASS. 동일fixture10,000회에서body7,553.75ns/168.33bytes,
  body+요약31,634.83ns/759.78bytes perstep. 실제RTF개선량의대체증거는아니다.
- 물리궤적을바꾸지않은실제Gazebo `68c22106-3776-473a-a607-5d907ec7bf4d`,
  resultUUID `1aa4fe76-28c4-492f-a535-ec73744ba6fe`: **FAIL**. SHIFT/unload전
  원생접촉상실을재현했다. FL22.924ROS초에원생pair수0/힘0/중심z.0196766m,
  직전22.922초는41.8794N/z.0200m, 다음22.926초는pair1/50.7362N이었다.
  3발하중이있어서상세조건(<3발)은아니며fullpair자료는없다. 원생요약의0pair를
  정규화결함이나실제airborne으로위장하지않는다. 정규화FL0은원생관측과일치했다.
  나머지3발의측정지지polygon에서현재CoM이안전하지않아kernel중단이정당했다.
- Crawl최초fault ROS22.938/wall879348958510ns `current measured support lost`;
  Carry최초fault같은ROS/wall879355833312ns `measured carry posture lost`.
  carry가선택한joint22.930초의팔qd.0331773/.0342230rad/s는기존.02를초과했다.
  원생촬영과노드관측벽시각이달라노드실행순서를물리인과로대체하지않는다.
- 이번IMUframe은통과했고정적RTF.6623(직전fullraw.6510)이었다. 축약만으로
  전체RTF/접촉문제가해결되지않았으며동일최종전수검증도아니다. 전체sensor freshness/
  contact support/carry/normalexit실패는그대로남겼다. STOPPED/runtime_exit=false,
  deactivate/typedterminal/소비자/relay정리성공/native0/launch0/relay0/reaped/noforce/
  residual[]보존. 원본79runtime소스ZIP `task8-control-clock-68c22106.zip`
  19,366,426bytes/SHA256`deb4cce131f73fa1aaecd0bfb69f0cf1c3fd014aa7beae6a53de8d70e60884bc`.
- 다음물리단일변수실험: G1에서만같은형상/CoM목표를sqrt(2)배시간에실행해peak
  가속도.05m/s²(기존상한.1의절반)로줄인다. 일반CRAWL/게인/limits/10wall초는
  유지한다. 참조의수학회귀RED1/10.16초→관련회귀진행중. 접촉단절이줄어드는지
  검증할가설이지확정원인/수정완료가아니며,전처리병행후보는동시에구현하지않는다.

- 판단경계 수정본 N설치22.8초/8패키지감사PASS 후 실제Gazebo
  `8b101e20-537a-447a-bab7-0921b79ab10c`, result UUID
  `6f82cbfa-02c3-4d31-aee0-22a9cce180e4`: **FAIL contact_calibration**.
  이번에는 음수age/support상실이 최초실패가아니라 원래10wall초의교정deadline이었다.
  요청ROS20.940/wall623871522699ns→최초faultROS27.254/wall633876319704ns.
  SHIFT의unload_start23.006초, 원본restz.0167551→목표z.0252551로8.5mm를
  .002m/s에가깝게계속진행했다. 따라서몸체settled때문에자주멈췄다는가설을지지하지않는다.
  실제FLforce<2N은비동기probe기준끝직전이고5mm실제lift는없었다. 새verticalhelper는
  아직진입전이며 generic unload비용을포함한전체G1예산재검토가필요하다.
- 센서/접촉/기본물리/시계계약은통과했으나 IMU기준촬영22.760초1건이없었다.
  원생controls sequence1137→1140 사이1138/1139 packet누락이있고, 해당packet의
  2ms기준묶음에속한시각이다. gyro값을보간하거나인수항목을삭제하지않았다.
  contact 상세추가packet 평균32,763자/교정317packet,전체native_controls.json은
  114,821,715bytes였다. 이값만으로전송누락이나전체RTF원인을확정하지않는다.
- 별도읽기전용ECM fixture10,000회에서body기준경로7,136.96ns/168.33bytes,
  body+fullraw접촉경로96,186.89ns/1,210.78bytes per step이었다. 실제Gazebo
  CPU/RTF의대체측정이아니다. `task8-calibration-observer-cost.json/.sha256`와
  재현helper를남겼다. 다음은정상시요약/지지상실시raw상세로진단payload만줄이는
  TDD이며, 필수gyro/접촉원생시각·50Hzpacket/실제인수조건은그대로다.
- measuredSTOPPED/runtime_exit=false는유지했다. deactivate/typedterminal/소비자/
  relay정리는성공했고native0/launch0/relay0/reaped/noforce/residual[]였다.
  원본79runtime소스·실행ZIP `task8-control-clock-8b101e20.zip`32,933,779bytes,
  SHA256`b399a8e3cf269d0badb56f534a95ea14c9b6ef303a3a9b43acc30539783dda04`.

- 후속2ms raw접촉 계측은 누락함수compile RED→네이티브ECM/plugin4PASS19ms,
  sensors전체45건PASS15.6초/8패키지설치감사PASS였다. 기존50Hzpacket에batch하며
  제어·힘·접촉 판정·일반CRAWL게인을 바꾸지 않았다.
- 실제Gazebo `d1136df9-b6b0-4e4a-80a7-79378a5d30e6`, result UUID
  `0e0b1196-30e6-430c-a878-ba00fef4ca4f`: **FAIL**. 이번에는 물리support상실이
  아니라 교정 중 `calibration_carry:wall_age`로 먼저STOP했다(ROS24.002초,
  wall440194094423ns). 최초kernel fault는null이다. raw접촉은 이 정지창에서
  네발모두pair/하중이 있었으며 이전23d 접촉단절 원인을 재현한것으로 세지 않는다.
  최초분석기는first_fault없음을검출해파일생성을거절했고, 이후명시적`--first-stop`
  분석만 `contact-substep-postmortem.json`에기록했다(아래ZIP후추가분석).
- 이번 STOPPED/deactivate/typedterminal/소비자·relay·native/launch0/reaped/noforce/
  residual[]는 확인했다. 원본result의normal_runtime/enginecheck는false로보존했다.
  정확한79runtime소스·원본고정ZIP `task8-control-clock-d1136df9.zip`27,712,222bytes,
  SHA256`6cf9e5d5b85d7414f5943f9fb732e53b08599c4a893c03b6ceae1b8e9248fbe1`.
- 첫stop에고정된carry는23.988ROS초/receipt440163880161ns(판단보다30.214262ms앞)
  로유효했다. tick이sensor bundle을선택한뒤교정carry에서다시선택하는경계가있었다.
  판단이후새수신을같은ROS시각으로평가하면음수wallage로실패한다. 기존API최소회귀
  `task8-calibration-negative-age-red.log`에서동일reason으로1FAIL11.90초를재현했다.
  실제거부후보owner receipt는기존실행에기록되지않았으므로독립probe시각으로대체하지않는다.
- 수정: Inbox/guard선택은고정ROS/wall cutoff를사용하고tick은carry/물리/firststop에
  같은bundle을사용한다. 늦은후보원본receipt보존/다음tick평가/200ms만료/중복lease금지/
  원래fault의고착은유지한다. API경계RED8/기존3PASS14.24초→관련ROS26PASS47.53초,
  보행·교정·PythonMuJoCo component·추가만료회귀60PASS57.63초. 전체N/실제G1아님.
  `task8-calibration-decision-native` 설치감사후새고정소스실측으로진행한다.

- 사용자에게 교정 전용 lift-return/시간 예산 재설계·검증을 승인받았다. 일반 CRAWL
  궤적/게인·10wall초·기존실제5mm/고유3촬영·속도/하중/안정화 기준은 유지했다.
- `calibration.py` pure reference RED10→GREEN10/9.82초. 통합 RED3/기존1PASS는
  기존19.253mm 보행 bump·하중 해제 확인 중 목표 정지·원본요청 예산 보고 누락이었다.
  수정 후 관련48PASS64.90초, Python MuJoCo3.3.7 component 포함26PASS47.95초.
  실제ROS/C++MuJoCo3.12 G1 또는 전체13.5 성공 증거로 혼동하지 않는다.
- 더 낮은 설정 속도.001m/s가 초기 해제.002로 덮이는 결함 RED1→seek=min(speed,unload)
  수정. 교정 phase origin/잔여예산 기준 시각도 RED 각각1→관련22PASS29.77초로 검증했다.
- 첫 실제Gazebo `5b47123d-fa60-4558-a58a-8a8ee1053847`, result UUID
  `6c4ecc65-e2a8-44b9-ba78-58571c201066`: **FAIL**, measured_startup에서
  `guard:wall_age`202.236736ms. 교정 전용 경로에 진입하지 않았으므로 궤적의
  성공·실패나10초 완료를 판단할 수 없다. 독립probe는 실패20.095422ms 전
  새guard2.712초를 받았으나 owner선택은2.548초였다. 최초fault null/stop은guardwall.
- 이 실행은 모든 정리 단계(STOPPED/deactivate/액션 drain/소비자·relay·native/launch0/
  회수/강제정리없음/잔여[])를 확인했다. 전체 필수검사 FAIL은 그대로 보존했다.
  원본79runtime소스·준비장면·실행/시험/설치 고정본 `task8-control-clock-5b47123d.zip`
  3,017,534bytes/SHA256`6258edddaa5382c3ce5ea6ba3d0edad3c54516c0cc827277037b64837f11d510`.
- 원인은 상태 피드백 중guard구독만 default제어 그룹/모델잠금에 남은 경계로 좁혔다.
  실제DDS RED1/3PASS13.36초→같은sensor_group/짧은inbox잠금, selection/해석은
  제어 소유자에 남김→관련26PASS60.35초. QoS/주기/200ms 한계·토픽/명령 소유권은
  바꾸지 않았다. 원본 callback-entry receipt를 보존하며 cleanup/first_stop snapshot도 보호했다.
- 후속 소스N설치17.5초/8패키지 감사PASS. 실제Gazebo `23d7439a-9574-4cee-aca4-5363e868e634`,
  result UUID `b8d73a50-d43b-4992-a22e-1c8c00f3d66b`: **FAIL contact_calibration**。
  SHIFT 중 ROS25.410초에 `current measured support lost`. 선택된25.404초 접촉은
  `[41.7091,41.5385,0,0]N`이었다. unload/새 vertical helper는 아직 시작 전이다.
  따라서 새 들기·복귀 궤적을 실제 검증했다고 표시하지 않는다.
- 접촉력0은50Hz 보존창에서 단일 고유 촬영이며 전후 rear하중은 약33–35N이다.
  무하중시 fallback인 rear발 중심z는.0197729/.0197763m로 반지름.02m보다 낮다.
  이것만으로 실제 들림·관측 결함 중 하나를 단정하지 않는다. 원생 비포화P-law로
  추론한12다리 목표의50Hz 최대 차분속도.1028765rad/s; callback/정확한2ms명령
  이력으로 위장하지 않는다. `contact-loss-postmortem.json`은 판정 후 추가 분석이며
  먼저 고정한ZIP에는 포함되지 않는다. 원본FAIL은 변경하지 않았다.
- STOPPED 실측 실패/runtime_exit=false를 보존했다. deactivate/액션 terminal drain/
  소비자·relay종료는 확인했고 native/launch/relay실제exit0, reaped/noforce/residual[]였다.
  모든프로세스0을 정상 물리 정지로 바꾸지 않는다. 원본79runtime소스·증거ZIP
  `task8-control-clock-23d7439a.zip`15,053,721bytes,
  SHA256`ac58e7c7db9d8d3a864e08f5b14c8ab1456081ccabe9bc4036d5beb2a192ebc2`.
- 다음 판별은 원본2ms post-step의 raw접촉 pair/깊이/wrench/발중심을 기존50Hz
  native진단에 batch하는 읽기 전용 계측이다. 접촉 필터·임계값·일반CRAWL게인·
  10wall초를 바꾸지 않는다. 새 actual 실행은 설치 감사/소유정리 후에만 진행한다.

## 2026-10-24 수정본 전체 회귀 및 MuJoCo 기본 경로

- 고정 수정본 navigation385PASS324.10초(`task8-control-clock-mailbox-full.log`), sensors45건(CTest wrapper포함)PASS10.7초(`task8-control-clock-mailbox-sensors-final.log`), 선택8패키지 소스/설치 감사PASS. 마지막 검증에서 재빌드/런타임 수정 없음.
- 동일78runtime 소스의 새 MuJoCo `c1ae8cd3-a240-4145-88bc-0cfd719a4033`, result UUID`de49988a-170c-48b7-9209-9d681fe7da92`: 기본native/single_worker G1 **23/23PASS**. 실제typedterminal/physicalsettle/IMU810고유·누락0·최대오차.0031418598rad/s/lift57고유. engine/runtime/launch0, receiverjoined,parentreaped,noforce,residual[]. relay100 또는G2/Nav2 성공으로 세지 않는다.
- 소스+MuJoCo 원본/준비 장면/최신 전체회귀/계측+Gazebo 시간예산 후분석을 `task8-control-clock-mailbox-mujoco-regression.zip`11,214,240bytes,SHA`089541abbb20c33c3f44fa9ca0ef316b01493e867279ddbcb544c848dc17a338`에 보존. 실행과 현재 source manifest 일치/member 해시 재독 검증. 원본 삭제 없음.
- Gazebo 후분석 최초5mm lift9.404706273wall초/최대lift.0102151m. 센서 비동기 후분석이며 정확한 owner replay가 아니다. 당시 G1 전용lift-return 제안은 사용자 답변 대기였다. 이후 승인·진행은 위 최신 항목에 기록하며, 일반CRAWL게인/10wall·실제lift·속도·하중·settle 한계는 유지한다.
- 작성자 자체 검토: model→mailbox 잠금 순서/ingress에서Machine 직접변이 없음/기존Clock구독하나/원본receipt/최초fault와publish경계/정상종료 의미를 재확인. 서브에이전트나 독립리뷰를 사용한 것으로 표시하지 않는다. 전체13.5 미완료, main/PR/push 없음.

## 2026-10-24 메일박스 격리 실측 — 이전 센서 실패 미관측, 전체 인수는 FAIL

- actual44a97d81의 소유자 contacts wall208.579433ms/clockread36,561ns/독립 ingress 정상에서 최소 DDS 재현으로 default 제어 그룹+모델 잠금 병목을 판별했다. clock은 통과/contacts는 실패(1FAIL/2PASS11.69초), malformed input 경계1FAIL11.92초를 먼저 보존했다.
- relay100 검증 모드만 별도 센서 그룹/메일박스 잠금을 적용했다. 모델·라이프사이클·모터 발행은 제어 소유자 하나이며 오류 latch 확인과 최종 발행을 같은 메일박스 경계로 묶었다. native 기본 그룹/단일 실행기·촬영/시계·50Hz·안전 수치는 유지했다. 관련31PASS68.93초+N설치18.9초+8패키지 감사PASS.
- 새 실제 Gazebo `5f2a8463-2ae6-4bdd-acef-50e28e853a48`, result `3a2522c8-6905-4254-a873-6452a5554e6d`: 기존23+1 모두 유지, 전체FAIL. 정적/실제 carry terminal/settle/센서/접촉/발 lift/IMU/clock 통과, 교정10wall초 안에 착지/settle 미완료. controller 최초fault/stop null, 마지막CALIBRATING/SWING. 이전결함의3회 연속 성공이나G1완료가 아니다.
- 시계4020고유/최소10.134392ms/최초receipt→발행최대23.636744ms/4개MotionState양의stamp lineage누락0. 교정8.2ROS/10.1205wall(RTF.8102), Crawl94.00%/17threads. 정적9.98ROS/12.6246wall(RTF.7905), Crawl91.44%. CPU 개선 완료 주장 없음.
- STOPPED/deactivate 미확정FAIL을 유지하면서 consumers stop/relay ACK+actual0/native1140actual0/launch0/parentreaped/receiverjoined/noforce/residual[] 확인. 최초 종료 실패를 성공한 PID 반환으로 대체하지 않았다.
- 실행/78소스/준비 장면/시험/설치 고정본 `task8-control-clock-5f2a8463.zip`20,149,669bytes,SHA256 `3979b0af242b5d4b54ac8c884928a5805e471dddb063ae6e5d90d7dfe2447b62`; 원본은 삭제하지 않았다.
- 별도 CPU fixture inherited1.094ms/tick vs BLAS1 1.072ms/tick, 양쪽3threads. 실제 CPU 병목을 BLAS 탓으로 단정할 수 없어 스레드 설정을 바꾸지 않았다. 원본 `task8-sensor-cpu-characterization.json`은 물리 판정이 아니다.

## 2026-10-24 승인된100Hz 중계 실험 — 첫 실제 실패 보존

- 사용자가 고수준5개 노드 검증 전용 중계를 승인했다. native 기본/원본 엔진·TF·센서·
  probe 시각/50Hz steady 제어/200·300ms 원래 계약은 변경하지 않았다.
  source/rate/owner/close TDD→관련44통과→동결N366·S42보고(CTest wrapper포함)통과,
  선택8패키지 설치 감사 후 첫 실제Gazebo를 실행했다.
- `925d70ff-642d-458d-b34c-619248b18ab8`, result UUID
  `2fba0266-f5ff-44a2-9f52-eb0591f6c690`: 전체FAIL. 첫4ms 전달 뒤 시동 중200ms
  중단을 운전 손실로 간주해 중계가 고착됐다. JSB 활성화 전이며 carry/stand 단계에
  도달하지 못했다. CPU 개선이나 기존 물리 결함 해결을 판단할 수 없는 실행이다.
  accepted inputs1로 callback 부재를 단정하지 않는다. 실제 graph는 정확히5개였고
  relay PID1156/start127768/exe·lib SHA를 확인했다. native PID1140 exit0/launch0,
  noforce/reaped/residual[]지만 relay1·STOPPED 미확정이라 정상 필수 검사는FAIL이다.
- 원본77source·scene·실패·검증을 `task8-control-clock-925d70ff.zip`에 보존,
  13,187,215bytes/SHA949c2f1f2249a58826b8efb0f763608763a7818ba6c29fb0b7cf9fb9009ffa46.
  모든 member 재독 해시 확인. 원본/native원본도 유지. 기본 경로로 되돌려 성공 실행만
  고르거나 중단 시간을 늘리는 조치는 하지 않았다.
- Ruling: 원본 양의 첫 tick을 운전 활성으로 취급하지 않는다. 기존 StartupManager가
  fresh센서/guard/실제claims 뒤, 다리 활성화 전에 one-shot clock arm한다. 원본 receipt
  200ms 기준은 arm 때도 검사·갱신 금지. ACK 뒤 readiness 재확인. 운전200ms 고착·
  시동45s·재시도 금지 유지. bootstrap에도 source/rollback 오류 고착은 항상 적용한다.
  최소RED bootstrap1/기존8통과→10통과, 실제 startup RED2→8통과, unarmed판정RED1,
  수정 관련46통과60.58초. 현재 전체N 재검증은 아직 하지 않았다.
- 직접 ROS 시험에서 설치된 이전 lib가 build RPATH보다 먼저 로드된 도구 오류3통과/
  2실패를 보존했다. `~/arm`·`armed`가 없어 판별. 도구의 해당 프로세스만 build-lib
  우선/ldd기록으로 수정. 실제 설치 감사 경계는 유지한다. 새 동결 설치/센서 전체
  회귀/감사 중이며 다음 실제 실행 전에는 다른 엔진을 시작하지 않는다.

## 2026-10-24 재개 — native 판정 보완과 IMU 가설 교정

- 마지막 엄격 판정기로 `task8-strict-reference-navigation-full.log`
  **343passed/315.05초**. S colcon test-result28건(CTest wrapper포함)/실패0와
  frozen8패키지 감사는 별도 범위다. wholeCh13/13.3/13.4matrix/G2 성공으로 합치지 않는다.
  실패 원본 로그 `task8-gazebo-imu-history-red.log:60`의 pytest diff공백은 의도적으로
  보존했다. 로그를 제외한 staged 코드/문서 diff--check를 별도 확인한다.

- 1차 전체N 회귀 `task8-instant-reference-navigation-full.log`341passed321.89초,
  S28native통과와 합해 해당 범위369건이었다. 이후 자체 리뷰에서 동기 캐시 fallback을
  발견해 별도 RED2실패9.21초→관련62passed23.87초로 닫았다. 실제 f5 입력의 strict
  postmortem도410/누락0/오차0.0000342422를 유지하고 기준 삭제 음성을 거부했다.
  원본 FAIL과 그 시점 검증기/source hash는 변경하지 않았다.
- f5 조건부 역산 사후 분석:44native records/힘 포화0/팔목표 최대 오차
  1.35525e-20rad. arm2속도0.02610445,arm3속도0.02364773. 다리 역산목표20ms 차분
  0.00150797rad, odometry기반world속도 차분 가속도최대0.186899m/s². 이 값은
  모든 native2ms 명령 또는 순간 IMU가속도라고 부르지 않는다. `carry-excitation-analysis.json`
  원본 설명을 유지하며 팔 목표 소유권보다 base excitation 가설을 우선 검토한다.
- 한 실행의 정확한 보존본 `task8-gazebo-instantaneous-f5eff9bc.zip`14,278,979bytes/
  SHA256 `8afa141de8e1ef8a4fe0e5fc813913eaed38fa5cdc37366c3b13ebc97177c17c`.
  source71·실제FAIL/evidence/scene·시험 로그를 ZIP member별 재독 SHA 확인했다.
  원본/과거 실패/native 원본 삭제 없음. ZIP 후의 strict 순수 판정 변경은 현재 Git과
  별도 `task8-strict-native-reference-f5eff9bc.json`에 구분했다. 상세 복원/리뷰 안내는
  `Ch13/docs/SECTION_13_5_NATIVE_REFERENCE_REVIEW_KO.md`다.

- 새 실제 GZ `f5eff9bc-cc1a-49f1-a3d9-fc158b9b43db`는 **전체 FAIL 유지**:
  contact_calibration 중 carry `measured carry posture lost`, raw팔최대속도
  0.0261044473rad/s >0.02, 실제 lift0이다. 사라진 callback으로 추정하지 않는다.
  순간 ECM 기준은 **IMU410고유 capture/누락0/최대오차0.0000342422rad/s**로 통과했다.
  native scalar force538records/라이브러리 매핑/센서 신선도 등도 통과했지만 G1
  완료가 아니다. `joint_tf_ownership=false`는 성공 끝의 owner_attestation 단계에
  도달하지 못해 독립 graph 확인을 완성하지 못한 상태이며, 새 충돌의 증거가 아니다.
- 실제 종료: native관찰기 stopACK true → pause true → nativePID1141/부모1138
  **같은 PID exit0**, runtime/engine true, launch0, receiver joined, noforce/reaped/
  residual[] 확인. 실제 engine정리와바이트복사22파일의 `storage-copy-ledger.json`을
  확인한 뒤 다음 시험으로 넘어갔다. native원본도 보존했다. 추가clock계측기 없음,
  scopedLP2는 직전비교와 같으며 기본 채택 아님. source/설치 manifest는 해당UUID다.
- 순간기준 첫 build는 28native tests 통과했으나 build도중 REUSE수정 때문에 설치
  감사가 실패했다. 이를 무시하지 않았다. frozen 재build87초/native28 tests0실패/
  8패키지감사 통과 후 위 실제실행을 했다. 평균기준거부 포함 Python49passed27.75초.

- `task8-gazebo-controls-verdict-red.log` 누락 API15실패 뒤 GREEN35passed/13.53초.
  기존 be485/5dbc/571의68/851/539개 native packets를 새 메타데이터 검증기에 대입해
  모두 일치했다. 각 `native_controls_postmortem.json`에 입력·검증기SHA와 제한된 범위를
  적었다. 원본 result/manifest/실패는 수정하지 않았다.
- 운반 회귀 첫 RED는 test import 누락10실패였다. 이를 고친 confirmed RED10실패는
  실제 누락된 admission API였다. `task8-carry-owner-verdict-green.log`51passed/24.64초.
  이제 독립 raw 관측이 정상이어도 소유자 first_fault/FAULT/불명 결과/모델·세대 불일치가
  있으면 세부 carry 판정도 FAIL이다. 실제571의 raw만 PASS였던 맹점을 재현했다.
- GZ exact odometry history 첫 RED2fail7pass → 관련64passed/33.18초. **불충분한
  가설로 판정**: 5dbc는682개누락0/최대0.01930168이지만571은435개누락0/0.04321401.
  후자의 carry raw true/owner false도 확인했다. be485는 정적10초 미달 및 owner wall-age
  fault로 계속 FAIL. `capture-and-owner-postmortem.json`의 hash는 그 시점 검증기에
  해당하며 새 엔진 인수가 아니다. 뒤의 원본 소스 조사로 odometry는 평균, IMU는
  순간 component임을 확인했고 odometry를 IMU 정답으로 허용하는 분기는 철회했다.
- `task8-gazebo-instant-reference-red.log`2fail7pass/11.88초는 순간 기준 미지원 및
  평균 기준의 잘못된 허용을 각각 검출했다. native C++ 첫 RED는 헤더 위치 오류였고,
  confirmed RED는 `read_gazebo_body_reference` 미선언 컴파일 실패다. runtime assertion
  RED라고 부르지 않는다. 새 구현·실제 재측정 전에는 해결됐다고 선언하지 않는다.
- `task8-gazebo-observer-stop-red.log` API부재6실패 → GREEN17passed/8.59초.
  기존 stop service로 관찰기 송신부터 막고 pause/server stop을 수행한다. ACK는 종료
  증거가 아니며 실제 native PID exit0/회수/강제없음/잔여없음을 계속 별도 요구한다.

## Gazebo 시간 예산 후속 판별 — checkpoint abcc057 이후

- description 직접 PID 빌드44.1초/확장8패키지 source-install 감사 통과 후
  `5dbc1a36-6153-4fc8-83c6-3cea70449459` 실제GZ 실행:
  launch1141 → **직접 native child1144**, 실제3library 매핑도PID1144이며 같은PID의
  launch 종료 로그0을 수집했다. launch0·runtime exit true·강제 없음·회수·잔여[]이다.
  `/bin/sh` 종료나 stop ACK를 native 정상 종료로 대신 세지 않았다. 전체 G1은 여전히
  **FAIL**(10wall 교정 시간; IMU 비동기 cache 대조 오차0.02350rad/s도 남음)이다.
  native 기록 helper의 기존 `no_runtime_or_model_changes`는 helper가 코드를 편집하지
  않는다는 뜻이었다. 이 실행은 직전과 달리 description/script source가 바뀐 직접PID
  회귀이며, 실제source manifest가 이를 기록한다. 이후 helper metadata는 `purpose`와
  `driver_does_not_edit_runtime_or_model`로 명확히 구분한다. 원본 FAIL/ledger는 수정하지 않는다.
- 원생 library 검증 TDD `task8-gazebo-library-attest-red.log`: API 누락9실패8.42초.
  파일 경로·device/inode·실제 bytes SHA와 동일 PID/PPID/PGID/start tick·명령을 결합하고
  전후 identity/파일 변경을 거절한다. inode/device 교체 사례를 추가한 관련 회귀
  `task8-gazebo-library-attest-green.log`: **27통과10.85초**. 이는 fixture 산술 검증이며
  실제 mapper 성공으로 대체하지 않는다. 다음 실제 실행에서는 초기 READY 직후와 최종
  성공 구간의 매핑을 별도로 수집한다. source/설치8감사를 재확인했다.
- CPU 가설 격리 domain219 진단: 최초 도구는 Jazzy에 없는 qos_profile_clock import로
  시작 전 실패했다(엔진/자식 없음). 공개 QoSProfile로 교정했다.
  `clock-cost-diagnostic-2e76ac26-...json`의53.1%/17.5%는 **프로파일러 포함** 값으로
  운영 비용으로 인용하지 않는다. 오버헤드를 분리한
  `clock-cost-diagnostic-956e5e3d-085d-4fc1-9f3e-816d4c3c38bc.json`은 무계측3초에서
  500Hz idle ROS 수신19.2515%,50Hz6.50234%(one-core process CPU)다.
  계측 구간의 callback1500/150회로 주기 차이를 확인했지만 이는 합성 clock fixture이며
  실제 엔진 입력 빈도·전체 실패 근인을 증명하지 않는다. 프로파일 함수 시간은 계측
  오버헤드/코루틴 집계 영향을 포함하므로 절대 CPU 귀속으로 사용하지 않는다.
- 추가 Python 고주파 수신기로 실제 엔진을 더 부하 주지 않도록 읽기 전용 C++ clock
  계측기를 별도 사용자 build 영역에 만들었다(로봇 runtime 패키지/underlay 수정 아님).
  `clock-rate-fixture-6993765f-d4af-4eaa-9309-ae142404218f` domain219에서2458메시지/
  499.990Hz·publisher1·rollback0을 확인했다. 이것도 native 엔진 증거가 아니다.
  다음 실제GZ의 정적 구간에서만5초 계측하고 원본stamp 간격/GID·실행 binary/source SHA·
  진단 프로세스 CPU/종료를 기록한다. 시계 relay·속도/가속도/시간 상한 변경은 아직 없다.

- native 기록 비교 `571bdbe2-1fad-47fa-b209-fab9f96afe49` **FAIL**: SHIFT에서
  실제 carry arm2속도0.023103694rad/s>기존0.02. 동일 owner 선택joint stamp/판정ROS
  22.328초, arm3속도0.01841648 등 다른 팔은 기준 안이었다. 감쇠/게인/시간/힘 기준
  변경 없이 재발했으므로 저장 위치만의 해결이 아니다. 정적 관측9.98ROS/13.214146wall,
  RTF0.75525는 직전0.67148보다 높았지만 새 효과를 확정할 반복 인수는 아니다.
  calibration은0.78ROS만 관측돼10wall 완료 예산 비교는 중도 실패로 검열됐다.
  원본 native evidence20파일을 저장소로 byte/SHA 일치 복사했고 원본도 유지했다.
  runtime/launch0·강제 없음·회수·잔여[]·probe join 확인.
- `carry-excitation-analysis.json`: 실패 전후46 native snapshot 모두 비포화이며
  P법칙으로 **추정한** 팔 목표의 carry 목표 대비 오차 최대3.4e-21rad다.
  명령 토픽을 실제 native 명령으로 위장하지 않았으며 직접 command 관측은 아니다.
  다리 추정 목표 최대20ms차0.00200065rad, 회전 basis를 WORLD로 맞춘 몸체 속도
  차분 최대0.180245m/s²를 관측했다. 이는 실제 IMU 가속도나 모든 물리 스텝의 추적이
  아니므로 그 자체로 근인 확정/인수 판정에 사용하지 않는다. 단순 팔 목표 상실 가설은
  뒷받침되지 않았다. 무조건 gain 증대/속도 상한 완화는 하지 않는다.
- Task8 종료 출처 보강 TDD: `task8-direct-gazebo-child-red.log` 직접 child 없음으로
 1실패11.34초; `task8-description-runtime-audit-red.log` source/install 감사 누락4실패
 8.27초. navigation opt-in만 shell=False argv 실행으로 바꿨고 공식 설치 helper를
 import해 plugin/resource 환경을 보존했다. 첫GREEN은 테스트가 잘못된 공개 API 위치
 Executable.shell을 읽어1실패21통과17.69초였다. 올바른 ExecuteLocal.shell로 고친
 관련 회귀 `task8-direct-gazebo-child-fixed.log`는 **23통과15.80초**.
 기존13.4 경로 보존, 공백 포함 world 단일 argv, 변경/누락/소스 symlink 설치 거절을
 함께 검사했다. 실제 PID 매핑+exit 수집은 아직 실행 전이며 description 재빌드/감사 중이다.

- 로컬 `abcc057b8a2317d6034092abf15b969a270a2383`은 WIP 체크포인트이며 push하지
  않았다. 기존 Task8 source/tests와 MuJoCo3연속 G1 PASS 요약·69source 바이트 보존본을
  포함한다. 최종 Task8/G2/Nav2 완료로 표시하지 않았다. 사용자13.4교육 문서는
  stage/수정하지 않았고 원본 실패 raw도 로컬에 모두 유지한다.
- 설치8패키지 감사를 재확인한 뒤 `2e09eeac-7f06-4ff8-ae72-49b66f980472` 실제GZ를
  LP_NUM_THREADS=2 프로세스 한정으로 실행했다. native PID1131/start6676의 실제
  환경과3library 매핑을 수집했으며 root 최대59threads였다. **FAIL**: 원래10wall초
  교정 제한에 도달했다. 이 실행에서는 carry READY/first_fault=null이지만 이를
  과거 간헐 팔 속도 결함의 해결로 단정하지 않는다. 관측 정적 구간9.98ROS/14.862648wall,
  교정 구간6.478ROS/10.135101wall로 RTF0.67148/0.63916이다. 이전default 약0.69보다
  개선을 입증하지 못했으므로 LP2를 기본으로 채택하지 않는다.
- 최초 제한 도달 보고서: ROS24.008초, CALIBRATING/SHIFT/FL unload, unload시작19.650초,
  경과4.358초·명령 높이8.684mm 증가·FL 하중2.33117N으로 기존2N 미만 조건 미충족.
  지지·속도 조건 없이 시각만으로 발을 들지 않았고 기존 max10mm/2mm/s도 유지했다.
  all process0·강제 없음·회수·잔여[]·probe join 확인. STOPPED 미확정으로 runtime
  정상 인수는 실패다. wrapper exit와 service ACK를 실제 native PID 정상 exit 증명으로
  대체하지 않으며 direct native exit 증거 보강은 여전히 미완료다.
- Ruling: `_validate_limits`의 unload_speed_mps 상한0.002를 올리거나10wall 기준을
  늘리지 않는다. 다음 판별은 같은 LP2/소스/설치/모델에서 **실행 기록 위치만**
  `/home/jinho/ch13_5_completion_.../evidence`로 바꾼다. 준비 장면은 기존처럼 저장소
  evidence에 두고 실제 운전 중 raw/system/process/driver 기록만 native 영역에 쓴다.
  종료 후 원본 native 파일을 그대로 보존하고 새 저장소 UUID로 byte/SHA 일치 복사한다.
  `storage-copy-ledger.json`은 실제 command root와 복사 출처를 명시한다. 위치 효과의
  실험이며 runtime 수정·driver 변경·자료 제외·제어 한계 완화가 아니다.

## 최신 판별: 검사기 수신 소유권과 IMU 촬영 대조

- 최신 navigation 전체 회귀 `task8-imu-capture-navigation-full.log`:
  **283 passed/303.63초**, 직전 원생 센서27건도0error/0failure/0skip이다.
  이전294건의 stale 기대값 실패를 소급 수정하지 않고 새 전체 실행으로 확인했다.
  이 합계310건은 navigation+센서 범위이며 Ch13 전8패키지/기존13.3·13.4 전체 행렬
  재실행을 완료했다는 뜻이 아니다. runtime 수정 없이 문서 REUSE의 CRLF 혼입만
  LF로 정리한 뒤 diff whitespace 검사도 통과했다.

- **MuJoCo G1 수정 후 3회 연속 PASS 확정**:
  `6f390aa7-0b81-4f3b-9711-18de43e2b9dc` →
  `296cc582-b465-42a7-bda5-c941cc5d4f64` →
  `5fab26df-0a01-486e-9f25-83f7d3ccfbe7`, 각각23/23 required checks true.
  추가 두 실행 IMU720/764고유 촬영·누락0·최대오차0.00369906/0.00300633rad/s,
  lift56/54고유 촬영이다. 세 실행 모두 source_manifest와install_manifest 전체 및
  실제 원본 source bytes SHA가 동일했다. 모든 engine/runtime0·join·회수·강제 없음·
  잔여 없음 확인 뒤에만 다음 엔진을 시작했다. 첫 실패 시 중단하는 드라이버의
  `task8-imu-reliable-g1-confirmations.json` passed=true이며 원본FAIL들은 그대로다.
  69개 정확한 source bytes를 검증해 `task8-imu-reliable-frozen-source.zip`
  (188698bytes/SHA256 f25102c7d7202b21de3dac5fc0271b5c944c5c663569163fd4ed23d46e2bf578)
  으로 보존했다. **이는 MuJoCo G1만 통과한 것으로 G2/Gazebo/Nav2/Task8 완료가 아니다.**

- 신뢰 전송 후 원생S rebuild1분56초·27건/0error/0failure/0skip·8패키지 설치 감사
  통과. 실제 MuJoCo **`6f390aa7-0b81-4f3b-9711-18de43e2b9dc` G1 23/23 PASS**.
  IMU760고유 capture/기준 누락0/최대오차0.0029212526rad/s<기존0.02,
  실제 단일 발 lift51고유 capture, 수납·typed terminal·native provenance·TF 소유권·
  정상 runtime/engine 종료 모두 통과. worker와receiver join true, launch와engine0,
  forced_cleanup=false·parent_reaped=true·residual=[]를 별도 teardown에서 확인했다.
  기존 실패(d0/7c3/6a 등)는 제외하지 않고 보존한다. 이 PASS는 G1 MuJoCo 1회이며
  G2·Gazebo·Nav2·최종 전체 회귀의 대체 증거가 아니다.
- 추가2회는 source_manifest 전체·설치 manifest·실제 source bytes SHA를 앞선PASS와
  대조하며 순차 실행한다. 첫 FAIL/불일치/정리 미확정에서 중단하고 자동 재시도하지
  않는 `confirm-mj-g1.py`를 사용한다. 최종 판정은 새 confirmation JSON에 보존한다.

- 진단 신뢰 전송 TDD: `task8-imu-reliable-native-red.log` 실제 pluginlib/ROS에서
  RELIABILITY 비호환 경고와 controls.empty로1실패3.554초. 수신기 endpoint 회귀
  `task8-imu-reliable-probe-red.log`도 BEST_EFFORT로1실패11.12초다.
  양단 진단만 RELIABLE/KeepLast100으로 변경했다. 첫 관련GREEN은1실패33통과28.39초:
  Jazzy RMW graph가 history depth를0(미제공)으로 보고해 테스트 가정이 잘못됐다.
  해당 관측 불가 assertion만 제거한 `task8-imu-reliable-probe-fixed.log`는
  **34통과23.96초**다. source 계약의 bounded KeepLast100은 유지하며 센서/제어 QoS는
  변경하지 않는다. 원생 rebuild/27회귀/8설치 감사 후 새 실제 장면을 실행한다.

- 원생 동일 snapshot 구현 후 S빌드1분45초·**원생27건/0error/0failure/0skip**,
  선택8패키지 설치 감사 통과. 실제 `d0f25980-f841-4e5b-871a-ebc214d77cab`는
  다시 **IMU 하나만 FAIL**, 물리 lift/수납/typed terminal/정상종료 등 나머지 전부 true다.
  worker와receiver join true, engine/runtime0·강제 없음·회수·잔여 없음.
  `imu-reference-coverage.json`:757고유 IMU 중751은 정확히 같은 native capture와
  대조됐고 최대오차0.00729323rad/s/한계 초과0개다. 나머지6capture의 큰 진단 메시지가
  수신 기록에 없다. 센서 plugin은 같은 lease에서 IMU와 JSON을 함께 발행하지만
  진단 토픽도 best-effort였으므로 두 토픽의 동시 도착은 보장되지 않았다.
  누락6개를 삭제하지 않고 FAIL을 유지했다. 다음은 진단만 RELIABLE/유한 queue로
  바꾸는 실제 ROS 계약 회귀다. 센서·제어 QoS/시각/기준은 그대로 유지한다.

- fastFK 관련43통과50.05초, live 보고서5통과20.87초 후 설치 감사8패키지 통과.
  실제 Gazebo `82895c1e-f8b2-4587-ac52-5b22b8bcf961`은 정적10.002ROS/14.477wall초,
  SHIFT에서 팔2속도0.0281001/팔3속도0.0241314rad/s로 FAIL했다. owner 선택 관절
  stamp22.190/판정ROS22.194초이며0.02한계를 유지했다. 추가 gain 변경은 없다.
  전 프로세스0·강제 없음·회수·잔여 없음이나 STOPPED 미확정으로 정상 인수는 실패다.
- 실제 MuJoCo `6a94dda3-8179-4046-ac39-be556a090dab`은 단일 발 검증을
  9.932ROS/9.901917wall초에 마쳤고 실제 terminal/native 출처/정상 종료도 통과했지만
  frame1112의 여러 스트림 wall age약228–242ms 한 건으로 전체 FAIL이다.
  제어 소유자 fault는 없었다. 수신기와 부모 IO/프로세스 조회를 같은 executor에 묶은
  구조를 분리했다. 실제 ROS 관련20통과18.98초; 예외 고착·blocked callback join 실패
  자원 보존도 검사했다. 임계치 완화·outlier 삭제·자동 재시작은 없다.
- 다음 실제 MuJoCo `7c3d8a5e-0479-4b75-be72-b4ead8a6461e`: **IMU 하나만 FAIL**,
  나머지 required checks는 true다. 수납868고유 관측 최대오차0.019082rad,
  속도0.018871rad/s/그리퍼0.003115m/s, 단일 발 물리검증·freshness·typed terminal·
  native 관측/TF·정상 runtime/engine 종료 통과. receiver join true·exit0·강제 없음·
  회수·잔여 없음. 전체 FAIL 원본을 바꾸거나 성공 반복에 포함하지 않는다.
- `imu-alignment-analysis.json`: 독립 최신 cache의 IMU/body 시차34–54ms에서
  gyro오차0.02 초과4건. 최악31.412/31.446초,0.040626rad/s다.
  `imu-history-analysis.json`은 **인수 아닌 사후 가설**이며20ms내 선형BODY보간은
  752중314누락으로 채택하지 않았다. 모든752개는 원본 body history 안에 존재했다.
- Ruling: 같은 immutable snapshot의 free-root qvel 각속도를 gyro와 독립적으로 읽어
  기존 native_controls 진단에 넣고 exact capture로 대조한다. 촬영 header/epoch,
  .02rad/s 기준과 누락 실패를 유지한다. body 좌표를 WORLD로 중복 회전하거나
  sensordata를 정답으로 재사용하지 않는다. 신규 명령 소유자·engine 쓰기는 없다.
- `task8-imu-capture-red.log`: async positive case1실패/6통과13.04초.
  최소 검사기 수정 후 `task8-imu-capture-green.log`: 관련41통과22.69초.
  원생 회귀 `task8-imu-qvel-native-red.log`는 미구현 body_angular_velocity 멤버의
  컴파일 실패를 확인했다(실행 assertion 실패와 구분). 이어 원생 구현·빌드·전체 sensor
  회귀·설치 감사 중이며 실제 엔진 성공으로 아직 집계하지 않는다.

## 효율 개선 적용 후 단일 원인별 판별

- 실제최적화c948d056-0759-4224-a987-d74a1c23b10d: 새ELF3개의 실제mappedSHA·기본LP환경
  확인. 정적10.004ROS/14.6583wall(이전21.38wall), calibration6.694ROS/10.0618wall에서
  원래10wall초제한 실패. 그 시점CALIBRATING/SHIFT/FL하중해제 중이었고 최초fault/stop 없음.
  carry804고유관측 최대오차.0218639/속도.0103384rad/s, 그리퍼.000904m/s로 해당 구간의
  수납은 기준 안이었다. 전체G1은 실패다. process모두0·강제 없음·회수·잔여 없음.
  정적RTF.68491/crawl79.96%/guard61.00%/native143.31%onecore. 기준 변경 없이 남은
  실행 예산·하중 해제 단계를 분석한다. 최적화만으로 전체 완료라고 하지 않는다.
- c948운전 프레임 신선도를 전부 조사한 `frame-freshness-analysis.json`: scanwall_age1회,
  frame658/ROS16.412/ROSage112ms/wallage301.578094ms. 이 표본을 삭제하거나300ms한계를
  바꾸지 않는다. probe는 이미미래COM/일반sensor후보를 보류하므로 추정만으로 고치지 않는다.
- hotFK계산량 RED1실패2통과7.88초(일반4x4solve4회) → 관련43통과50.05초.
  검증된Rx/Ry/Ry URDF에만 해석적식을 사용하며 일반axis fallback·관절 한계·비유한값검사
  유지. 독립MuJoCo32자세·일반axis·기존물리/보행시험 통과이며 실제엔진 대체 증거는 아니다.
  오류가 아닌 제한시간 실패에서도 현재unload명령·floor를 볼 수 있도록 읽기전용 live보고서
  회귀를 추가했다(RED1실패10.49초). 현재 관련GREEN검사 후 새 실제 시험으로 진행한다.

- RelWithDebInfo 실제 빌드S3분29초/N18.5초/전체3분48초, 설치8감사 통과.
  고정gz1.2.20의 legacy hardware export API deprecation 경고는 빌드 로그에 보존했다.
  전체 회귀는 **294건/0error/1failure/0skip**: 유일한 실패는
  `test_nav_gazebo_position_system_binds_gains_without_changing_legacy_hardware`의
  옛calf500/arm3kv20 기대값이다. 현재calf750/arm3kv40 후보 literal로 교정한
  장면·정적 하중 관련9건은15.45초에 통과했다. 전체294 실행을 소급해 성공으로 바꾸지 않는다.
  frozen 최종 전체 인수에서 다시 실행할 예정이다. runtime 코드 변경은 없다.
- `native-optimized-build-provenance.json`에 실제 old/new CMake cache·target flags·ELF SHA,
  GCC13.3.0을 기록했다. 원래3개GZ target flags에는-O가 없었고 새flags는-O2 -g -DNDEBUG다.
  fast-math는 없다. byte가 달라졌으므로 새 actual mapping 및 실제 구동 결과가 필요하다.

- 실제82ffc55f-858a-44cb-b519-c9a06cf48956: mappedPID1183 환경LP_NUM_THREADS=2 확인,
  최대스레드59(이전71). bootstrapRTF.463/정적 일부2.528ROS/4.889wall이라 명확한
  속도 개선을 입증하지 못했으며 기본 설정으로 채택하지 않는다. 정적 구간guard:ros_age 실패,
  모든process0·강제 없음·회수·잔여 없음. 실제 guardstamp11.578초 > 로컬ROS11.576초로,
  과거250ms지연과 달리 미래2ms의 callback/clock 도착 순서였다. 임계치 완화로 숨기지 않는다.
- guard 회귀: 시험노드 참조 오기1실패11.38초 보존(원인 재현으로 세지 않음), 교정 후
  실제node callback/clock 분리RED1실패12.13초. 최대10후보 중 로컬ROS 이하 최신만 선택,
  header/최초receipt 유지·중복 갱신 금지·원래200ms 만료·inactive 준비 guard 검사 적용.
  첫관련6통과1실패27.02초는 옛 시험의120ms 즉시 만료 가정이었다. 마지막 유효 capture의
  실제200ms 만료를 기다리게 교정한 뒤 관련10통과36.76초. 실제 반복 인수는 아직 미완료.
- 빌드 병목 판별: 기존S CMakeCache의CMAKE_BUILD_TYPE/CXX_FLAGS 모두 비어 최적화 없음.
  Ch13 일반 사용자 native prefix에서만 RelWithDebInfo(-O2 -g -DNDEBUG)/빌드병렬2를 선택해
  S+N 전체빌드·8패키지 감사·전체 두패키지 회귀를 진행한다. 외부 underlay 변경이나
  fast-math/물리/힘/안전/카메라 설정 변경은 없다. 새 ELF hash로 실제 성능·결과를 다시 검증한다.

- 실제950a56ec-f016-4e0f-b6ed-f0deb9962eef: 분할 탐색 관련36통과66.75초,
  기준 고정 후5통과18.02초, N빌드22.1초/설치8감사. 오프라인20회 최대slice9.49ms,
  전체 중앙31.57ms/최대44.66ms; 목표·곡선 시간은 baseline과 동일하다.
  실제실패 직전16tick5.81–13.64ms, age위반이 아닌 팔1/2/4 속도 위반으로 실패했다.
  선택joint19.310초에서qd=-.02078356/-.03890714/+.03085482rad/s, 팔3=-.00131890.
  READYeterminal/위치 오차는 허용 범위였으나 이를 전체 수납 성공으로 집계하지 않는다.
  모든process0·강제 없음·회수·잔여 없음, 정상/전체G1 성공은 아니다.
- 원인 범위 갱신: arm3만 증대하는 접근은 전체 하중 이동 안정성을 해결하지 못했다.
  실제 몸체 속도차분31고유 관측 최대.1598m/s²(몸체basis 회전 보정 없는 범위 명시),
  내부 목표 곡선 .10m/s²와 실제 가속은 같지 않다. 다음 팔 게인 증대를 반복하지 않는다.
  950정적 구간은9.974ROS/21.323wall, engine143.27%onecore/71threads,
  crawl80.86%/guard54.10%였다. 이에 동결runtime/model의 다음82ffc55f는
  프로세스 한정LP_NUM_THREADS=2만 비교한다. 모든 안전 기준·카메라320×240/15Hz 불변,
  드라이버/시스템 설정 불변이며 실제 mapped PID의 선택 환경 키를 별도 증거로 수집한다.

- 실제149959a0-4fb0-44cc-ac36-3d8d11dcedb7: arm3감쇠 후보 관련8통과17.78초,
  N빌드21.9초/설치8감사 통과 후 실행. 첫SHIFT에 contacts:wall_age로 실패해 감쇠 효과는
  판정 불가다. 최초fault ROS18.354초, 접촉stamp18.284초/receipt424022331995,
  판정wall424228131181: ROS70ms/wall205.80ms. 직전tick173.879ms 이후 queued callbacks.
  모든process0·강제 없음·회수·잔여 없음. 성공으로 집계하지 않는다.
- 오프라인 계산 재생: 첫shift-cost-before는 설정 파일 로드를 포함했으므로 실제loop 비용으로
  쓰지 않는다. cached-config-before 중앙28.00/max34.33ms, profile의FK741회/CoM22ms/IK17ms.
  CoM 공통경로 캐시 RED1실패1통과10.31초 → 관련38통과68.31초. 변환은 한 측정 안에서만
  재사용하며 다음 측정에는 폐기한다. after 중앙28.95/max39.45ms, FK312회/CoM14ms/IK26ms.
  계산 횟수는 줄었지만 전체 wall 비용 개선을 입증하지 못했으므로 수정만으로 해결이라 하지 않는다.
- Ruling: coarse9점/binary8회 동일 탐색을 후보1개/안전 주기로 나눈다. 기존 센서·지지·owner·
  STOP 검사를 매 주기 우선하고 계획 중 기존 명령을 유지한다. 완성 후 곡선 시계를 시작하며
  STOP/FAULT는 탐색을 버린다. 새스레드/두번째명령소유자/age완화 없음. 추가 명목계획시간은
  기존10wall초calibration 예산 안에 포함한다. 계산량RED1실패2통과10.51초(한tickCoM14회)
  → 기존물리/보행포함36통과66.75초. 기준자세를 불변 복사한 최종 관련 회귀를 이어 실행한다.

- 실제626473a5-e032-4979-94c3-e6b59eb4fe75: 최초carry보고서 확보. READY 실패 판정
  ROS17.590초, 선택joint17.578초(12ms), 수신후19.3ms. arm3 q=-2.018997141870555,
  qd=.02803877186796927. 오차.018997rad<.03, 속도>.02이며 다른팔/그리퍼는 해당 한계 이내다.
  guard/crawl 모두 같은generation0/modelhash, 선택상태CALIBRATING. age/terminal실패가 아니다.
  정지3초 제한 내 STOPPED는 미확정, wrapper/runtime0·강제 없음·잔여 없음이어도G1FAIL.
  source21.4초 재빌드/설치8감사 및 nativePID라이브러리 수집 통과. 원본실패 보존.
- Ruling: 실제 실패626(원생 전체 시험 RED)를 기준으로 팔3 kv20→40만 비교한다.
  kp105/힘 한계·모델 질량·제어율·모든 인수 기준은 불변이다. 위치 강성은 오차 기준 이내이고
  하중 이동의 상대 속도 억제가 목적이다. 감쇠와 응답은 전체 연성 동역학에 의존하므로
  단순히2배면 무조건 성공한다고 주장하지 않는다. 새 양 엔진 physics/profile 해시로 재검증한다.

- 실제8fcaed13-3026-49ac-8550-b2339085192e: calf750 후보 N빌드28.6초/설치8감사 통과.
  시동·수납 READY·정적10초 후 contact_calibration에서 carry:measured carry posture lost.
  주변18.404초 native prephysics arm3 q=-2.0189842553,qd=.0219094796으로 기존.02초과지만
  CarryManager 동일 선택 입력은 아직 없으므로 원인 확정/재조정으로 뛰어넘지 않는다.
  wrapper/runtime0·강제 없음·회수·잔여 없음. filtered carry 평가 true를 전체 성공으로 쓰지 않는다.
- 최초 팔 실패 입력 보존: 실제ROS /report 회귀 RED1실패27.43초(KeyError:first_fault) →
  관련2통과25.37초. lock 안의 최초 selected cache를 깊은 복사하고 이후 입력으로 덮어쓰지 않는다.
  정지 실측이 실패해도 carry_failure_report.json을 먼저 확보한다. 임계치/제어/lease 변경 없음.
  다음 실제 Gazebo 1회에서 소유자 입력과 주변 native 관측을 연결한다.

- 고정 일반 사용자 Linux 영역 `ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b`를
  만들고 설치607파일 해시를 대조했다. source는 원래 저장소에 두며 외부 원본은 불변이다.
  navigation만 재빌드23.0초/후속21.4초와 실제 선택8패키지 감사를 확인했다.
  기존 audit wrapper가 Windows prefix를 다시 선택한다는 점을 발견해 native 전용
  감사 wrapper를 분리했다. 수정 중 첫 native 감사의 `gait.py` 불일치 실패도 보존했다.
- 활성화 명령 인계: 커널RED4실패 → 기존 상태기계 포함35통과68.23초,
  실제ROS 첫 명령RED1실패11.77초(1.035 vs1.0), 초기값 출처RED3실패 →
  인계8통과15.18초. 관련 lifecycle/안전/Python 물리10통과40.57초.
  명령 FK 목표만 기존 명령으로 인계하고 실측 앵커·floor·안전 판정은 바꾸지 않았다.
- Git 감사 범위: 실 임시 저장소RED2실패 → 프로세스·증거 회귀 포함12통과9.93초.
  HEAD와 모든 해시 대상 runtime 수정/미추적 파일은 기록하되 과거 evidence 트리는
  순회하지 않는다. manifest에 `dirty_scope=hashed_runtime_files_only`를 명시한다.
- 실제5091c217: 활성화 구간 네 발 하중은 유지됐지만 guard ROS age로 실패했다.
  이후STOPPED를 실측했어도 GazeboSIGTERM/SIGKILL 승격·forced=true·launch-15를
  보존했다. 부모 회수·잔여 없음만으로 정상 종료라고 하지 않는다. 실제라이브러리
  소유권 자동수집은 성공했다. 새 실행의 성공률에 이 실패를 제외하지 않는다.
- kernel first_fault만으로 STOPPING 원인을 설명할 수 없어 첫stop의 선택 guard/header,
  수신 시각/노드ROS시각/직전16callback소요를 보존했다. 실제DDS250ms지연RED1실패
  16.56초 → 기존 최초fault·명령 인계 포함3통과17.10초. 200ms 기준은 그대로다.
- 실제64989f80: guard age 재발 없음·STAND 지지 유지, kernel first_fault/first_stop 없음.
  그러나 STAND ready 미확정으로 startup45초 제한 실패다. wrapper/runtime0·강제 없음·
  부모 회수·잔여 없음이 확인돼도 G1을 통과했다고 하지 않는다.
  `static-preload-budget.json`은 마지막5ROS초251고유 관측을 모두 사용했다.
  앞 calf 비포화 위치력17.74983371Nm/최대속도4.03e-7rad/s,
  P법칙 유도 오차0.035499667rad가 기존0.03rad 준비 기준을 넘는다.
  이는 직접 적용 actuator force나 내부 선택 목표 측정으로 부르지 않는다.
- 설정 후보: calf만kp500→750/kv8.944272→10.954451(sqrt1.5비), 기존30Nm 한계는 유지.
  반올림 상향18Nm 설계 부하의 오차0.024rad를 기대하되 실제 인수는 별도다.
  예산RED1실패12.07초 → 예산/물리/장면9통과32.78초. 새 양 엔진 physics/profilehash와
  실제 재검증이 필요하다. 다른 게인·안전 기준은 바꾸지 않았다. 다음 실제 실행은 고유UUID다.

## 재개 후 관측 경계와 시동 시간 판별

- `task8-gz-native-damping-package.log`: 두 패키지 빌드 후 전체276건 중275통과/1실패.
  실패는 수납 READY 이후 이상 입력을 설정하고80ms만 기다려 수신 상태를 단정한 시험이었다.
  실제 이상 감지·선택된 관절 입력·클라이언트의 fault 수신을 각각 기다리도록 시험만 교정했다.
  첫 후속 실행은 새 검증 코드의 저장 위치 오기(`selected`는 guard/crawl 전용)로13통과/1실패,
  이를 실제 `inbox.samples['joints']`로 바로잡은 `task8-carry-observation-storage.log`는
  **14통과149.31초**다. 원래1초 정착·200ms watchdog·고착 실패 조건은 변경하지 않았다.
  설치8패키지의 현재 소스 일치 감사도 `task8-native-damping-resume-audit.json`에 통과했다.
  전체276건 실행을 소급해 성공으로 바꾸지 않는다.
- 새 원생 감쇠 실행 `4d5bf634-812b-4b17-b9f5-a061824a471b`
  (run_id `25628fd6-511b-4078-9ddf-d7d20f8c7767`)는 **시동55초 제한 실패**다.
  관절 상태 broadcaster를 얻지 못했고 실측 프레임0개여서 정적/보행 비교 결과가 아니다.
  native 구동91개는 관측됐으나 운전 중 연속 수납·지지 판정을 대체하지 못한다.
  실제 서버PID1202/start33913/PPID1192/PGID1189의 라이브러리3개 경로·해시를 확보했다.
  엔진 wrapper는 SIGTERM(-15)로 종료됐다. parent 회수/잔여 없음이 확인돼도
  `forced_cleanup=true`, 정상 종료 false를 유지한다. 다음 실행과 섞지 않는다.
- 프로세스 start tick 대조에서 첫 자식 생성까지4d5는33.69초,
  이전547은20.20초,384는22.65초였다. 처음부터 순수 물리 계산이55초 걸렸다고 하지 않는다.
  모든 관측 단계가 시작되지 않은 `phase-timing-analysis.json={}`도 그대로 보존한다.
- NumPy 자체의 불필요한 BLAS 스레드 가설을 별도 일반 사용자 프로세스로 확인했으나,
  기본/프로세스 한정 OPENBLAS·OMP=1 양쪽 모두 import 후1스레드였다.
  따라서 관측된 ROS 노드15스레드를 BLAS라고 단정하거나 관련 설정을 수정하지 않았다.
- 다음 판별은 설치 파일을 모두 해시 대조해 Linux 소유 임시 영역에 복제하고,
  소스·바이너리·안전 기준은 그대로 두는 저장 위치 비교다. 복제 manifest·새 설치 감사·
  실제 실행을 각각 기록한다. 캐시 온도도 달라질 수 있으므로 단일 실행의 성패만으로
  저장 장치를 유일 원인이라고 결론 내리지 않는다. 아직G1/G2 통과나13.5 게시가 아니다.

## 2026-10-24 원생 구동과 계측 경계 판별

- 명령 관측 단계를 고친 센서 패키지21건과 설치8패키지 감사 통과 후,
  `54776df9-c003-44b1-af38-a554c8135e41`에서 실제20관절/1,040구동 진단을 얻었다.
  SHIFT에서 두 점 하중 지지가 재현됐으며 일부 전달 토크가20/30Nm 축 한계에 닿았다.
  직접 적용 구동력은 제공되지 않았으므로 무제한 토크라고 해석하지 않았다.
- 위치 명령을 유지한 제한 힘 PD 후보·모델 결합의 전체270건/설치8패키지 감사는 통과했다.
  그러나 첫 실제 비교 `31bc111a-cf0c-42f1-b7b0-962fdb76ed9c`는 시동 중 계측기 오류
  `CPU sample ownership changed`로 중단됐다. 물리 PD 실패로 집계하지 않는다.
  종료의 SIGTERM 승격·정상 종료 false는 그대로 보존했다.
- `proc-exit-characterization-6c6f4a26-01a8-414c-bf65-c2f7ca59c82d.json`에서
  일반 사용자 자식의 UID1000은 그대로인데 zombie의 `/proc/PID/stat` 파일 소유자만0이
  됨을 실제 확인했다. 관련 회귀2실패/3통과 → 수정 후27통과16.07초.
  동일 PID/start tick/PGID의 확인된 종료만 표본에서 제외하며 살아 있는 외부 소유자와
  PID 재사용은 계속 fatal이다. 권한·보안 정책을 바꾼 것이 아니다.
- 그 뒤 `38499c57-595c-4c11-8651-8f84c9f787ae`에서는 계측 오류가 재발하지 않았고,
  실제 서버PID1222에서 PD/관측 라이브러리3개의 경로·해시를 `native-owned-tree.json`에
  확보했다. 그러나 시동 대기 입력477개가 **실제 관절 속도 한계**로 거절됐다.
  팔 속도가 약±2/3rad/s로 진동하고 그리퍼는 약0.474m/s였다. 신선한 관측이며
  제어기 first_fault는 없었다(비활성 대기). 외부 probe 해석을 내부 선택 입력이라고 하지 않는다.
  종료0·강제 없음·잔여 없음이어도 측정 STOPPED 미확정 때문에 정상 종료 check는 false다.
- 원인 판별용 `dart-damping-study-fe875293-b545-44ae-bcd0-7442a7785cb3.json`은
  설치된 DART6.13.2의 독립1DoF 두 모델을 순차 실행했다. dt2ms/힘 한계12Nm/같은
  kp60·kd10에서 명시적 미분 힘은 속도3rad/s 진동·오차0.1rad가 남았고,
  원생 암시적 감쇠는 마지막200ms 오차1.93e-6rad·속도1.17e-5rad/s로 정착했다.
  **Gazebo 전체 로봇 G1 인수 성공이 아니라 적분 방식 판별 실험**이다.
- 새 후보는 원래 수동 감쇠+가상 감쇠를 모델에 명시하고 외부 힘에는 제한된 위치력만
  적용한다. 원생 감쇠·접촉 wrench를 actuator force로 위장하지 않는다. 새 물리 해시와
  실제 G1/G2 재검증이 필요하다. 장면 회귀8건 통과했고 하드웨어 감쇠 중복/모델 불일치와
  native damping 관측 누락을 각각 RED로 재현했다. 새 실제 엔진 성공은 아직 없다.
- 실패한 명시적 후보의 runtime4파일을 기존 source manifest SHA와 대조해
  `native-g1-gazebo-38499c57-595c-4c11-8651-8f84c9f787ae/failed-explicit-runtime-source.zip`
  에 보존했다(SHA256 `93e31b0b7dde237cd2a530de547e4161aa346359cfaf3547343fe59174d4a1b5`).
  원본 결과·로그·source/install manifest는 덮어쓰지 않았다.

## 최초 실패 입력에 근거한 Gazebo 지지력 분석

- `task8-gz-fault-exit-package.log`: **259 tests, 0 errors/0 failures/0 skipped**.
  `task8-gz-fault-exit-install-audit.json`:8패키지 설치본·출처 감사 통과.
- 후속 실제 실행 `native-g1-gazebo-81da9758-805b-4052-8f44-057e4995ff66`은
  **FAIL**이다. 정적10초·수납 typed terminal/원본 위치·속도 검사는 통과했지만,
  SHIFT 시작22.354s 뒤23.030s에 `current measured support lost`가 발생했다.
  `controller_report.json`은 제어기가 그 tick에 실제 선택한 불변 입력을 보존한다.
  접촉 촬영23.024s에서 FR76.9202/FL0/RR0/RL72.0329N이었다. unload는 아직 시작되지
  않았고 swing_foot도 없다. 관절/몸체 촬영은23.028/23.020s, ROS age2~12ms,
  wall age7ms 미만이다. 오래된 입력/발 들기 명령/TF 부재를 원인으로 추정하지 않는다.
- 원본에서 계산한 `controller-support-analysis.json`:실제 하중 지지점2개,
  몸체 속도 약(-0.03728,-0.02100,0.000148)m/s, 높이0.46046m다.
  발의 FK 높이가 약0.02m이고 몸체 기울기가 작아도 하중 지지점3개를 보장하지 않는다.
  이론적 지지 다각형과 실제 힘에 의한 지지를 구분한다.
- 접촉 어댑터 PID1167은 이번 실제 실행에서 SIGINT 종료0으로 바뀌었다.
  기록된 runtime 자식 모두 종료0이고 엔진 wrapper0·부모 회수·강제 정리 없음·잔여 없음을
  확인했다. 그러나 sticky FAULT 뒤 측정 STOPPED가 확정되지 않았으므로 전체 정상 종료
  check는 여전히 false다. 종료 코드0만으로 정지 실패를 숨기지 않는다.
- 다음 가설은 Gazebo 위치→속도 구동과 MuJoCo 감쇠 위치 PD의 동역학 차이다.
  아직 확정하지 않는다. 실제 ECM 관절 상태·명령·전달 wrench의 읽기 전용 계측을 추가한다.
  전달 wrench와 실제 actuator force는 다른 값이며 제공되지 않은 후자는 null로 남긴다.
  코어 회귀 `task8-gz-controls-red.log`의 API 부재 →
  `task8-gz-controls-first.log` 실제 ECS 2건 통과. 수신 회귀는
  `task8-gz-controls-probe-red.log`2실패/9통과 →
  `task8-gz-controls-probe-first.log`11통과9.47초다.
- 공식 Physics 구현의 명령 초기화 단계도 검토했다. 물리 계산 이후의 0값을 적용 명령으로
  오해하지 않도록 소비 전 관측 단계 계약을 추가 검증한 뒤 다음 엔진을 실행한다.
  외부 소스·드라이버·시스템 권한·힘/시간/3점 지지 기준은 변경하지 않는다.

## Gazebo 교정 실패와 종료 처리

- 실행 `d5460fa1-f944-4b79-ab83-54ee8536743b`(run_id `d8224db6-d6b9-4ebc-9d60-9a534c2553e0`)은 시동 경쟁 수정 후 실제 FJT terminal·수납·정적10초를 통과했다. 교정 SHIFT에서 `current measured support lost`로 실패했고 발 들기까지 도달하지 않았다. 외부 probe의7개 frame check가 true여도 제어기가 선택한 정확한 실패 입력이 같다고 단정하지 않는다. 팔 최대 위치 오차1.93×10⁻⁷rad/속도2.15×10⁻⁶rad/s, 센서 힘·IMU·scan·충돌 판정은 기준 이내였다.
- STOPPED는 확인하지 못했다. 엔진 프로세스는 종료0·강제 없음·잔여 없음·부모 회수를 확인했지만, 접촉 어댑터의 SIGINT가 처리되지 않은 KeyboardInterrupt로 종료-2를 냈다. runtime 정상 종료 미확정이므로 전체 normal check는 false다. GZ 실제 제어값/라이브러리 출처도 아직 미구현이며 성공으로 세지 않는다.
- `task8-gz-fault-exit-red.log`:2실패17.23초. 실제 ready 어댑터의 SIGINT 종료-2와 제어기의 첫 실패 입력 조회 기능 부재를 각각 재현했다. 예외 처리·join.stop 및 읽기 전용 첫 실패 snapshot을 추가한 `task8-gz-fault-exit-first.log`:관련17건 통과29.25초. snapshot은 제어기 첫 fault 관측 tick의 선택된 촬영·수신 시각·phase·목표를 보존하고 후속 건강한 입력으로 덮어쓰지 않는다. 실제 fault가 advance 중 발생했는지도 구분한다. 물리 원인 수정이 아니라 원인을 판별할 계측이며 다음 실제 실행으로 분석을 계속한다.

구현 시작: `a077ff2b15145e58fca8319595215d0db41cf905`, 브랜치 `feat/ch13-section-13-5`.
작업 범위: 사용자 승인 상세 설계·구현 계획. 네이티브 단일 작업자.
아래 기록은 초기 구현 시험이며 G1~G5 실제 엔진 인수 완료가 아니다.

## G0

- 기존 설치 감사: `python Ch13/scripts/verify_all_13_4.py --audit-install-prefix Ch13/ros2_ws/install13_4_completion_f8c0bed5-cdac-43d8-81ff-84ab88360cdb`.
- 결과: 기존 6패키지 소스/설치 byte 감사 성공. 원본 JSON: `g0-install-audit.json`, stderr: `g0-install-audit.stderr`.
- 기존 소스 시험: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test -q`.
- 결과: **374 passed, 224.38초**, `g0-pytest.log`.
- 원격 조회: 일반 sandbox의 네트워크 연결 실패 뒤 허용된 네트워크 조회로 재확인했다. 동명 13.5 원격 브랜치 없음. main은 `e83fe949553d9a2217c274c0bab23bf8f0713241`. 원격 변경은 하지 않았다.

## Task 1

- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test -q`.
- 최초 `task1-red.log`: 3 failed/9 fixture errors. 누락 샘플 모듈과 신규 IDL 때문에 실패했다. 모델 계약 시험을 더하고 fixture 부재를 시험 본문에서 드러내도록 고쳤다.
- 재확인 `task1-red-confirmed.log`: **15 failed**, 새 샘플/모델/IDL 부재. 무관한 의존성 실패를 의도한 RED로 세지 않았다.
- 순수 코어 GREEN: 같은 명령에서 `test_samples.py test_model.py` 선택, **12 passed, 3.23초**, `task1-core-green.log`.
- 빌드 명령: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`.
- 기존 ROS/외부 MuJoCo underlay와 지정 venv만 source한다. 이전 장·기존 13.4 overlay를 새 빌드의 의존성으로 사용하지 않는다.
- 전용 build/install/log 접미사는 이 실행 UUID와 같다. `task1-build.log`에 실제 결과를 보존한다. 신규 센서 패키지는 아직 작성 전이므로 이 단계는 7패키지 빌드다.
- 빌드 결과: **7 packages finished, 6분52초**. 기존 제어기 deprecation 경고 외 빌드 실패 없음.
- 전체 소스 회귀: 기존 세 시험 경로+신규 navigation/test, **389 passed, 202.34초**, `task1-all-source.log`.
- colcon 시험: `--packages-select integrated_robot_navigation integrated_robot_interfaces`, test-result **15 tests / 0 errors / 0 failures / 0 skipped**, `task1-package.log`.
- 새 설치본 감사: 기존 6패키지 감사+신규 모듈이 실제 새 prefix에서 로드되는지 및 Python byte 일치를 검사해 통과했다. `task1-install-audit.json`에 모듈·기존 .so 경로와 소스 SHA256를 보존한다.
- 이 시점에는 엔진을 기동하지 않았다. 실제 crawl/Nav2 성공을 주장하지 않는다.

## 환경·결정

- WSL은 일반 사용자 jinho/uid1000로 실행한다. sandbox WSL 접근 거절에만 도구 실행 허용을 사용했으며 sudo/관리자 권한을 사용하지 않았다.
- 기존 `/etc/wsl.conf`의 알 수 없는 키 경고를 관측했다. 범위 밖 설정을 수정하지 않았다.
- Windows→WSL 중첩 인용 명령에서 증거 경로 변수가 사라진 실행은 permission denied로 중단됐다. 같은 환경을 별도 shell 파일에서 읽으면 올바른 경로임을 확인해 이후 plan-local 실행 파일을 사용한다. 이 실행 오류를 제품 시험 FAIL/PASS로 계산하지 않는다.
- 기존 제어기 빌드의 deprecated API 경고는 원본 로그에 남기고 새 기능 때문에 관련 없는 소스를 변경하지 않는다.
- 커밋 시 `.git/index.lock` 때문에 실패했다. Windows/WSL의 Git 프로세스·열린 핸들이 없고, 0바이트 잠금의 시각이 16분 넘게 변하지 않았음을 확인했다. 삭제하지 않고 `.git/index.lock.stale-85670137-e73c-4c72-bcb2-0c73e755088b`로 보존해 정상 Git 동작을 복구했다. 실패한 커밋 뒤 자동 완료 원장에 같은 BASE/HEAD가 들어간 항목은 미완료로 정정하고 실제 커밋 뒤 재시험한다.
- pytest 원본 실패 로그에는 프레임워크가 출력한 줄 끝 공백이 있다. 원본 증거를 정리해 바꾸지 않고 보존한다. 소스·문서의 whitespace 검사는 raw evidence를 제외한 별도 검사로 적용한다.

## Task 2

- 시작 기준/Task 1 완료 커밋: `01ad4986cf740673dd8452c111b589dde4805a97`.
- RED: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_leg_kinematics.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_support.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_center_of_mass.py -q`, **15 failed**, `task2-red.log`.
- 최초 GREEN: navigation/test 전체 **30 passed**, `task2-green.log`. 전진 기구학은 별도 MuJoCo native 모델의 8자세×4발과 대조했다. 이는 물리 step/ROS/보행 시험이 아닌 오프라인 FK 교차검사다.
- 자체 검토에서 실제 thigh 상한 4rad와 atan2 주값 범위 차이를 발견했다. q=(0,3.8,0.4)의 유효 자세가 IK에서 거절되는 것을 `task2-angle-wrap-red.log`로 재현했다.
- 최소 수정: 원래 관절 한계 안의 2π 동등 해를 열거하고 직전 자세에 가까운 해를 선택한다. 작업 공간·관절 한계를 clipping해 통과시키지 않는다.
- 수정 GREEN: 전체 navigation/test **31 passed, 3.96초**, `task2-angle-wrap-green.log`.
- 수정 전 패키지 결과 `task2-package.log`와 소스 실행 `task2-all-source.log`는 최종 수정본 증거로 재사용하지 않는다. 수정 후 고정 소스로 `task2-fixed-*`에 재빌드·시험·감사를 수행한다.
- 수정 후 전체 소스 회귀: **405 passed, 202.55초**, `task2-fixed-all-source.log`.
- 수정 후 패키지 시험: **31 tests / 0 errors / 0 failures / 0 skipped**, `task2-fixed-package.log`. 새 설치본 byte 감사도 통과했으며 `task2-fixed-install-audit.json`에 해시를 보존한다.

## Task 3

- 시작 기준: `ba05b4896922e66f2c5abff06e133e5b26cdb7e8`. profile/footprint 최초 RED **9 failed**, `task3-red.log`.
- 독립 오프라인 검사 `task3-native-geometry-probe.json`: 원래 URDF와 MJCF 각각에서 base_link/네 thigh_link 침투 약0.020m. 렌더링·물리 step·ROS 실행은 하지 않았다.
- 교정 판단: 기존 기본값을 유지하는 Xacro 선택 인수 `hip_mount_y=0.13`을 추가한다. navigation 전용 발 y는±0.18m이며 이전 기본 발 y=±0.15m다. 새 MJCF도 같은 hip origin에서 생성한다. 비인접 충돌 쌍을 제외하거나 collision 크기를 줄이지 않는다.
- 선택 인수 시험: `task3-mount-red.log`에서 실제 미반영 실패→`task3-mount-green.log`의 기본 모델 보존/선택 모델 및 기구학 **8 passed**.
- profile은 오프라인 상태로만 생성한다. G1 검증 기록은 엔진/모델/물리/config hash, 필수 검사와 관측·액션·소스·설치·종료 artifact 해시가 모두 필요하다. 별도 ready 플래그만으로 통과하지 않는다.
- footprint는 허용 gait/arm 오차/roll·pitch 구간 전체의 삼각함수 극값과 보수적 행렬 구간을 사용한다. 몇 자세만 샘플링한 크기가 아니다. 원래 URDF collision과 더 큰 MJCF capsule 경계를 함께 포함한다.
- `task3-green.log`: 42 passed/1 failed. cos(π/2)의 부동소수 잔여가 경계0을 제외하는 문제를 확인해 trig 구간에 반올림 여유와 바깥 방향 반올림을 추가했다.
- `task3-roundoff-green.log`: **43 passed, 14.37초**. 준비 CLI 부재 RED는 `task3-cli-red.log`에 보존한다. 새 출력 생성·기존 출력 덮어쓰기 거절을 실제 명령으로 시험한다.
- 최초 구간 경계의 앞쪽 0.720643m는 접근 후보 상한0.65m와 맞지 않아 `task3-interval-refinement-red.log`로 과대 추정을 재현했다. 연속 구간을 최대0.10rad로 나눈 전체 합집합을 배치 계산하고, 실제 native 형상24자세의 독립 투영과5cm 여유 포함을 대조했다. `task3-interval-refinement-green.log` **5 passed**. 몇 점만 샘플링해 경계를 줄인 것이 아니다.
- 안전 설정 약화(여유·age·기울기·속도)를 허용하던 준비 API는 `task3-safety-limits-red.log`의 **4 failed**로 재현했다. 설정 상·하한 검사를 추가한 뒤 `task3-refined-green.log` **49 passed, 18.16초**.
- 수정 후 전체 소스 회귀: `task3-refined-all-source.log` **423 passed, 198.97초**. 패키지 시험: `task3-refined-package.log` **49 tests / 0 errors / 0 failures / 0 skipped**.
- `task3-refined-install-audit.json`에서 실제 설치 모듈·기존6패키지·신규 config/share bytes 일치를 확인했다. 준비 CLI는 설치본에서 실행했다.
- 새 `task3-refined-offline-profile`은 앞쪽0.579451m/뒤쪽-0.572826m/좌우±0.427560m, inflation_radius0.770118m다. 원래의 더 큰 `offline-profile`도 보존한다. 두 출력 모두 **offline**, G1 증거 없음, 이동 허용 불가다.
- 명목 수납 자세에서 URDF와 MJCF 각각401개 비인접 형상 쌍을 검사했다. 허용 gait 구간의 모든 자세가 자기 충돌 없이 동작한다는 실제 보행 보증은 아니며, G1/G2 실측이 남아 있다.

## Task 4 — navigation 센서·장면·선택 launch

- 시작 기준: `e1331bf5ff363037b7c371a7837b2a3c0049d8fa`. 소유한 중단 프로세스가 없음을 확인하고 재개했다. 기존 13.4 교육 문서40723바이트는 수정·stage하지 않았다.
- RED: `task4-core-red.log`에서 snapshot/normalization 헤더 부재, `task4-contact-wire-red.log`에서 예상 밖 접촉 필드 부재를 재현했다. 별도 미빌드 prefix의 의존성 오류는 feature RED로 세지 않는다.
- 구현: 독립 모델 clone·전체 `mj_copyData` 2슬롯·단일 consumer lease·최신 대기 프레임 덮어쓰기·stop 발행 경계·worker join. 카메라/EGL worker 또는 물리 live 데이터에 쓰지 않는다. reset/clock rollback은 재시작 전까지 차단한다.
- 버전 진단: Python 오프라인 MuJoCo는3.3.7, 실제 ROS C++ vendor는 **3.12.0/header3012000**이었다. `mj_ray` 추가 normal 인수에서 컴파일 실패한 원본은 `task4-core-first-build.log`에 보존한다. underlay/driver는 바꾸지 않았고 정확한 버전의 공개 API로 컴파일했다. 실제 플러그인 시험에서 header/library 모두3012000을 확인했다.
- 실행기 오류: `task4-core-vendor-test.log`는 colcon 탐색 범위 누락으로 Ch01의 기존 인코딩 진단이 나왔다. 소유한 시험기 PID1266에만 SIGINT를 보내고 `--base-paths Ch13/ros2_ws/src`로 교정했다. 시뮬레이터 종료 성공으로 세지 않는다. ROS 시험 콜백의 명시 타입 누락과 C++ Time 변환 오류도 원본 build log에 보존했다.
- 실제 ROS plugin class 부재 RED는 `task4-plugin-load-red-test.log`, 이후 GREEN은 `task4-plugin-time-test.log`다. fixture의 물리 kernel에서 발 하중 합/중력 IMU/원래 world 벽 ray·source 상태 불변, 실제 ROS header·발행·reset 차단·worker stop을 검사했다.
- Gazebo 관측기는 모든 로봇 collision에 `ContactSensorData`를 요청하고 실제 ECM 관성/세계 pose로 CoM을 계산한다. 빈 접촉 tick도 발행한다. fixed joint 결합 후의 실제 SDF collision 이름으로 매핑한다. 센서 core 부재 RED→ECM GREEN은 `task4-gz-observer-*`에 있다. 이는 Gazebo 전체 로봇 실행 정확도 인수는 아니다.
- Gazebo 힘은 세계 좌표의 알려진 평지 지지 하중만 정규화한다. pair 미러링의 collision 순서와 원래 힘 방향을 동일시하지 않으며, 발/ground 명시 매핑·힘 쌍 검증·중복 거절을 사용한다. 경사면/일반 접촉 힘 추정을 주장하지 않는다. native G1 정적 체중 검사는 여전히 필요하다.
- 장면 RED→GREEN: `task4-scene-red.log`, `task4-contact-map-red.log`, `task4-scenes-contacts-green.log`. 실제 MuJoCo parser와 Gazebo SDF 변환으로 검사했다. 평지·pedestal/컵·벽/우회 장애물과 같은 점유 지도를 생성하며 root 강제 이동/외력 plugin을 추가하지 않는다. RGB-D는320×240/15Hz 그대로다.
- exact scene launch·변조 hash RED→GREEN: `task4-launch-red.log` / `task4-scene-launch-first.log` **16 passed**. 실제 생성 URDF/SDF를 선택하며 navigation=false의 기존 경로를 유지한다. Gazebo controller 파일은 기존 긴 경로 문제 때문에 내용 hash 기반의 짧은 `/tmp` 복사본을 사용하고 bundle과 bytes 일치를 검사한다.
- 결합 시험: `task4-gz-join-red.log`의 신규4실패→`task4-gz-join-green.log` **11 passed**. 같은 native 촬영의 접촉/발 위치를 결합하고, 중복 수신으로 원래 wall 나이를 갱신하지 않는다. ROS/wall 각각200ms 및 clock reset 영구 차단을 확인했다.
- 최종 build: `python /usr/bin/colcon --log-base <log13_5_UUID> build --base-paths Ch13/ros2_ws/src --build-base <build13_5_UUID> --install-base <install13_5_UUID> --packages-select integrated_robot_description integrated_robot_navigation_sensors integrated_robot_navigation --executor sequential --cmake-args -DPython3_EXECUTABLE=<venv/python>`; `task4-fixed-build.log`, 성공.
- 최종 package: 같은 prefix에서 `colcon test --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation_sensors integrated_robot_navigation --executor sequential`, 이후 `colcon test-result --test-result-base <build13_5_UUID> --verbose`. **85 tests / 0 errors / 0 failures / 0 skipped**, `task4-fixed-package.log`. 구성은 Python70 + C++ 실제10 + CTest wrapper5이며85개 실제 물리 시험이라는 뜻이 아니다.
- 최종 전체 source: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_navigation/test -q`, **444 passed /257.47초**, `task4-all-source.log`.
- 설치 감사: `task4-fixed-install-audit.json`. 기존6패키지 + navigation + navigation_sensors의 실제 경로/bytes/빌드 소스 manifest를 확인했다. `.so` SHA와 실제 pluginlib probe의 header/runtime 버전, `gz plugin --info --plugin <실제 설치 .so>`의4개 System 인터페이스 등록을 기록했다.
- **미검증:** 전체 ROS 엔진 G1/G2, 실제 Gazebo 접촉·scan 정확도/자기 충돌 활성화, crawl 이동, Nav2, 정상 전체 엔진 종료는 아직 실행하지 않았다. 위 kernel/ROS/ECM/등록 시험을 종단 인수 통과로 세지 않는다.

## Task 5 — 평면 투영·이동 게이트

- 시작 기준: Task4 완료 커밋 `5d3c137a08776516642b9c4e1de27df4d90e47b2`. 커밋 후 CTest5 target/실제10 gtest 및 navigation70 시험 재확인 기록은 `task4-commit-gate.log`다.
- RED 명령: `python -m pytest Ch13/ros2_ws/src/integrated_robot_navigation/test/test_projection.py Ch13/ros2_ws/src/integrated_robot_navigation/test/test_motion_guard.py -q`, 누락 기능 **13 failed**, `task5-core-red.log`.
- 첫 구현의 ModelContract 필드명 오류 `.foot_links`는 `task5-core-first.log`의3실패로 확인하고 기존 계약 `.feet`만 사용하도록 수정했다. `task5-core-green.log` **13 passed**.
- 투영은 원본6D pose/twist/촬영·수신 시각을 바꾸지 않는다. 별도 `nav_base` z/roll/pitch0과 그 프레임의 실제 planar twist를 계산한다. `/odom`은 구독만 하고 `/navigation/odom` 및 `odom→nav_base`만 발행한다.
- 실제 DDS wrapper 부재는 `task5-ros-red.log`, offline profile 실제 서비스 거절을 포함한 부재는 `task5-ros-admission-red.log`에서 확인했다. 새 구현은 짧은 수신 실행기와 독립 monotonic watchdog으로 원본 raw 및 각 관측의 나이를 검사한다. 미래 센서는 clock이 따라올 때까지 최초 receipt를 보존해 대기시킨다.
- 헤더 없는 Twist의 RESET 이전 패킷은 동일 host DDS SYSTEM source timestamp cutoff로 거절한다. 엔진 epoch와 명령 generation은 별도이며, RESET은 관측·명령 cache를 비우고 HOLD로 돌아갈 뿐 CRAWL을 자동 허용하지 않는다.
- `task5-ros-first.log` **6 passed**: 실제 DDS·ROS clock pause에서 smoother 계속 발행/raw 중단, 중복 publisher, carry 이탈, scan 만료, 이전 generation, 실제 offline profile 거절. **양성 통신 시험은 외부 native-evidence admission만 stub**한다. controller·물리 보행이나 native G1 통과를 주장하지 않는다. 별도 unstubbed 서비스 시험은 실제 profile validator를 호출해 거절을 확인한다.
- 추가 RED3는 `task5-boundaries-red.log`: 실제 DDS용 투영 Node 미노출, dict 명령의 KeyError, 최종0 발행 후에도 ready=true 상태가 남는 문제. Node 경계를 노출하고 형식을 검사하며 종료 시 STOP/not-ready를 설정해 `task5-boundaries-green.log` **22 passed**로 확인했다. STOPPED는 guard가 증명하지 않는다.
- 실제 소유자 교체 RED: `task5-owner-replacement-red.log`. raw publisher를 파괴·재생성해 수가1로 돌아오면 출력이 계속(.006,.01)이었다. CRAWL 동안10개 입력/명령 stream의 실제 DDS endpoint GID도 고정해 교체 시 fault·0·명시적 재무장을 요구하도록 교정했다. `task5-owner-identity-green.log` **23 passed /26.03초**.
- 최종 build: 같은 전용 prefix에서 `colcon build --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation`; `task5-fixed-build.log`, 성공.
- 최종 package: 같은 prefix에서 `colcon test --base-paths Ch13/ros2_ws/src --packages-select integrated_robot_navigation --executor sequential`, `test-result --test-result-base <build13_5_UUID> --verbose`. `task5-fixed-package.log`: **108 tests/0 errors/0 failures/0 skipped**. Python93 및 이전 고정 C++10+CTest wrapper5 집계이며108개 실제 엔진 인수가 아니다.
- `task5-fixed-install-audit.json`의8패키지 소스/설치 bytes·센서 build manifest/library hash·실제 등록 감사 통과. fixed-topic DDS 시험 프로세스가 서로 다른 producer로 보이지 않도록 package 시험과 전체 source 시험을 같은 domain159에서 **순차** 실행했다.
- 최종 전체 source 명령은 Task4와 같은4개 pytest 경로다. `task5-fixed-all-source.log`: **467 passed /260.61초**.
- **미검증:** 실측 접촉 기반 crawl 및 G1/G2, 실제 Nav2 접근·취소, 전체 엔진 정상 종료와 최종13.3/13.4 실제 엔진 회귀는 후속 작업이다. 이 단계는 native 배포 완료가 아니다.

## Task 6 — 관측 기반 crawl kernel·lifecycle 다리 소유자

- 시작 기준 `25ba8531f16bb020e5d664df79710b38638c62b4`. Task5 commit gate93 통과는 `task5-commit-gate.log`에 보존했다.
- `test_gait.py`/실제 DDS lifecycle 시험을 먼저 작성했다. 부재·초기 경계 실패는 `task6-gait-red.log`, `task6-gait-boundaries-red.log`, `task6-lifecycle-red.log`다. 첫 kernel11, 공유 수신기/기존 DDS22, lifecycle6 통과는 각각 `task6-gait-first.log`, `task6-shared-receiver-first.log`, `task6-lifecycle-first.log`에 기록했다.
- 확대 시험 `task6-gait-envelope-red.log`: **4 failed/15 passed**. 0명령인데 다음 swing 진행, 현재 지지 밖에서 몸체 목표 발행, 최대 전·후진 중 CoM 여유 부족을 재현했다. 0명령은 현재 발 착지·정지 대기로 바꾸고 현재 지지 검사를 선행했다. `task6-pause-support-green.log` 관련6 통과.
- `task6-com-unit-probe.json`은 수정 전 코드 SHA가 포함된 **ideal-unit-only** 진단이다. 전진 첫 swing 여유0.01530→0.009970m, 후진 RR에서0.02204→0.009922m로 감소했다. 몸통 이동=전체 CoM 이동이라는 근사가 고정 지지 발의 관절·질량 변화를 누락했다. 전체 IK/URDF 질량으로 후보 CoM을 계산하고 제한 구간 내 유계 탐색을 사용했다. 측정 여유0.01m를 완화하지 않았다. `task6-kinematic-com-first.log`: **19 passed/20.19초**.
- 시계 정지/양쪽 시계 역행, 명시적 STOP 후 비영 명령 재개 금지와 inactive 진단 보존도 추가했다. `task6-final-boundaries-red.log`: **1 failed/26 passed**. deactivate가 직전 `clock paused`를 지우는 결함을 실제 DDS에서 확인하고 inactive 상태에도 fault를 보존하도록 수정했다.
- 최초 촬영/수신 나이·미래 inbox를 복제하지 않기 위해 Task5 수신기를 `observations.py`로 추출했다. 기존 motion_guard 실제 DDS도 같은 설치본/전체 source 회귀 대상이다.
- `task6-fixed-build.log` 성공. `task6-fixed-package.log`: **141 tests/0 errors/0 failures/0 skipped** (navigation126+기존 C++10/CTest wrapper5). `task6-fixed-install-audit.json`: 8패키지 설치 bytes·센서 plugin 출처/실제 등록 감사 통과. 전체 source 회귀 결과는 실행 종료 후 별도 기록한다.
- ideal-feedback fixture는 목표에 정확히 반응하는 수학/상태 전이 시험이며 native 물리 성공 증거가 아니다. 별도 무응답 시험은 계획 CoM만으로 발을 들지 못하게 한다. **G1/G2·실제 보행/전체 종료는 아직 미검증**이다.
- 최종 전체 source: `python -m pytest Ch13/tests Ch13/ros2_ws/src/integrated_robot_runtime/test Ch13/ros2_ws/src/integrated_robot_vision/test Ch13/ros2_ws/src/integrated_robot_navigation/test -q`. `task6-fixed-all-source.log`: **500 passed/337.63초**. 검증 뒤 runtime 변경 없이 문서만 보완하고 Task6를 커밋한다.

## Task 7 — 실제 ROS 수납 액션·시동 순서·배타 launch

- 시작 기준 `b6b976c2481d729c3d2170c61ef56da2a0782f31`. Task6 지정 commit gate **30 passed/32.26초**, `task6-commit-gate.log`.
- 실제 ROS FJT peer 경계 RED: `task7-carry-red.log` **1 failed/6 errors** (기능 부재). `task7-startup-launch-red.log` **4 failed**, 누락 시동/launch와 validation_mode에서도 CRAWL을 허용하던 문제. 서버·클라이언트·terminal·cancel ACK는 실제 ROS 전송이지만 peer는 물리 엔진/실제 JTC가 아니다.
- carry는 기존13.4 `ArmActionOwner`/독립 `ArmActionTransport`를 import한다. 서비스 success=예약이며 실제 result+실측 정착1초 전에는 ready가 아니다. 미확정 terminal 중 destroy 거절·receiver 보존, 이전 세대·팔 고착·외부 active goal·중복 그리퍼 명령자를 검사한다. 빈 그리퍼0.015m 유지가 물리 파지 증거라는 주장은 하지 않는다.
- `task7-carry-first.log` **5 failed/2 passed**. 후속 계측에서 action status endpoint가 실제2개임을 확인했다(`task7-core-second.log`). 시험의 native ActionServer waitable에 명시적 destroy를 추가했다. count 제한을2로 늘리거나 중복 발행자를 무시하지 않았다.
- `task7-explicit-server-lifetime.log` **3 failed/5 passed**: 중복 endpoint 오류는 사라졌지만 실제 시험 송신 공백 **303.573768ms**가200ms 안전 제한을 넘었다. production과 다른 하나의 MultiThreaded pool에 긴 peer와 짧은 parent를 묶었던 시험을 분리했다. 실제 배포와 같은 SingleThreaded parent + 별도 blocking peer 실행기에서 `task7-production-executor-comparison.log` **13 passed/33.41초**. 제품 age·취소 제한은 완화하지 않았다. 이전 실패는 모두 보존한다.
- launch 검사의 Jazzy public executable/location 표현을 바로잡은 뒤 실제 `scene_directory`/`scene_dir` 불일치를 `task7-launch-binding-red.log`의 Gazebo1실패로 재현·교정했다. 엔진 include는 하나이며 legacy locomotion/manipulation/tracking requester를 기동하지 않는다.
- 초기 설치 검증 `task7-fixed-package.log` **155 tests/0 error/0 failure/0 skip**,8패키지 감사 통과. 하지만 native 관절 broadcaster가 뜨기 전 activate할 수 있는 빈틈을 추가 검토에서 발견했다. `task7-premature-activation-red.log` **2 failed** → inactive 비명령 관측 준비 phase를 대기하도록 수정 → `task7-bootstrap-first.log` **13 passed/26.88초**.
- 수정 뒤 `task7-bootstrap-fixed-package.log` **156 tests/0 error/0 failure/0 skip**,8패키지 감사 통과. 이후 직선 그리퍼에 rad/rad-s 허용 오차를 쓰는 단위 결함을 `task7-gripper-units-red.log` **2 failed**로 재현했다. 팔0.03rad/0.02rad-s는 유지하고, 그리퍼는 목표0.015m에 대해 **0.002m/0.005m-s**를 별도 적용했다. 양성 peer도 명시적으로0.015m 실제 메시지 피드백을 공급하도록 교정했다. 기존 footprint는 그리퍼 전체 허용 구간을 포함하므로 축소하지 않는다.
- 위155/156건은 후속 runtime 변경 이전의 결과다. 마지막 소스의 package·설치 감사 결과는 실행 종료 후 별도 기록한다. 변경 없는13.3/13.4 전체 matrix는 이 디버깅 단계마다 재실행하지 않고 Task13 최종 동결 회귀에서 수행한다.
- **미검증:** G1 실제 controller·native 센서·carry·발 lift, G2 실제 보행, 실제 Nav2와 전체 정상 엔진 종료. unit/peer 통신 성공으로 이 항목을 PASS로 세지 않는다.
- 마지막 소스 검증 `task7-si-fixed-build.log` 성공. `task7-si-fixed-package.log`: **158 tests/0 errors/0 failures/0 skipped** (navigation143+기존 C++10/CTest wrapper5). `task7-si-fixed-install-audit.json`: **8패키지 설치 bytes·센서 library/실제 등록 감사 통과**. 이후 runtime 수정 없이 Task7를 커밋한다. 실제 엔진 결과는 아직 없다.

## Task 8 — 실제 엔진 G1/G2 인수 (진행 중)

### 새 서보 설정의 실제 MuJoCo와 SHIFT 연속성

- 시동 초기 상태 수정 `task8-empty-bootstrap-build.log`27.0초 빌드 성공, `task8-empty-bootstrap-package.log`**257 tests/0 errors/0 failures/0 skipped**(Python238+native13+wrapper6), 두 패키지 시험3분48초·8패키지 설치 감사 통과를 확인했다. 소스·설치를 다시 고정하고 새 UUID Gazebo 진단을 시작한다. 이전 강제 종료를 정상으로 바꾸지 않고, 기존 MuJoCo PASS도 수정 전 역사적 결과로 구분한다. 최신 소스의 양 엔진 인수·최종 연속 성공/전체 회귀는 여전히 남아 있다.

- 최초 Gazebo `87854340-d0e6-4e20-a246-a0681ecec04c`(run_id `7fdfaf56-6b8b-4e2e-9571-099c5ca24440`)는 시동 중 `crawl:startup scene model mismatch`로 FAIL이었다. 원본에는 구성 전 `INACTIVE/BOOTSTRAP_WAIT_FEEDBACK/빈 hash/not-ready`가 실제 발행됐고, 구성 완료 서비스 ACK보다 기존 status 수신이 늦게 반영되는 순서 경쟁이었다. 이후 정상 hash는 일치하지만 이전 fault를 자동 복구하지 않는다. STOPPED 확인 실패 후 Gazebo pause/stop ACK는 받았으나 wrapper1149/start7379,parent1144가 SIGTERM(-15)까지 escalated됐다. **forced_cleanup=true, 정상 runtime/engine=false**, 잔여 없음·부모 회수만 확인했다. 이를 정상 종료로 세지 않는다.
- `task8-empty-bootstrap-red.log`:1실패/실제 잘못된 hash 거절1통과8.83초. 최소 수정은 WAIT_FEEDBACK 중 명시적 구성 전 빈 상태만 준비 부재로 기다리는 것이다. 잘못된 nonempty hash·ready/stopped를 주장한 빈 상태는 허용하지 않고200ms·45초·claim 검사는 유지한다. `task8-empty-bootstrap-first.log`:관련10건 통과19.72초. 전체 빌드·회귀·설치 감사 후 새 Gazebo 진단으로 진행하며, 종료 정지의 별도 원인은 아직 확정하지 않았다.

- **최초 MuJoCo 전체 G1 PASS:** `9bd81e84-4a85-4d91-8082-d54a318fd3d1`, run_id `cb913220-9080-4a5a-bc8d-2e1b22272e1a`.23개 required check 모두 true/errors 빈 배열, 실제 실행기 exit0이다. 정적 ROS10.038초/wall10.0366초, 교정 ROS9.84초/wall9.81075초였다. 팔 최대 오차0.0191749rad/속도0.00736246rad/s, 그리퍼0.00013943m/0.00136038m/s, 실제 FL lift41개 고유 촬영을 확인했다. 체중 상대 오차6.58×10⁻⁶·최대 거리 오차1.26×10⁻⁶m, 전체 gyro/body 차이최대0.015624rad/s도 새 판정 경계 이내였다.
- Native1216/start9523,parent1210, TF관측기와 runtime/engine 정상 종료0·회수·강제 없음·잔여 없음을 확인했다. 기존 실패는 원본 FAIL로 보존한다. 이는 **첫 G1 PASS 한 회**이며 G2 보행·Gazebo·Nav2·최종 동결 회귀/3회 연속이나13.5 완료를 의미하지 않는다. 다음은 순차 Gazebo 진단이다. Gazebo의 실제 제어값/라이브러리 출처 판정이 아직 미구현이므로 해당 required check는 false를 유지하고, 실제 물리 시동·수납·교정을 먼저 조사한다.

- G1 sensor 의미12건 RED10.14초→GREEN8.96초 뒤, 수납 raw 판정 부재8건 RED8.71초와 구간 경계3건 RED8.31초를 추가 재현했다. `task8-g1-semantics-related.log`:기존 인수·제어값·관측·TF 회귀와 함께 **61 passed/17.42초**. 실제 정적 시간은 ROS/wall 각각10초를 유지하고 원본 coverage와 구분한다. 알 수 없는 stage나 운용 중 실패를 거르지 않는다.
- controller/N/S runtime은232건 검증 이후 바꾸지 않았다. 새 검증용 script/test 변경만 관련 회귀와 문법 검사·`task8-g1-semantics-install-audit.json`8패키지 byte 감사를 통과했다. 현재 새 실행은 `9bd81e84-4a85-4d91-8082-d54a318fd3d1`이며 이전 FAIL을 재판정/수정하지 않고 완성된 검증기로 처음부터 실행한다. G1 전체 인수는 결과 완료 전 선언하지 않는다.

- 실제 `67ccb0eb-d0b8-4f8f-8ea3-2edc6d6b8f4c`(run_id `b5f9cadb-6c29-4774-834f-cdc18d7486ee`)는 시동·실제 FJT terminal·수납 정착·정적10초·단일 발 교정 후 STAND 복귀와 정상 정리를 마쳤다. runtime fault/error_traceback은 없었다. Native1148/start75222,parent1142, 관측기와 런타임 모두 종료0·부모 회수·강제 없음·잔여 없음이다. 구현된18개 check는 모두 true이며 실제 loaded producer/ctrl/TF·명령 단일 소유권도 확인했다. 다만 접촉 힘·IMU·거리·충돌·실제 발 들기5개 필수 의미 판정이 아직 없어 **원본 전체 결과는 FAIL을 유지한다**. 이 실행을 G1 전체 PASS나3회 연속 성공으로 세지 않는다.
- 누락 판정 RED `task8-g1-sensor-semantics-red.log`:12실패10.14초로 API 부재를 확인했다. 합성 unit fixture는 native 출처 증거가 아니라고 명시했고, 힘 배율/발 이름/IMU 축/자체거리 hit/발 들기 누락·오매핑/비예상 접촉/겹침/중복 촬영/합성 odometry를 거절하도록 정의했다. 종료 구간은 명시적으로 구분하되 운용 중 실패 프레임·원본 로그는 보존하는 계약이다.

- 속도 예산 후보 `task8-foot-speed-bound-horizon.log`:관련53건 통과80.73초. 그 뒤 `task8-foot-speed-build.log`34.0초 빌드, `task8-foot-speed-package.log`**232 tests/0 errors/0 failures/0 skipped**(Python213/199.32초+native13+wrapper6),8패키지 설치 감사 통과를 확인했다. 소스·설치본을 고정하고 새 UUID 장면/프로파일의 실제 MuJoCo로만 원인 가설을 판별한다. 기존 d11/046 실패는 보존하며 G1 인수와 최종 전체 회귀는 아직 미완료다.

- 속도 후보 첫 회귀 `task8-foot-speed-first.log`:48통과/3실패75.88초. 새 속도/프로파일 상한·착지 연속성·실제 물리2건은 통과했지만 최대 전진/후진 네 발 순서 시험이40초 안에 세 발만 관측했고, ideal 교정이 기존5초 관측창을 넘었다. controller fault나 실제 물리 실패와 구분한다. 최대80mm 궤적은 도출한 속도 상한에서 약10초가 필요하므로 단위 순서 관측창만 bounded60초로 명시 정정했다. 교정 단위 시험은 실제 G1과 같은10초를 적용한다. 실제 G1 교정10초·G2/과제 기준·네 발 모두 확인 조건은 유지하며, 새 회귀 `task8-foot-speed-bound-horizon.log`로 확인 중이다.

- 착지 수정 후 실제 `046c4a16-410f-4be7-97dc-70f1feef287e`(run_id `e597de84-814d-43a9-9434-337a87d64088`)도 FAIL이었다. 첫 READY16.408초, 교정26.708초, SWING32.864초, fault33.526초로 **TOUCHDOWN 전** 수납 이탈이다. 팔2 속도0.06134rad/s·그리퍼0.01510m/s였고 실제 ctrl 목표는 유지됐다. 따라서 접촉 이후 연속성만으로 전체 원인을 설명할 수 없으며 이전 수정의 효과를 과장하지 않는다. frame7항목과 정상 runtime/engine/observer 종료0·부모 회수·강제 없음·잔여 없음은 확인했다. 생산자/graph 수집 이전의 실패 check는 원본 그대로다.
- 기존 `.8s` SWING에 별도 발 속도 상한이 없다는 구조를 분리했다. `task8-foot-speed-red.log`:정지 교정·전진·회전3실패12.98초. `task8-foot-speed-profile-red.log`:0.021m/s 설정을 허용해1실패14.02초였다. 현재는 전체3D 궤적의 미분 상계로 실행 시간을 정해 발 목표 속도≤0.02m/s를 보장하는 후보를 구현했다. 새 설정은 config/profile hash에 포함되고 기존 모델/프로파일로 허가를 재사용하지 않는다. PD·힘·수납 기준은 변경하지 않는다. 관련 회귀 및 새 실제 엔진 판별 전 G1 PASS를 선언하지 않는다.

- 착지 수정의 관련36건 통과 후 `task8-measured-landing-build.log`34.1초 빌드 성공, `task8-measured-landing-package.log`**228 tests/0 errors/0 failures/0 skipped**(Python209/198.82초 + native13 + wrapper6), 두 패키지 시험3분41초·8패키지 설치 bytes/센서 출처 감사 통과. runtime을 고정하고 새 장면·프로파일·UUID의 실제 MuJoCo 진단으로 진행한다. 단위/물리 component 통과를 G1 인수로 세지 않는다.

- 후속 새 실행 `d11db78d-df47-4450-82ca-9ef113b990f9`(run_id `a6defb62-dca5-44c5-8b49-b31e2aac817f`)에서 시동 게이트와 실제 FJT typed terminal/수신·수납 정착은 통과했다. 첫 READY18.416초, 교정 SHIFT28.622초→SWING34.834초→TOUCHDOWN35.622초에 수납 이탈로 실패했다. `carry-failure-analysis.json`: 팔 최대 속도0.019385rad/s는 기준 이내였고, 그리퍼 실제 ctrl0.015m 유지 중 속도 약±0.005404m/s(직전0.5초 최대0.006271)가0.005를 넘었다. 수납 이탈을 완화하거나 성공만 골라 세지 않는다.
- `calibration-failure-analysis.json`: 착지 때 FL 하중25N, 몸체 수평 속도약0.045m/s·각속도 반동과 함께 내려가는 다리 ctrl 변화가 지속됐다. 실제 관측은 정상이며 오류 출력이 아니다. Native1149/start75825, observer1158/start75828, parent1143 모두 정상 종료0·회수·강제 없음·잔여 없음이다. 이번 정적486프레임7항목과 전체 frame7항목은 true지만 실제 생산자/graph 수집 전에 실패했으므로 native ctrl/TF check를 소급 PASS로 바꾸지 않는다.
- 착지 계약 RED `task8-landing-continuity-red.log`:3실패 중1개 시험 IK 인자 오류를 보존하고 바로잡았다. `task8-landing-continuity-red-confirmed.log`:**3실패/8.44초**로 실제 접촉을 무시한 timer-only SWING, 접촉 반동 시 과거 floor로 약13.45mm 목표 점프, 측정 compliance를 새 목표로 복사하는 착지 불연속을 각각 재현했다. 최소 수정은 접촉 시 하강 선점, command anchor 연속 유지, 접촉 상실 때 기존2mm/s의 유계 탐색이다. 그리퍼 PD·힘/위치·속도 기준은 변경하지 않으며 물리 및 native 후속 검증 전 해결 선언하지 않는다.

- 시동 순서 RED `task8-startup-claims-red.log`:6실패/2통과18.06초. 비활성 제어기 응답에서도 activate가 나간 실제 DDS4건과 장면 모델 매개변수 누락2건을 재현했다. 최소 게이트 후 `task8-startup-claims-first.log`8통과21.40초. `task8-startup-claims-build.log`35.5초 빌드, `task8-startup-claims-package.log`**225 tests/0 errors/0 failures/0 skipped**(Python206/native13/wrapper6),8패키지 설치 감사 통과. 새 UUID 실제 엔진으로만 후속 검증하며 G1 완료로 세지 않는다.

- 새 실행3ba3fa92는 교정 전에 `startup service rejected: CARRY_REQUESTED`로 실패했다. joint_state_broadcaster만 먼저 활성화되고 팔·다리·그리퍼 spawner가 기동 중인 시점에 prepare가 호출됐다. 서비스 존재/자연 정지 피드백은 실제 controller 활성/command interface 소유권의 증거가 아니다. 원래 Trigger.message가 버려져 정확한 거절 사유는 아직 미확정이다. engine/runtime/observer 종료0, STOP·측정 정지·비활성·결과 drain·worker join·부모 회수·강제 없음·잔여 없음은 확인했지만 G1 PASS는 아니다. 이전 승인 검토 사용량 제한은 재개 후 해소되어 일반 WSL uid1000으로 설치된 ListControllers/ControllerState 정의를 읽었다. 다음은 활성/소유권 지연을 실제 DDS로 재현하는 RED이며 기존 실패 원본을 보존한다.

- `task8-damped-profile-build.log`: 두 패키지 빌드34.6초 성공. `task8-damped-profile-package.log`: **222 tests/0 errors/0 failures/0 skipped**(Python203 + 실제 native13 + wrapper6). `task8-damped-profile-install-audit.json`:8패키지 설치 bytes·sensor 출처 일치. 그 뒤 runtime을 바꾸지 않고 새 장면/프로파일 `native-g1-mujoco-3ba3fa92-2ab2-4f6a-bafb-2f22682dbba7`으로 실제 G1 진단을1회 실행 중이다. 이전 prepared535a나 그 source/physics hash를 새 허가로 재사용하지 않는다.

- `task8-unload-owned-first.log`:32통과/물리1실패42.08초. 교정 자체는7.62초에 완료됐지만 팔 최대 오차0.0312446rad·속도0.050753rad/s, 그리퍼 속도0.012067m/s가 남았다. `calibration-trace-e99cea13-8a78-4e2e-bf7b-ce1080348338/trace.json`으로 SHIFT의 팔 속도0.00579와 달리 SWING 말기/TOUCHDOWN에서 반동 응답이 크다는 것을 확인했다. 단위 시험 완료만으로 수납 안정 성공이라 하지 않는다.
- `carry-gain-probe-6ee635d8-509c-4d4a-a052-a89fb70a0156/comparison.json`: 팔 강성1/1.5/2 후보 모두 교정 완료, 그러나 속도 기준 실패로 채택하지 않았다. 강성1.5를 고정한 `carry-damping-probe-89795b9b-dbd1-408b-91e8-4694117f7e90/comparison.json`의 감쇠2/3/5 비교에서 **5만** 모든 기존 기준을 충족했다. 팔 오차0.019399rad·속도0.016485rad/s, 그리퍼 오차0.000304m·속도0.004840m/s였다. force/ctrl/관절·질량은 그대로다.
- 이 후보를 navigation 전용 생성 MJCF 설정에만 적용한 `task8-damped-carry-first.log`: **53 passed/44.05초**(커널31·물리2·profile11·native 제어 의미9). 기존 description/13.4 모델은 바꾸지 않았다. 감쇠 증가는 실제 FJT settle과 ROS C++3.12.0에서 다시 확인해야 한다. `task8-damped-profile` 전체 설치/회귀/감사가 현재 실행 중이며 완료 전 다음 엔진을 시작하지 않는다.
- 원본535a의 `g1-static-analysis.json`은 정적488프레임의 독립 센서 기하 계산이다. 기대 체중149.211081N 대비 실제149.210100~149.210188N, 중력 벡터 오차최대1.54×10⁻⁵m/s²·gyro/body오차1.91×10⁻⁷rad/s·world 벽 ray 거리오차1.48×10⁻⁶m였다. 외부 센서 값을 주입하거나 기존 FAIL/required_checks를 바꾸지 않았다.

- `task8-shift-continuity-first.log`: 28통과/물리1실패35.33초. 기울기 소실은 실제 결함이지만 교정 물리 실패의 전부는 아니었다. `calibration-trace-1c10d81c-d5f1-4a9c-b1fb-cee5d9c9cf6d/trace.json`에서 내부 몸체 이동 peak≈0.17m/s,0.7초 후 반동 중 SWING 시작, 최종 FR/RL 두 발만 약73N씩 지지하는 과정을 확인했다. 센서 기준을 낮추지 않는다.
- `task8-dynamic-shift-red.log` 2실패: 내부 기준 가속도0.59625m/s², 잔여 실측 속도0.004m/s에서도 lift가 발생했다. 내부 quintic 가속도≤0.10m/s² 및 100ms 실측 안정 게이트를 추가했으나 `task8-dynamic-shift-first.log`는27통과/4실패30.57초였다. 부하 전달·진행 시계 구조가 여전히 부족하므로 이것만으로 해결됐다고 쓰지 않는다.
- 원인은 **기하학적 여유와 발 부하 해제의 혼동**으로 더 좁혔다. FL에 약25N이 남은 채 빠른 swing을 시작했다. `task8-measured-unload-red.log`는 ideal peer에서도 실제 하중30N을 확인하지 않고 전이함을 재현했다. SHIFT 안에서2mm/s로 부하를 천천히 해제하고 실제 force<2N·다른 세 발 지지·실측 안정100ms 후 SWING하는 후보로 바꿨다. 안전 대기 시간은 더 이상 몸체 진행에 추가 적분하지 않는다.
- 최초 후보 `task8-measured-unload-first.log`:30통과/2실패44.98초. carry 속도0.005794rad/s·오차0.029026rad·그리퍼 속도0.000359m/s는 원래 기준 이내였으나,5mm 해제 경계에서 여전히 FL13.75N이 남아 안전 중단했다. `calibration-trace-178939ca-584f-465a-a437-050c8eba03a2/trace.json`에 목표 높이·실제 힘/CoM/몸체를 보존했다. 이를 contact 해제로 세지 않는다.
- 같은 compliance 관측에 따라 해제 상한을 총 swing20mm 안의10mm로 설정하고, 시간 한계는 높이/2mm/s+1초로 유도했다. 실제 force<2N 조건과 부모 교정10초·팔·접촉·지지·센서 한계는 유지한다. 이전 scene/profile을 재사용하지 않는다. `task8-unload-stop-red.log`의1실패로 해제 중 STOP에서 발 소유 식별이 빠진 결함도 재현했고, 해제 시작부터 같은 발을 소유해 기존 착지≤1초/STOPPED1초 검사를 적용했다. `task8-unload-owned-first.log`가 현재 관련 회귀다.
- **시기 계약 정정/미완료:** `cycle_s=8`은 이제 발 목표·몸체 진행의 명목 phase-time이다. 실제 하중/안정 게이트 때문에 물리 주기는 더 길 수 있고 **고정8초 보행을 달성했다고 주장하지 않는다**. 이는 Nav2 진행률·기존 deadline의 실제 검증 비용을 늘린다. 순서/최대 명령 시험은 임의450/550tick 대신 bounded40초 내 네 발 모두의 실제 SWING을 요구해 범위를 강화했다. 실제 G1/G2·실습 완료·게시를 아직 선언하지 않는다.

- 새 실행 `535a37d0-bd38-43af-8438-b0bcbb0d8f66`(내부 run_id `da8a2300-9c48-470f-9932-b7491083f90f`): 기립과 실제 FJT 성공/수신·측정 settle·미검증 CRAWL 거절은 확인했다. 첫 READY ROS10.726초, 정적 유지 후 한 발 교정 `SHIFT` ROS20.906초 진입, ROS20.968초에 `measured carry posture lost`로 실패했다. **G1 전체 PASS가 아니다.**
- `carry-failure-analysis.json`: 팔2의 실측 속도0.0319435rad/s가0.02 기준을 넘었다. 실제 native ctrl은1.2, 팔3 ctrl은-2.0으로 목표를 계속 유지했다. 힘 포화가 아니라 몸체 이동 중 팔 응답을 조사해야 한다. 실패 전 stand488프레임의 freshness/자세/지지/CoM/관절/slip7항목은 모두 true였다. posthoc native 제어값·TF 의미도 true지만 실행 중 provenance/graph 수집까지 완료하지 못한 check를 소급 PASS로 바꾸지 않는다.
- **정상 정리 개선 확인:** parent2202/start55375, native2208/start55793·TF관측기2217/start55796. STOP/측정 정지/비활성/실제 결과 drain/native worker join 후 런타임·엔진 각각 종료0, 부모 회수·강제 정리 없음·잔여 없음. 이번 실행의 정상 종료 check는 true다. 반면 전체 frame의 freshness false에는 의도적으로 센서를 끈 종료 구간이 섞여 있으므로 측정 구간 분리도 후속 판별한다. 원본 FAIL은 보존한다.
- 작은 물리 `task8-carry-calibration-physics-red.log`에서도 교정 완료 실패를 재현했다. 통제 비교 `carry-gain-probe-49f87f69-f4a5-4d7f-8719-c06f7870054b/comparison.json`의 팔 gain1/3/5는 모두 `current measured support lost`였다. 팔 오차는 줄었지만 속도와 그리퍼 응답/지지 실패가 남았으므로 **어느 gain도 채택하지 않았다**. 원본 팔/그리퍼/힘 한계는 그대로다.
- 구조 판별 `task8-shift-continuity-red.log`: 기립 pitch0.04rad에서 경과0초·zero command의 교정과 첫 이동 두 경로 모두, 기존 회전이 yaw-only 항등행렬로 바뀌는 결함을 재현했다. 수정은 world-z yaw 증분만 기존 회전에 곱해 기존 기울기를 연속 보존하는 것이다. 자세 기준·8초 cycle·힘/속도/센서 기준을 완화하지 않는다. 전체 커널/실제 물리 회귀 `task8-shift-continuity-first.log` 실행 중이다.

### 수납 시험 경계 후속 진단

- 고정 소스 `task8-engine-clock-build.log` 두 패키지 빌드37.0초 성공. `task8-engine-clock-package.log`: **215 tests/0 errors/0 failures/0 skipped**(Python196 + native gtest13 + wrapper6). `task8-engine-clock-install-audit.json`: **8패키지 설치 bytes·sensor plugin 출처 일치**. 이어 `native-g1-mujoco-535a37d0-bd38-43af-8438-b0bcbb0d8f66` 새 장면/프로파일로 actual G1 진단을1회 시작했다. 이 시점 G1 PASS는 아니다.
- **시계 가설 판별 증거:** `carry-wire-trace-a171ee1c-c0e5-45c1-bedd-cc29b4f73acf.json` 연속 span의 `Δsource_system_ns − Δend_ns` 최대가 **2,936.113704ms**다. 즉 이번에는 실제 SYSTEM 대비 monotonic의 약2.936초 step을 직접 기록했다. 같은 시험은 의도한 `carry measured settle timeout`으로 끝나고 자식 exit0이었다. OS/NTP/호스트 중 누가 보정했는지는 이 자료만으로 확정하지 않으며 시스템 설정은 바꾸지 않았다. 테스트 ROS를 엔진과 같은 독립 `/clock`으로 구성한 이유를 뒷받침하지만, 이전 native body 공백을 같은 원인으로 단정하지 않는다.

- `task8-peer-owned-package.log`: 전체215건 중 고착 팔1실패로 다음 엔진/설치 감사를 보류했다. **독립 발행만으로 완전 해결되지 않았다.** 원본 `carry-wire-trace-9de378fb-220d-4466-9d8f-dcf35c5f47e2.json` 최초 fault에는 ROS age2960.115632ms/수신 후 wall age10.208276ms가 함께 있고, 별도 발행기 span은20ms 간격으로 계속됐다. graph 조회도 약0.25ms였다. 단순200ms publisher 공백과 다른 시계 경계이며 SYSTEM 시계 보정 가설을 세웠지만 이 원본만으로 운영체제 원인을 확정하지 않는다.
- 실제 엔진과 조건을 맞춰 시험용 `/clock`을 monotonic 경과로 생성하고 manager/peer에 `use_sim_time=true`를 적용했다. 기존 촬영 header 재기록, 호스트 시계 설정, 오래된 목표 재사용은 하지 않는다. 새 캡처/clock/SYSTEM/첫 MONOTONIC 수신을 별도로 남긴다. 시험 원본·clock을 함께 끊을 때도 **wall_age**가 취소를 일으켜야 하며, typed result 전 lease 유지와 sticky fault를 그대로 요구한다. 이 변경은 통신 fixture에만 적용되며 실제 MuJoCo body342ms 문제의 해결 증거로 쓰지 않는다.

- 후속 `task8-feedback-lifetime-fixed.log`: **14 passed/105.46초**. 원래 수납·취소·세대·11초 고착 팔 timeout과 새 독립 발행/실제 입력 손실을 모두 검사했고, 자식의 정상 종료0·join을 확인했다. `carry-wire-trace-*.json`에 각 시험의 실제 수신 상태, 최초 fault 경계, 발행 시각/스레드CPU, 자식 시작 단계/PID/종료를 보존했다. 시작 단계 계측의 대부분은4.19~4.79초로 기존5초 경계가 빠듯했음을 보이나 이전 두 지연의 정확한 원인을 소급 단정하지 않는다.
- `task8-native-control-verdict-red.log` 9건 API 부재 실패 → `task8-native-control-verdict-first.log` **25 passed/9.25초**(제어값 의미9 + 기존 인수 경계16). 새로운 판정은30개 고유 촬영/단조 sequence,20개 관절의 실제 scalar 주소/단위/position 제어/gain/한계/힘/유한값을 exact MJCF·URDF와 대조한다. fixture JSON의 통과만으로 native 출처를 증명하지 않으며 runner는 별도 loaded producer 감사와 결합한다. 나머지 G1 누락 항목은 여전히 false다.

- `task8-generation-timing-characterize.log`: 관련3건 통과25.46초. wall 대기157ms/발행0.28ms/스레드 CPU2.36ms로 관측되어 호스트 스케줄링과 클라이언트 본문에 묶인 발행 구조를 구분해야 한다. `task8-load-observed-package.log`는 전체204건 중 고착 팔 시험1건이 `guard:ros_age`로 실패했다. 통과할 때까지 동일 실행을 반복해 성공만 취하지 않는다.
- `task8-feedback-isolation-red.log`: 클라이언트가250ms 대기하면 pump 기반 원본도 멈춰 `guard:ros_age`가 발생하는 구조를 최소 재현했다. 실제 시스템처럼 **시험용** 상태 발행기를 별도 프로세스50Hz로 분리했다. 실제 엔진 센서 또는 물리 G1 증거로 부르지 않는다. 의도적인 실제 입력 손실에서는200ms 차단·sticky fault·typed terminal 전 lease 유지도 검사한다.
- 첫 분리 실행 `task8-feedback-isolation-first.log`는 **12통과/2 setup error,105.30초**였다. 입력 안전 검사는 바꾸지 않았지만 시험 자식이5초 내 시작되지 않은2건이 있었고, 부모가 이미 생성한 action receiver가 생성 실패 경로에 남았다. 프로세스 시작 실패와 제어기 실패를 혼동하지 않는다. 테스트 부모PID1099/PPID752/PGID752·실제 명령을 확인한 뒤 일반 사용자 SIGINT로 정리했다. 그 뒤 abort(-6)와 KeyboardInterrupt를 원본 로그에 보존했으며 이를 정상 종료 성공으로 세지 않는다. PID1099/1120 잔여 없음도 확인했다.
- 후속 수정은 시험 자식을 **부모 ROS 자원보다 먼저** 취득하고, interpreter import/rclpy init/Node/publisher 준비 단계를 계측한다. 자식 시작은15초의 별도 wall deadline이고 실행 중200ms 센서 기준과 무관하다. 정확한 ready 조건 후에만 시험을 시작하며 취소 결과 전 부모 자원을 파괴하지 않는다. `task8-feedback-lifetime-fixed.log`로 전체 수납 경계를 재검증 중이다. 새 native 엔진은 아직 시작하지 않았다.

- 시작 커밋 `b26bcfb03e72753140be41e5fa089621f417bd55`. G1이 통과하기 전 G2 실행과 Nav2 성공 기능 추가는 차단한다. 현재 **G1/G2 통과 기록은 없다**.
- 판정기는 명령 적분 odometry·필수 관측 누락·강제 정리·미회수 부모·cancel ACK/status만으로 PASS하지 않는다. `task8-verdict-red.log` 부재14실패 → `task8-verdict-first.log` 14통과. 수학 fixture는 실제 물리 증거가 아니다.
- G1용 한 발 제자리 교정은 validation_mode·실측 STAND·완료된 carry를 요구하며 기존 단일 다리 소유자만 명령한다. CRAWL 권한을 부여하거나 비영 이동 속도를 허용하지 않는다. kernel/실제 ROS 보고 경계 RED → `task8-contact-report-first.log` **28 passed/38.27초**. 실제 FJT 결과 보고는 UUID·typed result·future 완료·잔여 소유권을 구별한다.
- `prepare_navigation_model_13_5.py --scene-engine mujoco|gazebo`가 exact scene URDF에 결합된 offline profile을 만든다. `task8-prepare-scene-red.log` → `task8-prepare-scene-first.log` **2 passed/21.34초**. offline 상태는 native 허가가 아니다.
- 첫 MuJoCo 실행: `native-g1-mujoco-584c83b0-af5c-4d62-851f-b75154aa833f`, 내부 run_id `9dcf00ed-9073-4990-9c94-5ffceca95769`, 부모 PID1236/start17927·native PID1242. probe가 Jazzy의 dict 형식 MessageInfo를 객체로 가정하여 실패했다. native frame은0건이고 물리 인수로 세지 않는다. 종료 중 SIGINT **후** native controller 생성에서 context-invalid 예외가 발생했다. 주 원인을 MuJoCo ABI 오류로 단정하지 않는다. 부모 회수·잔여 없음이어도 native -6 종료는 정상 종료 FAIL이다.
- 이 경계의 실패 회귀는 `task8-first-native-regression-red.log`, `task8-child-exit-red.log`에 있다. dict/object metadata를 지원하고 잘못된 metadata도 executor를 파괴하지 않게 하며, 실제 소유 native PID의 부모 로그 종료 코드를 검사했다. `task8-native-boundary-green.log`: **19 passed/8.34초**.
- 두 번째 호출 `native-g1-mujoco-9e34cf5a-8376-41ee-8150-6287714a0fbf`는 **엔진 시작 전** 실패했다. `task8-scene-cache-load-probe.log`로 `/tmp/ch13_5_controllers_1927b0a9a09dae57.yaml` 소실을 확인했다. persistent bundle은 온전하며 OS 소실 원인은 단정하지 않는다. 이를 두 번째 물리 실행 실패로 집계하지 않는다.
- 수정 원리: persistent 파일들의 hash를 먼저 확인하고, 내용 hash로 도출한 정확한 소유 cache만 exclusive-create로 복원한다. 손상 cache·symlink·임의 대상·변조 원본은 거절하고 덮어쓰지 않는다. `task8-cache-lifetime-red.log`에서 소실/임의 대상 실패를 확인했다. 재개 후 첫 회귀는 JSON list/원본 tuple 비교라는 시험 표현 오류1건으로 실패했으며 원본 기록 `task8-cache-lifetime-first.log`를 보존했다. controller binding/실제 복원 bytes로 시험을 교정한 `task8-cache-lifetime-green.log`: **8 passed/30.05초**.
- **남은 인수:** 실제 native 센서 연속성·carry/발 lift·ctrl 실측·frame/힘/CoM/scan 의미 검증·정상 종료, 이후 양 엔진 G2. 누락된 check는 false로 유지하고 profile을 승격하지 않는다.
- 2026-10-23 설치 갱신: `task8-cache-fixed-build.log` 26.5초 성공, `task8-cache-fixed-install-audit.json` 8패키지 일치. 새 실제 실행 `native-g1-mujoco-ac9bc025-63bd-4ae0-a66f-c163edf2c5d6` (run_id `015c3bc8-36e7-44db-9400-716ad60d1be3`)은 TF 수신 metadata의 `publisher_gid` 누락으로 실패했다. 부모 PID1216/native1222/start43945, 수집 frame0. 잔여 없음·강제 정리 없음·부모 회수는 확인했지만 native -6이므로 정상 종료 FAIL이다.
- **가설 교정:** 앞선 dict 양성 fixture가 실제 API에 없는 키를 공급했다. 엔진 없는 실제 DDS characterization `task8-actual-tf-metadata.json`에서 Python callback 필드가 source/received timestamp와 두 sequence뿐임을 확인했다. graph에는 GID가 있으나 그것을 개별 TF 메시지의 출처로 추정하지 않는다.
- **최소 구조 보완:** Ch13 신규 C++ `tf_provenance`가 실제 `rclcpp::MessageInfo`의 GID를 읽는다. TF·모터·상태 명령을 발행하지 않고, 동일 topic/parent/child/GID만 중복 제거한다. 소유자나 부모가 바뀌면 반드시 별도 줄을 기록한다. 새 파일만 독점 생성하며 기존 evidence를 덮어쓰지 않는다. runner는 소스/설치 bytes·실행 파일 hash·소유 PID/start tick·실제 종료 코드를 함께 요구한다. Python의 API 기능 부재 자체를 로봇 fault로 해석하지 않되, C++ 증거가 없으면 TF 소유권 check는 FAIL이다.
- 회귀: `task8-tf-provenance-red.log` C++ header 부재 → `task8-tf-native-test.log` 실제 DDS **1 gtest passed/2.00초** (실제 publisher GID 대조·반복 제거·서로 다른 소유자/부모/static topic 보존). `task8-tf-boundary-red.log` 7실패와 `task8-tf-launch-red.log` 2실패 → `task8-tf-boundary-green.log` **12 passed/10.38초**.
- 별도 실행 파일 시험은 설치 전 binary 부재, 이어 peer의 explicit context/default executor 혼용으로 실패했다. 두 원본 로그를 보존하고 fixture executor만 동일 context로 맞췄다. `task8-tf-process-context-fixed.log` **1 passed/5.43초**: 실제 GID·기존 파일 거절/bytes 불변·소유 프로세스 SIGINT 종료0을 확인했다. 이 엔진 없는 성공을 전체 엔진 정상 종료나 G1 통과로 세지 않는다.
- TF 보완 후 고정 소스 `task8-tf-fixed-build.log` 두 패키지 build 성공111초. `task8-tf-fixed-package.log`: **196 tests/0 errors/0 failures/0 skipped** (Python179/116.50초 + 실제 native gtest11 + CTest wrapper6). `task8-tf-fixed-install-audit.json`: **8패키지 소스/설치 감사 통과**. 이 뒤 runtime을 변경하지 않고 새 UUID의 실제 MuJoCo 진단으로 진행한다. 최종 동결 전체13.3/13.4 엔진 회귀는 아직 아니다.
- 다음 실행 `native-g1-mujoco-407340de-1b07-4865-9ed6-e7693003ca82`, run_id `25c12e1f-0dfd-4525-a345-9fd5c85ad932`: 실제 native 관측과 TF 소유 관측기가 동작하여 bootstrap frame201건을 수집했지만, startup은 `crawl:body:wall_age`로 실패했다. 수납/정적10초/발 lift 단계까지 도달하지 않았으므로 G1 PASS가 아니다.
- 원본 시각 분석 `timing-analysis.json`: 최초 fault ROS12.564초에서 body 마지막 촬영12.384초, probe 수신 후 나이206.309ms. 같은 시점 IMU/접촉54.9ms·관절37.4ms였다. body의 최대 수신 공백342.539ms 동안 촬영 시각 증가는30ms였다. **전체 엔진 정지나 renderer 하나로 단정하지 않는다.** 원본 FreeJoint 발행과 Python 변환/전달 중 어느 경계의 지연인지 추가 계측해야 한다.
- 종료 증거: native PID1172/start95648·부모1166, TF 관측기1181은 모두 실제 종료0, 강제 정리 없음·잔여 없음·부모 회수 확인. 하지만 fault 이후 STOPPED를 확인하지 못해 서비스 기반 자원 정리 순서는 완료하지 못했다. 따라서 정상 runtime/engine 종료 인수 check는 FAIL을 유지한다. 종료 코드0만으로 성공을 덮어쓰지 않는다.
- 외부 고정 FreeJoint 소스를 **읽기만** 했다: SystemDefaultsQoS, RealtimePublisher `try_publish`,50Hz, 원본 ROS header 보존. 외부 원본 변경은 없다. 다음 계측은 `/native/free_joint_states` 원본과 `/odom` 변환 출력의 DDS source/received SYSTEM 시각·callback SYSTEM/첫 MONOTONIC 수신, 소유 PID/start tick의1Hz CPU/thread sample을 수집한다. ROS 시간과 wall 시간은 빼지 않으며 age200ms를 완화하지 않는다.
- 계측 부재 RED `task8-body-boundary-red.log` 3실패 → `task8-body-boundary-first.log` **29 passed/17.75초**. 관측기 자체가 두 번째 모터/TF 발행자가 되지 않도록 원본은 구독·로그만 한다. 실제 ROS 콜백 형식도 별도 시험 후 다음 엔진을 시작한다.
- 실제 콜백/시각 시험 `task8-body-transport-wire-first.log` **1 passed/10.80초**, `task8-body-trace-install-audit.json` 8패키지 감사 통과 후 새 실행 `native-g1-mujoco-60663048-a98c-4242-a536-abed2c9d4c41`을 수행했다. 이번에는 body-age가 아니라 STAND의 `stance slip`으로 실패했다. engine/runtime 코드와200ms·20mm 기준은 바꾸지 않고 실패를 보존했다.
- `body-transport-analysis.json`: 같은 촬영638개를 연결했다. 원본 발행→변환 출력 발행 최대18.381ms/p95 9.653ms, 원본 RMW 전달 최대14.653ms였다. 이 실행의 양호한 변환 시간이 앞선342ms 공백의 원인을 소급 증명하지는 않는다. probe dispatch 통계에는 종료 정리 구간이 섞여 있어 그 최대값을 변환기 계산 비용으로 해석하지 않는다. `process_metrics.jsonl`은 소유 PID/start tick·1Hz CPU/thread 기록이다. renderer 원인 단정이나 CPU 설정 변경은 하지 않았다.
- `stand-geometry-analysis.json`: 앞발 실제 접촉점 XY 이동20.039mm, URDF-FK 중심 이동20.043mm로 일치했다. FK/접촉 XY 차이≤2.617mm, URDF/native CoM 차이≤2.581mm였다. 따라서 이번 실패는 좌표 계산 착시가 아닌 실제 물리 미끄러짐이다. native/관측기는 종료0, 부모 회수·잔여 없음·강제 없음이지만 측정 정지 확인 실패로 전체 정상 종료 인수는 FAIL이다.
- 최소 재현 `test_gait_physics.py`는 **Python MuJoCo3.3.7의 실제 물리 component 시험**이며 ROS C++3.12.0 인수가 아니다. 정상 keyframe 초기화와 actuator ctrl만 쓰고 root pose/속도/외력을 쓰지 않는다. 첫 fixture의 contact.id API 오류는 `task8-physical-stand-red.log`에 보존했다. 접촉 인덱스만 교정한 `task8-physical-stand-red-confirmed.log`에서 같은 미끄러짐을 **3.08초**에 재현했다.
- 통제 실험 `stand-gain-probe-ec500876-eac4-4996-bbe3-ca58b041df67/comparison.json`: 동일 원본 모델의 메모리 복사본에서만 다리 kp 배율1/5/10, kv 배율1/√5/√10을 순차 비교했다. 힘·관절·ctrl 한계는 모두 유지했다. 원본은20.063mm 이동/0.07715rad 오차로3.08초에 실패,5배는5초 유지·3.581mm/0.01067rad,10배는5초 유지·1.648mm/0.00515rad였다. 성공만 추려 집계하지 않았다.
- 낮은 검증 배율5를 navigation 전용 `mujoco_navigation_actuators.yaml`에 채택했다. 기존 모델·팔·그리퍼·힘 한계는 수정하지 않았다. physics hash가 바뀌므로 이전 scene/profile로 재실행하거나 허가를 상속하면 안 된다. `task8-physical-stand-first.log`: 실제 물리 STAND·힘 제한·profile/장면/footprint **23 passed/23.44초**. **실제 ROS G1/G2와 Gazebo 동역학은 여전히 별도 검증이 필요하다.**
- G1의 누락 항목인 실제 native ctrl도 보완 중이다. `task8-native-controls-red.log`는 원본 상태 읽기 기능 부재, `task8-native-controls-probe-red.log`는 수신기 부재를 확인했다. probe 수신/실제 DDS 회귀 `task8-native-controls-probe-first.log` **9 passed/10.90초**. native source는 같은 소유 snapshot에서 ctrl/qpos/qvel/actuator_force/qfrc_actuator·단위·gain·명시 주소를 읽으며 명령 토픽을 실제 제어값으로 대체하지 않는다. C++ 첫 빌드의 `mjNGEAR` 오류를 고정3.12.0 헤더의 실제6열 gear 및 nactuator/nu/nout 주소 계약에 맞춰 교정했다. **native_ctrl_observed check는 의미·출처 검증 완료 전 false를 유지한다.**
- 이후 `task8-load-fixed-build.log` 두 패키지 빌드는 성공했다. `task8-load-fixed-package.log`는 **204건 중 1실패**(실제 native gtest13 + wrapper6 통과, Python185 중 generation 변경 시험 실패)로 종료되어 설치 감사와 다음 엔진 실행을 보류했다. 세대0/MOVING의 마지막 발행만 확인됐으며 입력 콜백 부재라고 단정할 증거는 없다.
- 재개 후 진단 정보를 추가한 단독 `task8-generation-characterize.log`는 1통과/9.47초였다. 파일 단위 `task8-generation-full-characterize.log`에서는 세대 변경 시험은 통과했으나 실제 속도 settle/고착 팔 timeout 시험이 `guard:ros_age`로 2실패/10통과(52.51초)했다. 시험용 원본 발행 공백 **213.6852ms**가 관측되어 200ms 차단 자체는 옳다. 다른 실패를 같은 결함으로 합치거나 통과 실행만 추려 세지 않는다. 다음 판별은 시험 발행 전후 MONOTONIC/스레드 CPU와 실제 상태 이력이며 엔진을 시작하지 않았다.

## 2026-10-25 G2 전송 경계 및 결정 프레임 판별

- 후보 whole navigation/runtime617/617 PASS358.90초 이후 trace-only 관련22PASS44.62초,
  새 G1 `0374f925-dc3f-4b46-b558-9e4a231b508f`23/23 PASS, 정상 종료/reaped/noforce/residual[].
 118소스 manifest46b8df5b585ac6eb97f82b3bafb35211095f4d171475a96cd91430a58c0b13db.
 ZIP8,820,217bytes SHA92fe4924da3c7f2b192834c660a0ba475f46a71ff0ddbd15c06a461db78072e7.
- 동일 설치 G2 `04d65307-094d-4bda-9216-84e8353826d0` FAIL: native movement body:ros_age가 최초.
 정리 중 raw:ros_age/measuredSTOP/deactivate FAIL, carry terminal/native stop/consumers/engine0/parent 회수,
 forcedfalse/residual[] 확인. ZIP28,611,118bytes SHA0830bd51469fd488f5ec8a4aa96b15cd7a78ecf3cad2a8dafa28a1ff2d6446b0.
- postmortem은 전량 journal의 원래 DDSsource/RMW/callback 시각과 nativelease/capture를 사용한다.
 body DDS.124ms vs콜백182.645ms; 190ms 기록 프레임 생성 뒤 더 새 body가 도착했으나 runner는
 옛 기록 프레임을 나중 ROSnow로 재검사했다. 기본시계·촬영·200ms 기준 변경 없이 결정의 원자성을 수정.
 RED1FAIL9.21초(구 runner 경로 만료 재현 포함)→최신 관련25PASS21.62초/설치 감사8PASS.
 수정 후 실제 G1/G2는 별도 UUID로 평가하며 이 항목은 G2 성공 증거가 아니다.

## 2026-10-25 관측 결정 수정 후 실제 관절 도달 범위 판별

- `4e7ee50b` G1 23/23PASS/normal/reaped/noforce/residual[],118manifestd044e1588f302cfa68fd4f92ccdfa3913e5ebf8100198a62b2a5b1129db5aece,
 ZIP9,118,432bytes SHA4778b7a1de5fe2e2d2972778327bbf02a2a266769e1bc65f433877e155bbaee8.
- 동일 소스 G2 `3127f15e`FAIL349.300ROS/~.268m: FL명령calf.79980582<.8, 실제q.80232187은 별도.
 measuredSTOPFAIL, deactivate/carryterminal/nativeworker/consumer/engine0/parentreaped/noforce/residual[].
 원본 ZIP160,160,295 localonly SHA2d16f8e40d0275f19b376edf64ad478894ccadd5b0387c0440baa431c499a54f,
 72MB/72MB/16,160,295bytes 조각과 연결SHA 검증. 원본·분석 모두 보존.
- 기존 이상적0.45m 수식 재생은18,746tick PASS. 실제 preload/tracking/support 결합 문제와 구분한다.
 CHAMP pinned core zero_stance/half stance 원문·BSD3 확인/외부 코드 복사 없음.
- 새 중립 SE2/사전8cm 목표 후보 RED첫lead73mm vs중립44mm→초기관련22PASS후후발다리strideFAIL→
 거리예산을 목표 생성에 적용해44PASS48.59초. 실제 실패 형상3PASS5.85초, 기존 G1/착지33PASS25.21초.
 Nbuild14.5초/8auditPASS, 새 G1 `5ea905a9`23/23PASS/normal/reaped/noforce/residual[].
 118manifest9e42586f4a93592c7f561d25d6f6b2cab34981968e27cf35d4b9d4dc9a6ade18,
 ZIP8,815,573bytes SHA79ed3e9a019ff8ea4baa4d6db307c367cf13a993a86da38eed2c99b8de79c8f2.
- 같은 소스 G2 `46921c07`진행 중. 이 항목은 G2 인수 성공 또는 현재 전체 회귀 통과 선언이 아니다.

## 2026-10-25 실측 CoM 재계획 및 G1 복귀 충격 후보

- 46921c07 실제형상에서 predicted27.172mm vs actual9.877mm, RR8.163N/상승6.644mm/6.02초를 확인.
 실제형상 RED에서 ZEROshift 선택을 재현하고 normal CRAWL의 measuredCoM+IKdelta로 수정.
 1후보/tick/G1분리/기존한계 유지, 관련48PASS59.62초/Nbuild11.4/8auditPASS.
- 새 G1 8d7b5fd1 FAIL35.742ROS CALIBRATING gripper±.00514751>.005. 원본 sample age2ms,
 arm속도<.011/오차<.02, native gripper ctrl.015/.015. measuredSTOP/deactivate/terminal/nativeworker/
 consumer/runtime/engine0/reaped/noforce/residual[] 정상. 전체 G1 FAIL은 보존한다.
 118manifesta0d51d25827fedd7b8fb85438549974b1706d32946e21546649656f5633879f3,
 ZIP9,627,482SHA567a7ca91b55fe11b5907127ae8d91b517aff4e4259a577e1e13164c7e47fe21.
- 복귀 accel불연속 RED jerk10m/s³7.35초. 기존v.02/acc.2에서 quintic velocity와 정확한 적분,
 peak/시간을 해석적으로 선택하는 후보로 수정. 접촉 후 originalpreload완주/4N3고유착지/
 full1wall초settle/10wall초 유지. 기존회귀+PythonMJcomponent23PASS20.09초.
 nativeG1 새 실행 진행 중이며 물리적 인과/성공은 아직 판정하지 않았다.

스캔 직접 계측과 Probe 실행기 수명 관련28PASS28.73초/설치 감사8PASS 후 새 G1
`09711391-a45c-4d08-ade4-fb68abf647f0`이23/23 PASS했다. 실제 수신 실행기는 EventsExecutor로
부모PID/스레드ID/설치 dependency fingerprint와 함께 기록됐다. 손가락 최대3.01630mm/s,
carry raw/owner와 freshness 모두 PASS, measuredSTOP/deactivate/terminal/runtime/engine0/
부모 회수·강제없음·잔여[]를 확인했다. 한 번의 G1 성공을3연속이나 G2/13.5 성공으로 확대하지 않는다.
118source manifest `4d84751c7591b41f9c0d115fa2df11dbd1fdf8cf98d191f9c14625d471e64f51`,
ZIP9,333,064bytes SHA `092a47e162587c7a5566b9092eb4c6d9c108e5185d1ebc07cd2fae22cc85ce84`.
같은 모델/소스/설치의 G2 `f4157cd3-e73c-4558-8533-f0d9ee06f9f2`를 순차 실행 중이다.

## 2026-10-25 명령 시계 역행·단계 정지 의미 수정

- 실제 f4157cd3 G2는 FAIL. 약0.40665m 전진과1ROS/wall초 정착은 달성했으나 중간 STAND가 명시 stop latch를 걸어 좌회전이 시작되지 않았다.674.228ROS초 첫 stop은 final_command:ros_age. 원본 SYSTEM−MONO offset−2166.639ms/DDS source약−2140ms 역행, raw송신최대gap43.873ms/GC12.378ms/guard신선함을 확인. 스레드 정체 단정은 기각했다. OS 조정 주체는 미확인, 시스템 변경 없음.
- 원본 FAIL/정상 프로세스 종료와 measuredSTOP cleanup FAIL을 분리. ZIP295372609bytes 로컬 보존 SHA ba0c8bfde115cb11d2241b7a17cf9c06dcd465420e689aae19284fd300aaa75b;72MB 분할5개/연결 SHA metadata 보존. 소유 SIGINT helper는 이미 종료한 실행을 발견해 신호 전에 거부했으므로 실제 신호 없음.
- 중간 단계는 건강한 CRAWL0속도+원래 실측 settle, 명시 STAND는 최종에만.2초 안에 실제 CRAWL 미확인 시 failfast. 코어 fault/명시stop latch 자동해제 없음. RED→9PASS11.26초.
- command_order는 실제 DDS publication_sequence_number로 순서 판정, 원본source/RMW/Sample metadata와 기존source epoch cutoff/ROS·wall200ms 유지. 누락·중복·old epoch는 receipt 갱신 없이 거부. 감지된 SYSTEM backstep 후 RESET/다음 활성화는 receiver 재시작 요구. 메타데이터 제어 회귀RED12.10초→관련26PASS43.77초→coldactivation/기존lifecycle/guard/소유권 포함45PASS84.11초.
- N build11.5초/eight-package 감사PASS.119소스 새 MuJoCo G1 776ece6c-ea5f-481c-90a3-c1898d0d2ff8는23/23PASS. measuredSTOP/deactivate/carryterminal/nativeworker/consumer/runtime/engine0/parentreaped/강제없음/잔여[] 확인.
- source manifest b22d1862c313b069613caf31d928db24ecbfb5d881c0d389a525e3d211fe6883. ZIP10334954bytes SHA c2f41ae725d7f2be1cbd5116df95f7d0cecfd18f03f54b17bddb61981a01d42b. 원본과 압축 전량해시 검증. 이 한 번의 G1 성공은 G2/3연속/13.5 완료가 아니다.

## 982b8ca2: 회전 중 비인접 허벅지·몸통 접촉

119소스 manifest b22d1862c313b069613caf31d928db24ecbfb5d881c0d389a525e3d211fe6883의 G2는 FAIL했다.
좌회전이 실제 시작돼 약0.198rad까지 진행했으나485.724ROS초 contacts의 unexpected_contacts=1,
485.752ROS초 첫 controller fault였다. 관절/몸체는485.744ROS초 표본으로 약20ms 차이가 있다.
Python MuJoCo3.3.7에서 그 원본 관절·몸체를 재계산하면 rr_thigh_link/base_link 간섭38.4986µm가
나온다. 이는 오프라인 형상 진단이며 ROS C++3.12 엔진의 접촉 쌍을 직접 계측한 결과와는 구분한다.
세계의 벽은±4.7m이며 해당 위치는약(0.413,-0.046,0.459)m다. 장애물 높이나 접촉 필터를 바꾸지 않는다.

별도 전체0.30rad 이상적 회전 회귀는 좌회전 성공/우회전 SHIFT에서 rl_thigh_link 간섭274.477µm로
실패했다(1FAIL/1PASS21.19초). 따라서 물리/관측 지연만으로 설명할 수 없고 원래 계획의 기하 결함이다.
기존 계획은 지지 여유·관절 제한만 확인했으며 예정된 몸체 회전과 비인접 허벅지/몸통 간격을
동시에 검사하지 않았다. 원본 URDF 원기둥을 capsule로 감싼 보수적 간격 계산을 추가하는 RED 후
실제 실패 형상·네 다리 native 형상 대조·기존 IK12PASS12.98초를 확인했다.
계획 수정은 일반 CRAWL에만 적용하고 G1 교정 궤적/기준은 유지한다. 새 실제 엔진 인수는 미검증이다.

실제 실패의 carry terminal/deactivate/nativeworker/consumer/engine0/부모회수/강제없음/잔여[]는 확인했다.
그러나 measuredSTOP과runtime 정상 인수는 FAIL이므로 전체 정상 종료 성공으로 쓰지 않는다.
압축본231241893bytes SHA f0308b4d6bef8c5f60d1027e249dab30ad2a10462aff548d65a4cde18614aa7d,
원본 ZIP은 로컬 보존하고72MB 분할4개와 연결 SHA metadata를 보존한다.
사후 파생 분석은 task8-982b-unexpected-contact-derived.json SHA
2aa59f75521137638f26e50db92bca4c08aaf5a38d153baf6006c7ecd5643757이며 원본 copy ledger에 끼워 넣지 않았다.

## 시험 송신자의 대기 경계: 전체 회귀 실패를 숨기지 않기

일반 crawl 구조 수정 후19관련PASS53.72초였으나 전체 navigation은38PASS 뒤 기존 carry 정착 timeout 시험에서 guard:wall_age로 FAIL95.49초였다. 같은 시험만 분리해도 FAIL29.37초였다. 두 실패 모두 보존했으며 허용 fault를 늘려 통과시키지 않았다.

첫 carry-wire-trace-3b6f557b 원본에서 guard 수신 후217.432716ms, 송신자의20ms 대기 구간273.344956ms/CPU0.3944ms를 확인했다. 두 번째 ea38aa37 역시211.2919ms/송신 최대278.5868ms였다. 제어 계산 비용과 구분했다.

세 대기 방식을 같은 프로세스의 세 스레드에서40초 비교한 task8-wait-latency-fefad094-e578-4fb0-9381-7c1bae364b66.json: multiprocessing.Event만305.3668ms(CPU0.2297ms), time.sleep21.8855ms, threading.Event21.1879ms였다. boot_id는 비교 시작·끝 동일했다. 해당 지연의 SYSTEM−MONO 순변화는−1.561287ms여서305ms 전체를 시각 역행량으로 단정하지 않는다. 일반 사용자 CPU 대기/부하도 읽었고 관리자·시스템 변경은 없었다. Windows CIM 읽기는 접근 거부돼 추가 권한을 요청하지 않았으며 대체 실측으로 진행했다.

CPython3.12.3 [multiprocessing semaphore.c](https://github.com/python/cpython/blob/v3.12.3/Modules/_multiprocessing/semaphore.c)와 [synchronize.py](https://github.com/python/cpython/blob/v3.12.3/Lib/multiprocessing/synchronize.py)를 읽어 이 경로의 realtime 기반 timed semaphore 계약을 확인했다. 외부 Python 소스 수정/복사 없음. Linux 커널 내부의 이번305ms 지연 원인을 확정한 것은 아니다.

최소 수정은 시험용 carry_feedback_peer의 주기 대기를 time.sleep(.02)로 바꾸는 것이다. 같은 stop 플래그는 다음20ms loop에서 확인하고 새 캡처·원래50Hz 목표/원본 timestamp를 유지한다. catch-up/재태깅/제품 변경/200ms 완화는 없다. 기존 stuck-arm 정착 timeout·실제 입력 손실·독립 송신3PASS42.16초였다. 전체 navigation은 고유 로그 task8-intermittent-navigation-monotonic-full로 별도 실행한다. 기존 두 FAIL을 제외해 전체 PASS로 계산하지 않는다.

## 동시 수신 안전 시험의 발행·수신 경계 교정

두 번째 전체 회귀 task8-intermittent-navigation-monotonic-full은137PASS 뒤 동시 입력 시험에서 FAIL205.69초였다. 이 시험은 오류 뒤 발행 금지를 수신 개수로 판정했다. 오류 이전 정상 메시지를 명시적으로 DDS 큐에 남기는 최소 재현을 추가하니, 실제 발행 호출0건인데 수신7→8건으로 기존 assert가 FAIL했다(10.97초). ingress-publication-boundary JSON은 ingress_seen=true/states=[STAND]/actual_publications=[]를 보존한다. 원래 제품의 소유 모델은 입력 callback에서 변하지 않았고 tick이 latch를 관측해 FAULT로 전환했다.

제품 코드는 바꾸지 않았다. 시험은 실제 Publisher.publish를 전달·계측해 오류 입력 이후 새 호출이 없고 이후 신선한 입력에도 FAULT가 유지되는지를 검사한다. 정상적인 이전 DDS 메시지 지연 수신을 새 명령 발행으로 오인하지 않는다. 입력 callback이 모델 lock을 기다리지 않는 기존150ms 검사·실제 engine epoch fault·단일 소유권 검사는 유지한다. 기존 FAIL을 지우거나 허용하는 fault를 늘리지 않았다. 관련 회귀는 별도 고유 로그로 기록한다.

## 현재 전체 회귀와 종료 경고 처리

수정된 송신/발행 경계의 전체 task8-intermittent-navigation-boundary-full은597PASS392.63초였다(JUnit XML·개별 소요시간 보존). 다만 test_control_clock_dispatch의 background spin 종료 경고와 뒤늦게 수집된 미처리 coroutine 경고2건을 숨기지 않는다. 해당 시험은 별도 spin 스레드가 돌고 있는데 실행기 풀부터 닫았다. 생산 실행 경로처럼 dispatch를 먼저 중단·wake·join하고 그 뒤 pool을 drain하도록 시험만 수정했다. 예외를 수집해 assert하므로 단순 경고 억제가 아니다. 관련29PASS11.60초는 -W error 조건으로 확인했다. 런타임 변경은 없으며 최종 동결 전체 회귀는 실제 게이트 뒤 별도 기록한다.

## 정적 crawl 후보의 계산 예산·정지 표류 추가 확인

- task8-intermittent-kernel-351bcacd-768f-45cd-a33f-5a8c2b19fac6.json: 이상적 우회전−0.3002556rad/6978tick, 전체 wall 최대8.285674ms/p99 3.356743ms, CPU최대8.2764ms. 계획 CPU최대5.4757ms. 별도63반평면 투영100회 CPU최대10.8308ms. 이 회전에서는 fallback 호출0건이므로 실제 fallback 소요를 그 회전의 tick 비용이라고 합쳐 주장하지 않는다. ROS scheduling/native50Hz 보장은 별도다. 세 소스 SHA를 포함하며 본 결과는 실제 엔진 인수가 아니다.
- 기존5cm yaw 표류 기준을 참조 궤적의 정상 pause/STOPPED까지 추가 확인했다. 첫 추가 시험의 NumPy import 누락(NameError)만 수정했으며 제품 변경은 없다. task8-intermittent-turn-stop-drift-corrected는좌우2PASS34.86초. 기존 실제 G2의 위치/각도/표류 인수는 새 엔진 결과로 별도 확인한다.
- 현재 N build/8패키지 설치 감사 후 새 고정 소스 G1을 진행한다. 이전776ece6c23PASS는 새gait 변경 전이며 현재 source proof로 재사용하지 않는다.

## 새 고정 intermittent 후보의 실제 G1과 G2

- MuJoCo G1 49225530-989e-47cb-9957-a7e65b25fd6c:23/23PASS. 실제 measuredSTOP/deactivate/carryterminal/nativeworker/consumer/runtime/engine0/부모회수·강제없음·잔여[] 확인.
- 119source manifest f04031bd899108e72b670d69c30fdb54b0445c4782b37caac9854aa130e0551d. source HEAD4e87f6f6031d0ac5e73b2575bcee261e92a0e59e의 고정 작업트리 bytes를 보존했다. ZIP10012140bytes SHA e18f92816769507eaf00d481974e9dfdd97fc22172caedf53d2e76b05a4e601e. 원본/압축 모든 member 해시 일치.
- 동일 실제 G1 장면·설치·환경에 연결한 G2 a0631dc8-5dcc-4dd6-8ab3-3dfac2b1ac17를 순차 실행한다. source/설치/시험을 고정하며 다른 엔진/CPU 회귀는 실행하지 않는다. 이 항목은 G2 성공이 아니다.

## a0631dc8: 실제 입력 도착과 관측 callback 실행의 차이

새 intermittent119소스 G1 49225530은23/23PASS였지만 동일 source G2 a0631dc8은126.051999999ROS초 이동 판정에서 contacts:ros_age로FAIL했다. 선택 접촉 stamp125.838/sequence5755, ROS age213.999999ms·수신 후wall127.611347ms였다. body age166ms, 제어기 first_fault/first_stop은null이고 carry는READY였다. 실제 G2의 stopped/forward/left/right/sensor_freshness/native_ctrl_observed/joint_tf_ownership은 완료되지 않았으므로 통과로 쓰지 않는다.

같은 lease5755는 DDS발행→RMW0.1663ms, RMW→Probe callback127.466747ms였다. native free body의 capture 차이−1ns에 따른 발행 시각 대조는약0.0994ms(생산 지연의 근사값)다. 다음 접촉5757/stamp125.912는 DDS0.157ms/RMW→callback216.813ms이며 callback wall386946244336은 거부 판정386904585751 이후다. 더 최신 입력이 middleware에 먼저 있었어도 application callback이 처리하기 전이었다. 원본 시각을 바꾸거나 늦게 처리한 값을 과거에 받은 것처럼 간주하지 않는다. controls 같은 lease와 native body 출처를 포함한 derived-decision-boundary-native-g2-mujoco-a0631dc8-5dcc-4dd6-8ab3-3dfac2b1ac17-v2.json에 보존했다. 첫 v1 파생 결과는 native 폴더에 별도로 남아 있다.

GC 최대6.585927ms, 실패 전후1초에 해당 GC span은 없었다. 따라서 이214ms를 GC 하나나 llvmpipe 하나의 원인으로 단정하지 않는다. callback 대기 자체는 확인했지만, callback 내부 CPU/lock/기록I/O와 다른 프로세스 부하는 아직 분리 측정이 필요하다.

G2 FAIL과 별개로 실제 measuredSTOP/deactivate/carryterminal/nativeworker/consumer/runtime/engine0/부모회수·강제없음·잔여[]를 확인했다. ZIP53958191bytes SHA856baf6f7af575aac4f8c9b676e84a946e1402c39e8fac86134c866f59259e56, source manifestf04031bd899108e72b670d69c30fdb54b0445c4782b37caac9854aa130e0551d. 원본 실패/고정 소스를 보존했으며 성공 실행으로 세지 않는다.

다음 판별용 계측은 Probe callback의 wall/CPU/lock wait 집계, 기록의 직렬화/쓰기 비용, 실패 시512개 slow callback snapshot, 부모 observer의 소유 PID/start tick·CPU를 추가한다.5ms는 계측 보존 임계값이며 안전 기준이 아니다. slow ring의 누락 수를 명시하며 전량 원본 journal은 유지한다. 시계/QoS/age/제어/실행기는 그대로다. controlled15ms 계측RED11.95초 후 기존 SimpleNamespace fixture의 새 인터페이스 초기화를 바로잡아 관련36PASS31.22초(-W error)였다. 원인을 이미 해결한 것으로 선언하지 않고 새 실제 source/install 감사와 G1/G2로 판별한다.

## 관측 비용 계측 source의 실제 G1

abb04d17-32f2-48d4-bb12-a91a12d46862는23/23PASS, 실제 measuredSTOP/terminal/runtime/engine0/회수·강제없음·잔여[]다.119source manifeste49b7557431cc4cf5caa722430e4a4d0c11e5a4874ad2accc8be6352ae8650c1, ZIP8813421bytes SHA3f27bdb7b79bb03eb19a5d2d894a865819204ee63d1a28182ad285ab030d6604.
G1 controls callback wall4.649s/CPU1.345s, frame callback wall4.351s/CPU1.744s。frame 기록 write최대28.5603ms, controls write최대24.1328ms였다. G1은MNTc, 다음G2는EXT4이므로 이 수치를 G2 실패 원인으로 바로 가져오지 않는다. 동일 source/scene/install G2 d6715c71-62bc-4244-bc7a-5b07495129ac를 순차 실행 중이다.

## d6715c71: 수신과 기록 I/O 결합의 분리 실험

G1 abb04d17은23/23PASS였다. 같은119소스 G2 d6715c71은188.108ROS초에 접촉 stamp187.906의 age202ms로 최초 거부됐다. 수신 후wall48.815ms이며 body age136ms였다. 원본 명령6162건의 최대 송신 간격94.113192ms로, 최초 원인을 명령 생산 중단이라고 쓰지 않는다. 종료 중 raw:wall_age가 추가 발생해 measured_stop/deactivate/runtime 정상 종료는FAIL이다. 엔진exit0·부모회수·강제없음·잔여[]는 확인했다. ZIP77711915bytes SHA7319cf77c40786fd1579b56c10a2bca5da0a616f08a97cd5cd486c1398f9c2e2와 파생 분석을 보존했다.

새 계측상 frame 기록 write최대181.556882ms/직렬화31.195988ms, native_controls write최대48.494713ms/직렬화36.9921ms였다. 실패 직전 controls callback49.455438ms, frame12.701699ms, joints19.708155ms 등 지연이 연속됐다. frame193.362198ms는 최초 거부 이후224.231811961wall초에 시작하므로 최초 실패 원인이라고 소급하지 않는다. 이는 별도의 종료 지연 기여 가능성이다. CPU시간이wall보다 큰 일부 WSL측정도 있어 개별 CPU값만으로 스케줄링 원인을 확정하지 않는다.

### 승인 범위 안의 최소 구조 변경

가설: 실제 관측 callback이 원본 JSONL 쓰기까지 inbox잠금 안에서 수행하므로 디스크 지연 하나가 후속 수신을 막는다. 느린 sink를Event로 정지한 최소 회귀에서 callback완료/잠금 획득을 검사한 뒤 수정한다. 모든 runtime/Crawl/시계/QoS/200ms/300ms/캡처시각은 그대로다.

G2의 bounded_history모드에만 기존 형식의 직렬화된 불변문자열을 유계 writer에 비차단 제출한다. 작업자는 파일쓰기만 소유한다. 기본256레코드/8MiB(in-flight포함), overflow/쓰기오류는sticky FAIL이며 레코드 덮어쓰기·누락·재시작은 없다. callback진입 순서대로 제출하고 종료는 수신join→새제출차단→전량drain→파일flush/close→writerjoin→전량원본복원/개수검사다. 완료확인 전 최근cache만으로 평가하지 않는다. writer보고서에 제출/쓰기/최대대기량/에러/join과 실제I/O시간을 남긴다. 원본G1의동기기록은 유지해 실험범위를 제한한다.

파일쓰기만 옮기므로 JSON직렬화·프레임복사·DDS대기·다른프로세스부하가 해결됐다고 주장하지 않는다. 최소회귀 통과 후 관련시험/설치감사/새G1→같은소스G2로 실제효과를 판별한다. G2실패 시 같은실행을 성공으로 세거나 관측age를 완화하지 않는다.

## 재개 상태: G2 기록 I/O 격리 후보

- 새 G1 abb04d17:23/23PASS. 동일소스 G2 d6715c71: 최초contacts ROS age202ms로FAIL; 종료중raw wall age로measuredSTOP/deactivate/runtimeFAIL. 엔진exit0/회수/강제없음/잔여[] 확인. 최대 명령송신간격94.113192ms로 생산중단 단정 불가.
- 원본77711915bytes ZIP SHA7319cf77c40786fd1579b56c10a2bca5da0a616f08a97cd5cd486c1398f9c2e2 보존. callback안 기록쓰기최대181.556882ms는 최초실패 이후이며 최초원인으로 소급하지 않는다.
- 느린I/O로수신잠금막힘RED9.80초, 유계계약RED8.96초 뒤G2전용 불변encoded원본기록 worker 구현. 관련16PASS24.34초+실제DDS/원본transport/G2binding/종료25PASS32.53초(-W error). 최초5PASS뒤burst용량FAIL15.63초도보존.
- 실제새G1/G2효과는 검증전. 현재Task8 G2전체PASS없음. Nav2Tasks9–14/양엔진연속3회/최종전체회귀/commit·push는아직미완료. 사용자13.4교육문서40723bytes는수정하지않았다.

G1fe1496cd23/23PASS/정상STOP·terminal·runtime·engine0/회수·강제없음·잔여[]. ZIP9146720 SHA b07ed5477a8e95a8126739330381eadae1cafd85efe6ee1074b59d44246c2895; source119 f633a4497a368aae64479b2027faf51e9aecb54d357697174ec54024fef246d4. 동일 준비장면 G2 7e11d735-9e57-4cba-ac59-c2307e364d3a 순차 실행중. 실패를 성공으로 계산하지 않음.


## 7e11d735: I/O 격리는 확인, 입력/처리 실행 경계는 남음

새source119/f633a449 G1fe1496cd23PASS 뒤 동일G2는111.225999999ROS초에 contacts stamp111.012의213.999999ms/receiptwall99.085047ms로FAIL했다. body age144ms/receiptwall1.556591ms. 같은 접촉4965 DDS2.015658ms/RMW→callback107.717571ms, 다음4968/stamp111.118은95.384648ms 후callback으로 판정후도착했다. producer lease가4965→4968로 건너뛰어 application처리뿐 아니라실제생산/도착간격도분리해봐야한다. 큐 크기·callback부재·한스레드만을전체원인으로단정하지않는다.

기록기87762제출=87762쓰기/peak126레코드243350bytes/오류null/jointrue. 실제I/O최대172.5907ms는여전히존재하지만inbox잠금밖이다. 이번실행정상STOP/deactivate/carryterminal/nativeworker/consumer/runtime/engine0/회수/강제없음/잔여[] 모두확인. 전체G2는FAIL이고연속성공으로세지않는다. ZIP40943053SHA2348062487c6fc279aef77aae1aa5eb803ddf130a1cb3d8935025b77f780e9e1. 원본및transport파생자료보존.

프로세스계측에서실패근처observer1.135논리코어, 엔진1.923, crawl.944, guard.650 등최소약6.36코어를사용했다(100Hz/proc USER_HZ, owned프로세스만집계). i7의4물리/8논리코어와실제보장시간은다르며전체호스트상태를증명하지않는다. 부모평균.845코어이므로파일쓰기만분리해도다른Python계산·실행큐의지연이남을수있다.

다음가설: G2관측기의기본serialEventsExecutor에서무거운frame/controls처리와native입력/clock이한실행경로를공유한다. 느린frame기록직렬화경계를주입해실제DDS입력진행을검사한다. G2에만이미Ch13에서검증한2-worker drain실행기와독립MutuallyExclusive그룹을적용한다. 기본그룹은clock/센서/서비스수신,별도그룹은frame/controls/TF기록처리다. frame은좁은잠금으로불변snapshot을선택한뒤직렬화/제출을잠금밖에서수행하고controls도parse/직렬화는inbox잠금밖으로옮긴다. 공유카운터/기록순서는별도기록잠금으로보호한다. G1기본serialEvents·명령송신소유자·모든시각/QoS/물리계약은유지한다. 이는우선순위/하드실시간보장주장이아니며최소회귀→관련실제DDS→감사→새G1/G2로판별한다.

입력/처리분리20PASS64.89초(-W error): 과거inbox전체잠금·직렬화record잠금counterfactual둘다수신잠금차단확인,새경로는같은JSON처리250ms대기동안원본DDS촬영갱신/receipt100ms이내. 기존유계캐시전량복원/오류/큐초과/join/신선도거부모두유지. 이전5PASS후첫sample선택전제FAIL29.26초와6PASS후selected캐시비교FAIL36.79초도보존했다. 소스구조효과와실제G2성공은아직별도검증이다.

수신/처리그룹분리최소20PASS64.89초,확대27PASS뒤fixture_lock누락FAIL36.17초,동일native_probe13PASS10.51초(-W error). 여덟패키지설치감사 task8-probe-processing-group-install-audit PASS. 새고정소스G1→G2진행,이전G2성공없음/새효과검증전.

새G1d3f8f61f23/23PASS/정상STOP·terminal·runtime·engine0·회수·강제없음·잔여[]。ZIP10169092 SHA1c106cfbdb8d7591598d6f723aa300a128ed894eeaf5891e9575445193e23b6a/source119 manifest88c5539fc1f7316630eed7d1d0470cf82a5a1c597aa81703dae02b7c4487ecf6. 같은장면G2 42c6ad25-0f66-462f-9cb0-f4fbb82ec614 실행중(입력/기록그룹분리). 원격13-5 ref조회는기본환경443연결실패뒤승인범위읽기전용재확인으로성공/해당ref없음. push/merge/force는수행하지않음.

## 42c6ad25: 두 worker 후보 실패 보존과 다음 구조 선택

새G1d3f8f61f23PASS 뒤고정119/88c5539f G2는최초native movement body:ros_age로FAIL했다. 종료관측의imu:ros_age는최초실패라고소급하지않는다. precleanup controller_report.first_fault는null이며이후raw:ros_age가STOP/deactivate를거부해runtime정상종료는FAIL이다. writer23994=23994/peak42/jointrue, engine0/회수/강제없음/잔여[]를확인했다. ZIP9945608SHA31044fb137e81f7be7b39466dc7b2d4490bc091c7b9addbde3b1b649ff1785a8. 기록I/O와처리잠금의단위격리성공을native G2성공으로대체하지않는다.

기존관측Events→2worker변경은입력과처리의동시진행을허용하지만500Hz시계등의pool handoff비용도추가한다. 이비용이이번실패의전부라는측정은아직없다. 같은구조를더많은thread로덧대지않고,기존13.4 ArmActionTransport의저교통독립ROS수신노드·별도실행기·같은context/명시적join패턴을재사용하는다음판별후보를선택한다(Ch13내부원본열람,외부코드복사없음).

G2에만입력NavigationProbe와기록전용NavigationNode를분리하고각각기존serial EventsExecutor를소유한다. 기록노드는use_global_arguments=False/use_sim_time=False로새clock구독을만들지않는다. frame timer에는기존Probe ROSClock을명시적으로사용하므로원본시각/50Hz목표는동일하다. runtime/controller/command/TF생산자를추가하지않는다. 실제native_controls/TF구독과frame처리만기록노드로옮긴다. 앞서검증한좁은inbox잠금·잠금밖deepcopy/JSON·유계writer는유지한다.

ProbeReceiver는두소유thread의stop/wake를먼저수행하고둘다join한뒤각executor를닫는다. child오류는sticky상위check실패로전파하며자동재시작하지않는다. 미회수thread가있으면ROS핸들/로그를닫지않는다. 기록노드는기존clock참조의수명보다먼저destroy한다. 기본G1은기록sidecar없이원래serial관측기를유지한다. 두실행기라서하드실시간/CPU상한이보장된다고주장하지않는다. 최소실패시험/기존실제DDS/설치감사→새G1/G2로판별한다.

두serial관측실행기RED14.18초→관련22PASS52.94초(-W error). 종료미확정/기존G1단일실행기/원본transport/오류고착/소유권/기존G2·종료확대36PASS33.34초. metadata-only수동실행기fixture는기록Node도명시적으로add_node하도록수정했다(수신worker실제분리시험은별도유지). teardown.probe_receivers에입력/기록node·thread ID/alive/closed/error를각각기록한다. 같은context/부모원본ROSClock하나와모든원본capture/age계약유지. 새후보실제엔진검증전이며기존42c6ad25실패를제외하지않는다.

## 76473ca6 G1 실패: 공통 acceptance 관측기에도 기록 격리 적용

G2용새후보를검증하려던G1은22/23이었다. scan신선도만FAIL이며stand32513999999ROS의scan32164000000은age349.999999ms/receiptwall118.366142ms,calibrate39588의scan39278은age310ms/wall15.122984ms였다. 다른물리·파지유지·actual lift30고유촬영·안전·정상STOP/terminal/runtime/engine0·회수/강제없음/잔여[]는PASS. 전체G1은FAIL이며동일소스PASS실행을골라재시도하지않았다. ZIP10370977SHA05ef1d81d94852f81f71616511294261953331ad87b2ba16964ab7695e56250e/source119cf129153. 보존후추가한frame-freshness-analysis는사후자료임을구분한다.

선택scan32164의DDS0.074525ms/RMW→callback223.702325ms,다음32278은220.275367ms로거부이후callback이었다. 두번째선택39278도DDS0.074433ms/queue275.811708ms였다. 원본센서는계속발행했으므로callback부재로해석하지않는다. G1기존동기frame write최대272.51345ms/callback285.500692ms,CPU최대13.172ms였다. G2에만I/O격리를적용하고G1을동기경로로남긴범위제한이실제인수관측을다시막을수있음을확인했다.

최소변경은실제acceptance runner에서G1/G2모두같은bounded_history=True를선택하는것이다. 이미검증한두serialNode/단일Clock/좁은잠금/불변유계writer/양쪽join뒤전량원본복원을공통적용한다. 기본NavigationProbe의legacy API는유지하되실제인수runner는사용하지않는다. G1의물리·10초·정적10초·촬영/수신기준·전체필수검사·G2입장결합은그대로다. 실패프레임삭제/300ms완화/scan재태깅/지난PASS선별은없다. 관련회귀/감사뒤새소스로G1부터검증한다.

## d3e89913: 공통 관측 신선도 통과 후 실제 교정 착지 실패

현재119/03794a3e 공통관측G1은sensor_freshness PASS였지만carry:measured carry posture lost로전체FAIL했다. 최초실패38944ROS/선택joint38938ROS(age6ms),gripper좌−0.0062795536/우0.006279668m/s로기존0.005m/s초과였다. 팔최대관측속도0.01325rad/s/오차0.01902rad는각기준이내. 실제owner의first_fault와모든원본을보존했다. terminal결과는확정됐고runtime stop/deactivate/소비자종료·입력/기록양쪽join·writer28225=28225/jointrue였지만,roslaunch부모가최종SIGTERM으로정리되어launch_returncode−15/forced_cleanup=true/normal_engine_exit=false다. native엔진과TF관측프로세스는각exit0이었으나이를정상엔진전체종료로대체하지않는다. 잔여[]/부모회수확인. ZIP10648998SHA7e8abc209f5e40708c3528dcf32738682cd71ccbd31f5bc974f5e04c30ac8e53.

해당G1하강중원래preload(.017607732m)복귀참조는peak.02m/s/quintic velocity/return start.034089932m였고,선택접촉은baseline.018714378m부근에서실제하중을받기시작했다. 새fixture native_d3e_calibration_impact.json에는정확한request/10wall deadline/return brake·plan/selectedjoint와두원본보고서SHA를저장했다. 이는물리재실행/완전원인증명이아니다.

가설: preload보다앞선실제접촉시점에도20mm/s를유지하는교정하강이연성그리퍼를흔들수있다. 후보는G1하강만nominalpeak10mm/s·acceleration0.1m/s²로줄인다. 기존상한20mm/s/.2m/s²,상향brake·일반CRAWL·형상/질량/마찰/게인/30Nm/2ms/10wall초/실제lift·4N3촬영·full1wallsettle·그리퍼0.005기준은유지한다. 속도절반이실제그리퍼속도절반을보장한다고주장하지않는다. 기록된return초기조건에서원래deadline안에복귀와1wall초정착예산을남기는실패회귀→관련G1궤적·소유권회귀→새설치→실제G1으로판별한다. 원래개별unit의짧은반복횟수는새참조소요시간에맞추되원래10초/동일endpoint·속도상한/세고유측정요건은변경하지않는다. 강제정리원인과물리실패는서로대체하지않으며후속종료회귀도필요하다.

G1soft-return 관련24PASS28.54초(-W error): 기록된실패초기조건·원래deadline/1wall초예산·C3연속성·원래endpoint·하중/고유촬영·소유권·일반보행분리·실제ROS교정서비스. 이는실제그리퍼/정상종료통과증거가아니다. 두기존unit의짧은시간예상FAIL은보존하고원래10초안에서필요반복횟수만수정했다. N재설치/8감사뒤새G1을진행한다.

### 새 고정 소스 G1 e1c71613

23/23PASS. G1교정하강nominal10mm/s/.1m/s²와공통dual serial관측·유계기록원본을실제검증했다. arm속도최대0.004913338rad/s,gripper0.0018066675m/s;원래기준유지. runtime/engineexit0/강제없음/회수/잔여[]/입력·기록receiver각closed·errornull,writer25485제출=25485쓰기/jointrue. 한실행PASS이며간헐성3연속이나G2성공을뜻하지않는다. ZIP10070966SHA89f0fd9b09c5e14389df4b9eebc654579bb810bf64191f8008edc1c12a04c52c,119source manifest311fbc4f8c3d3d6d3847c42e3b99103e8f1a8e6aa66437995e489e1fc43110ef. 같은소스·준비장면G2 a82b70d1-c5b6-4737-817a-db0f1319e11f 진행중.

고정119/source311fbc4f 후보의MuJoCo G2연속성시리즈는현재a82b70d1을1회차로사전지정한다(아직실행중/결과미확정). 0.4m/±.3/정지/전체필수검사와정상정리까지ALL PASS일때만같은G1 e1c71613장면/설치/소스의2·3회차로진행한다. 어느FAIL도제외하지않고첫FAIL에서중단한다. 첫회부분이동이나G1PASS를G2완주로계산하지않는다. 후진별도·Gazebo3회·G1반복·최종13.3/13.4matrix는여전히별도필수다.
사전 지정한 a82b70d1 1회차가 native movement body:ros_age로 실패했다. 후속 2·3회차를 시작하지 않고, 원본 전체 평가와 회수가 끝난 뒤 보존한다.

## a82b70d1: 사전 지정한 연속 검증 1회차 FAIL · 후속 중단

644923999998ROS 시점선택body644717999998은age206ms/receiptwall48.831705ms였다. 같은원본nativepub→adapter4.622614ms/DDS0.136995ms/RMW→callback154.445676ms. 다음644815999998도원본nativepub→adapter8.739338ms/DDS.169639ms/queue130.659368ms로판정28.246528ms후callback이실행됐다. 헤더를now로바꾸지않았고새목표를못받은것으로명확히FAIL했다. 접촉age166ms는동시관측이었으며callback부재/순수생산부재로단정하지않는다.

writer560205제출=560205쓰기/peak71레코드/jointrue,입력·기록receiver각closed/errornull. native engineexit0/부모회수/강제없음/잔여[]였지만measuredSTOP기한과deactivate가실패해runtime정상종료는FAIL. 삼연속시리즈는현재1회차FAIL에서중단했고2·3회차를시작하지않았다. 원본318여MB ZIP317798016/SHAf3e8b95fc657e9690dd0cabdda4410dc09386051cb1b017ddf2c3cf5d31f300a와72MB분할5개를재독·연결SHA검증해보존했다. 원본native와repository복사도유지한다. 소스119/311fbc4f와설치본을고정했으며결과를성공으로바꾸지않는다.

실패주변CPU계측: observer.9307/엔진1.8804/pose adapter.5413/camera-info adapter.4274/crawl.8832/guard.7408논리코어등. 4물리·8논리환경에서단일프로세스가가볍다는것과전체스택의여유는별개다. 정확한OS스케줄링원인을이값만으로확정하지않는다.

다음최소구조판별: native_pose.py와camera_info_adapter.py를읽으니둘다get_clock/timer없이원본header를그대로전달한다. navigation_enabled에한해서이둘의use_sim_time=False로불필요한500Hz TimeSource구독만제거한다. 원본엔진/5개제어노드clock·모든촬영header/TF·카메라320×240/15Hz·유효시간/물리·명령소유권은그대로다. 100Hz relay를MuJoCo로확장하는것이아니며해당G2실행프로필금지는유지한다. navigationfalse인기존13.4launch의simclock설정은유지한다. adapter진단로그가SYSTEM시각일수있어물리촬영은항상원본header로대조한다. 실제launch평가RED12.06초뒤시계유무각각실제DDS헤더/좌표/TF단일발행보존을먼저검증한다. CPU전체개선과G2완주는새실측이필요하며아직해결됐다고주장하지않는다.

navigation 헤더전달 노드의 불필요한 시계 구독 제거 관련25PASS51.76초(-W error). 실제launch/원본헤더wire/기존13.4 Gazebo경로/단일소유권/G2프로필경계 포함. 기존5개nav노드와원본clock/원본촬영/물리/필수인수기준은동일하다. D+N새설치감사후새G1/G2에서CPU와연속갱신효과를실측한다. a82b의사전지정series1FAIL및후속중단은유지한다.

## 58dcbf31: Windows 공유 경로 쓰기와 종료 RPC의 수명 결합

119/47bd402c G1은저장장치기록실패로전체FAIL했다. writer제출1209=실제쓰기1209였으나in-flight포함레코드256/8MiB중256레코드한도를찍고overflow가고착됐다. peak277149bytes/한write최대272.128719ms. 빠진레코드가없었다는뜻은아니며거부된새레코드가있어인수는무조건FAIL이다. 원래큐한도를늘리거나오버플로를성공으로취급하지않았다. ZIP708651SHA d199579ead048949dfa0462e3a859accb12d87a2a1890d94b2cc030ad30b5637 보존. 엔진0/회수/강제없음/잔여[]/양수신·writerjoin은확인했지만진단·STOP·carryterminal·native-stop응답수신이끊겨runtime정상종료는FAIL이다.

추가결함: journal예외가ROS callback실행기까지죽여종료서비스future를받지못했다. 최소실제DDS회귀RED14.14초에서기록오버플로뒤RPC수신기가종료됨을확인했다. 새JournalFailure는운전fault()와전량복원/전체result실패에는고착시키되ROS수신기는유지해명시적STOP·deactivate·terminal·native-stop응답을받도록한다. 종료중ignore_faults는기존실패를지우거나동작재개를허용하지않는다. 보통callback예외의기존고착중단정책은유지하고기록실패만구분한다. 최초실패callback/ROS/wall을별도진단에남긴다.

기록위치판별: G1은지금까지/mnt/c에live journal을썼고G2는이미네이티브EXT4에기록했다. native-output-g1-mujoco.py로G1준비장면과live원본도기존소유native workspace/evidence에만만든다. 모델/물리/시계/큐한도/유효시간/인수조건은그대로다. 실제부모회수·잔여없음확인뒤Windows작업저장소에원본과준비장면을복사하고모든파일SHA를재독검증한다. 같은원본preparedscene을후속G2에넘기며native원본은삭제하지않는다. 이는실행위치라는통제변수를바꾼비교이며실패를제외한맹목재시도가아니다. 기존58dcbf31실패도원본/보고서/해시에계속포함한다. 저장위치변경만으로지연이모두해결된다고주장하지않으며새실측을요구한다.

기록 실패와 종료 통신 수명 분리 관련24PASS44.54초(-W error). 오버플로 뒤에도명시적cleanup RPC 응답은실제DDS로수신되지만fault()/journal오류/전량복원실패는고착돼인수가성공으로바뀌지않음을확인했다. 일반callback예외중단·유계메모리·원본복원·양쪽join은유지했다. 새G1은기존G2와같은native EXT4 live기록+회수뒤Windows복사/전파일SHA조건으로판별한다. 저장위치변경은통제변수이며실제효과는아직미검증이다.

새119/674ab243 G1 250b1a4a는native준비·live원본·회수뒤Windows복사SHA대조로23/23PASS. runtime/engine0·강제없음·잔여[]·양receiver/writerjoin,24709제출=쓰기·peak42/256. 실제gripper최대.002894823m/s/arm.006663775rad/s. ZIP9532457SHAc91e1386ac50768f6d09deaba0f87aea2b46e7ffd05b096c10c9392dd9e2f215. 전체G1평균CPU pose.15776/cameraInfo.06061코어;이전장기G2와동일부하비교는아님. 같은nativeG1원본result/장면으로G2 ef6a9b3d-f193-43b9-a155-98a5cb6ed0a6 실행중. 이번새고정소스연속성시리즈도첫회FAIL에서중단하고성공부분을골라세지않는다. 아직G2완주성공없음.

### 재개 후 확정 — ef6a9b3d G2 실패와 정상 정리

고정 소스119개(manifest `674ab243460d2ea9d637350b9508784be443233dd6a3474526e83af89a67594d`)의 MuJoCo G2 `ef6a9b3d-f193-43b9-a155-98a5cb6ed0a6`은 전체 FAIL이다. 최초 거부는 body 촬영 ROS age242ms/최초 수신 후 wall age162.000459ms이며 contacts도234ms/161.393128ms였다. 다음 회차를 실행하지 않았다. 실제 정지·deactivate·carry terminal·native worker·runtime·엔진 exit0·부모 회수·잔여[]·양 수신 작업자와 기록 작업자 종료는 모두 확인했다. 이 정상 정리를 이동 성공으로 대체하지 않는다.

기록은92,346개 제출=저장, peak85/256, 오류 없음, 최대 실제 write88.761179ms다. GC는 실패 시간 창에 없고 최대24.351581ms는 다른 시각이었다. 따라서 GC·디스크 하나를 최초 원인으로 확정하지 않는다. body DDS→callback90.462804ms; 다음 body/source 수신까지 약221/207ms 공백이 있지만 reliable native_controls에는 그 사이 촬영109208/109262/109312ms가 존재한다. 엔진 전체 정지나 입력 callback 전체 부재로 단정할 수 없다.

공식 rclpy `bd637294dd02b1c128422395c059fa06df8387a3`의 events_executor.cpp/events_queue.cpp/rcl_support.cpp를 읽었다. 알림은 C++ FIFO에 들어가고 메시지는 실행 시 take한다. DDS 알림 경로 자체가 GIL을 획득한다는 가설은 소스와 맞지 않는다. 공개 API의 호출 비용을 엔진 없는 별도 domain219에서 먼저 비교한다. 아직 QoS·기준·시계·런타임을 추가 변경하지 않았다.

원본 보존 ZIP48,922,296bytes SHA256 `2450415be0341f4420204a7965e835c37c1651ae78d0fdf19106cf6a9d429358`. 파일 `task8-g2-clockless-forwarders-mujoco-ef6a9b3d.zip`; 본 절과 Task8 G2는 미완료다.

### 승인된 MuJoCo relay100 비교: 소스 회귀

실행 프로필의 `relay100/native/native` MuJoCo 조합만 추가했다. 기존 다른 물리·기본 승격 거부를 유지한다. RED1/13.63초→관련51PASS/41.72초, 실제 ROS 중계 wire5PASS/2.60초, 최신 전체 navigation624PASS/460.54초(-W error). 실제 guard 서비스의 명시적 MuJoCo G2 admission fixture도 전체에 포함된다. 이 schema/센서 fixture는 물리 엔진 성공 증거가 아니다. 새 빌드·8패키지 감사→native 저장소 새 G1→같은 고정 소스/설치/장면·프로필 G2로 이어간다. 첫 실패를 제외하거나 기준을 변경하지 않는다.

## 첫 실제 비교 — f99a643c, 전체FAIL

MuJoCo G1 `f99a643c-cad9-4c5f-9a0d-33ef9778211d`는 measured_startup에서 `crawl:guard:ros_age`로 실패했다. 첫 stop의 ROS16.288s, 선택한 guard header16.062s(226ms 전), 최초 receipt부터31.131560ms였다. guard 자체의 state는STAND/fault빈값이었다. 시계중계 원본 부분집합/최초 receipt 계약은1556개 발행/최대26.556743ms로 통과했고, source/relay소유자 및 정확히5개 구독도 확인했다. 이를 이동 성공으로 대체하지 않는다. G2를 시작하지 않았다.

정리의 measuredSTOP/deactivate/carryterminal/nativeworker/consumers/relayexit0/runtime/engine0/reaped/noForce/residual[]/양receiver+writerjoin은 정상이다. 기록9,676개 전량 저장, peak96/256, 오류없음. 보존 ZIP2,905,291bytes SHA256 `bab716b98c6eccf945b3180fd759f8f54c0f560483d18c9593bfc3a5ee0c1d53`; source119 manifest `01242d0077a523a329ce32599b418a831a9e876ff8877cb8d8cfcd47bd673fe0`.

실패 시점±1초 프로세스 CPU는 engine2.274/관측기0.969/crawl0.905/guard0.400 core였다. engine66threads는 스레드 용도·함수 스택의 증거가 아니다. [Mesa 공식 환경변수 문서](https://docs.mesa3d.org/envvars.html#lp-num-threads)는 LP_NUM_THREADS가 렌더링 작업자 수이며 기본값이 CPU코어 수임을 설명한다. 그러나 이번 실패를 llvmpipe 하나로 확정하거나 현재 엔진 설정을 추가 변경하지 않는다.

현재 guard_state의 RELIABLE KEEP_LAST10은 최신 상태보다 오래된 상태를 먼저 전달할 수 있다. 먼저 별도 실제DDS의 유계 수신 정지/상태 버스트 최소 재현으로 이 의미를 판별한다. 관절·접촉 원본 QoS나 전체 물리 기록을 줄이는 방식은 채택하지 않는다. 최신 guard 상태 자체가 고착 FAULT/새generation을 보존하는지 확인하고, 원래 촬영·최초 receipt와200ms 판정을 유지한다. 실제 f99의 guard 발행 지연과 Crawl 큐 지연은 현재 metadata만으로 분리 확정할 수 없으므로 다음 guard 수신의 원본DDS source/received 시각도 함께 기록한다.

### 최신 guard 수정본의 실제 G1 — 61422188, FAIL 보존

MuJoCo G1 61422188-2d9d-4915-bdaf-eb06a8b1e4e0는 교정 하중 이동에서 arm_joint_2 속도0.0210090315rad/s>0.02로 실패했다. 선택 joints ROS32.021999999s/receipt 후1.314989ms로 신선한 물리 관측이다. guard 상태는ROS32.033999999s/receipt 후4.89ms이며 정상 최신 수신이었다. 정확한 source/RMW/callbackSYSTEM metadata가 저장됐다. 따라서 guard 캐시 회귀 통과와 물리 실패를 구분한다.

최초 소스119 manifest4a6731f9618581b88c4ca1011ae7cf851ce6c5b7ec1c1128186e6d0918baaadb; 보존 ZIP7,843,159bytes SHA42d461db29e4b87af0b99ccbfb090bdd74f1c6c1d3a3a034243dd2017065b21e. 실제 measuredSTOP/deactivate/terminal/native/consumers/relay0/runtime/engine0/reaped/noForce/residual[]/수신·기록작업자join을 확인했다. 기록22,841개 전량 저장/peak57/오류없음. G2를 열거나 동일 소스를 재시도하지 않았다.

원생 FR thigh ctrl은31.996→32.018s 표본 사이0.0050445065rad 변했다. 이 관측만으로 중간 callback/물리 인과를 확정하지 않는다. 기본 Controller Manager100Hz와 MuJoCo 물리2ms를 구분했다. 과거 효과 없던 SHIFT 가속도 절반 실험을 반복하지 않는다. 기존 Gazebo20ms 적용 성공과 공식 ROS2 controller 사례를 검토해, 별도 Ch13 MuJoCo 모터 참조 적용 비교안을 SECTION_13_5_MUJOCO_REFERENCE_PROPOSAL_KO.md에 작성했다. 이는 앞선MuJoCo native 참조 승인 범위를 넓히므로 승인 전 구현하지 않는다.

### 2026-10-26 native 유지·원인 분석만 — a1ee6678

사용자는 새 MuJoCo20ms 보간 controller 확대를 채택하지 않고 ‘현재 native 참조 유지·원인 분석만’을
선택했다. 새 controller/mode/게인/런타임/엔진 시행은 없다. HEAD4e87f6f/13-5브랜치 유지, no commit/push.

61422188 원본 ZIP SHA42d461db29e4b87af0b99ccbfb090bdd74f1c6c1d3a3a034243dd2017065b21e 재확인.
당시 manifest 런타임119파일 모두 현재와 일치했다. 분석 코드의 수치 self-check와 일반 URDF FK
대조 후36표본 FR/RR/RL implied command translation 최대편차1.5700924586837752e-16m,
FK대조1.1443916996305594e-16m, thigh .001rad 합성 교란 감도.441573mm. 합성은 실제기록과 분리.
동일36표본 팔6+gripper2 staged 목표는 모두 일정(arm2=1.2rad). 실제 carry peak.021009>기준.02는 유지.

외부 ros-controls/mujoco_ros2_control clean c261f5552edf124d1000a23fb25b6c07cadeb807:
write가 snapshot ctrl을 새 요청으로 갱신→plugin.update→전체배열 staging 잠금→물리적용/step 순서.
따라서 native_controls snapshot header와 staged ctrl은 새 명령의 물리적용 시각 trace가 아니다.
기존22ms 표본차를 정확한 입력간격/원인으로 해석하지 않는다. 역산곡선은 hold뒤50ms 진행을
시사하지만 발행/DDS/CM/apply 경계별 인과는 미확정. tick_spans ROS는 END시각, decision시각 아님.
원본 결과의 false4개+누락native_library_loaded1개도 보존했다(교정 뒤 확인 경계 미도달).

재현 코드·결과·외부 구간/파일SHA: analysis-a1ee6678-35ab-484c-9fba-aa861f1af230/.
result SHAaebcd0ea1188d6a0184427b824529f2820756552b39b445713828b735f61af9b.
한국어 설명/핵심Mermaid/보류가설/다음측정요건: docs/SECTION_13_5_MUJOCO_NATIVE_CAUSE_ANALYSIS_KO.md.
G1/G2·Nav2·절완료로 세지 않으며 새엔진은 실행하지 않았다. 원본614 정상종료/잔여없음은 그대로 보존.

### 2026-10-26 native 명령 적용 경계 — 실제 실행 전 검증

사용자 지시로 분석만 제한이 종료되고 Task8→Nav2→최종회귀/commit/push를 재개한다.
MuJoCo native 참조는 유지한다. 실제pluginlib+ROS에서 trace서비스 부재RED1/641ms,
Crawl 실제발행 기록 부재RED1/13.33초를 확인했다. 발행/기존안전 회귀6PASS/19.48초,
실행기/관측기/기존인수 관련29PASS/13.81초. 새S/N 빌드1분41초·8패키지 감사통과.
외부 tl_expected CMake deprecation 알림만 있고 컴파일 오류/새소스 경고는 없다.
설치된 실제plugin ROS1PASS/111ms, 전체S CTest10target PASS/4.68초(유계trace2case 포함).
이 결과는 실제 보행 성공이 아니다. 모든 런타임/시험/REUSE를 동결하고 새UUID G1에서
CM write의 staged ctrl/과거snapshot과 실제pre_step의 적용ctrl/이전stepvelocity를 비교한다.
수치record만hot path, JSON/내보내기는 측정STOP/deactivate/팔terminal 뒤 수행한다.
기록 실패는 FAIL로 남기되 원래 native worker stop을 건너뛰지 않는다.

### 새 고정본 G1 13728e5d — MuJoCo24/24PASS

실제 MuJoCo13728e5d-675e-4670-8342-f044774dca27는 기존24필수검사 PASS/오류없음.
STOP/deactivate/팔terminal/nativeworker/runtime/engine/부모회수 정상, force없음/잔여[].
source121 manifest e733c072746c7a61819c3f91ad65050bcba6a41c5b0cdca96ea7482dcfe5159c,
ZIP12,868,393bytes SHAba4a485738a279a188802d26f6e3eafb05df64d3d5145e9b9424c15163472f1b.
계측 수정 뒤의 단일성공이므로 이전 물리 실패 해결/연속성공으로 확정하지 않는다.
실제pre_step원본2ms 간격/기록drop0, CM/postwrite와pre_step구분 확인.
최근기록의 발행wall최대33.03ms/decisionROS38ms, CMwall22.96ms, pre_stepwall13.51ms,
호환발행→CM최대44.28ms/CM→적용10.50ms; 같은값 반복의 ID모호성은 결과에명시.
pre_step꼬리12초의 arm2최대.0101507rad/s는전체수신관절인수대체아님.
같은소스·설치·원본장면/프로필G1proof로G2새UUID를 시작한다. 첫FAIL에서보존/근인분석.

### G2 e75b4e86 — FAIL 원본과 root 판별

같은source121 e733c072.../같은G1scene·profile의 실제 G2 e75b4e86은 forward 중
final_command:ros_age로FAIL했다. decisionROS60.260s/selectedcommand60.020s=240ms,
최초receipt2145717317202→decision2145899899436=182.582234ms. guard는60.212s/CRAWL/ready로신선했다.
팔실측peak가원인이아니며carry는뒤에crawl:model/fault를고착했다. STOP요청이carry고착fault로거부되고
곧바로deactivate도미확정이었다. 부모회수/force없음/잔여[]는확인했지만runtime/engine정상종료검사는
FALSE다. 초기commentary의정상종료표현을확인직후정정했다. 이를종료성공으로쓰지않는다.
ZIP24,159,570bytes SHA5103f643967497a091adc5c54e0a96b08216424b50d3bb21a9e13aa4891ce963.

최종Twist수신은control기본callbackgroup+model lock에남아있고, 이전수정은센서/clock/guard만분리했다.
실제ROS에서긴model owner작업동안최종command가수신되지않는RED1/14.24초를재현했다.
수신을기존sensor group+짧은inbox lock으로옮기고원본callback-entry ROS/monotonic과DDS순서를보존한다.
결정cutoff에적합한원본sample만유계10개중선택하며200ms를완화하거나다시찍지않는다.
오류는ingressfault로고착하고model변경/최종발행판정은원래단일owner만한다.

STOP고착거절별도RED1/14.37초→fault/generation/0출력/재활성화거절을유지한STOP ACK수정,
순수+실제ROS관련21PASS/37.01초. ACK는실제STOPPED·deactivate를대체하지않는다.
초기command관련회귀는22PASS뒤activation실패(systembackstep)였다. 서로다른두ROS시험을
같은domain159에서겹쳐실행한것을발견했다. 실패로그는보존하고성공으로제외하지않는다.
전용domain224/순차실행으로같은조건을재검증한다. 실제엔진실행은계속없다.

### 명령 수신·STOP 수정본 실제 재검증 시작

전용domain224 command/time/안전/최초fault25PASS53.25초, 추가parallel-invalid명령/lifecycle/
publication/systemclock23PASS56.96초. 별도fault-held STOP21PASS37.01초.
한 중간명령은존재하지않는test경로로no-tests였으며원본로그를보존했고수정경로시험과구분했다.
N빌드19.5초(total21.4)/8패키지설치감사통과(task8-final-command-native).
런타임/시험/REUSE동결뒤새UUID MuJoCo G1시작. 단일성공을간헐실패해결로취급하지않는다.

### 49324eec 실패 원본과 접촉 후 계획 복귀 수정

현재121 manifest0ffe7b0ee7a72a9ed1705483629b2f957e119b582a6693da8bebe73c5a6e72fc의
G149324eec는lift는통과했으나TOUCHDOWN에서gripper.0085978>.005로FAIL.
실제pre_step은32.718s에arm2 .03219rad/s peak도보였다. 원본선택관절은arm2 .01296여서
낮은샘플빈도에서peak를놓친것이며,원래carry실패를소거하지않는다. 실제STOP/deactivate/
terminal/native/runtime/engine모두정상·회수/noForce/잔여[]라STOP ACK수정의엔진동작을구분확인했다.
ZIP13,380,188bytes SHAb20043a8c51fdffe4b53ffa7dd0052ecbfc0cf027de32c6ce36cc3b7095372cf.

분석상접촉32.478s FL10.49N,32.532s19.88N뒤에도.01m/s계획복귀가이어졌다.
32.636→32.714s 실제적용발기준이0.86mm변했고직후몸체/팔/그리퍼과도응답이있다.
Ch13 G1 planned return에만원래native참조로접촉확인뒤한번의quintic제동→느린원래preload복귀를추가한다.
loaded상한min(기존.01,2*기존seek)=.004m/s,가속도와기존jerk envelope도유지한다.
별도seek .002/일반CRAWL/게인/물리/10초/실제lift와3고유관측/1wallsettle은그대로다.
첫회귀RED1/11.06초(loaded뒤.00979m/s). GREEN초기2PASS뒤기존2.4초illustration loop에서미완료였다.
반복구간만원래10초와1초settle여유안에서확장하고모든기존물리/jerk/관측assert유지→20PASS21.57초.
원래settle예산을침범하는새계획거부도RED1/11.82초→명시적sticky실패를추가했다.
현재모든calibration/실제ROS관련시험session93922. 아직설치/새엔진미실행,전체13.5성공아님.

### 접촉 후 재시간화 실제 재검증 준비

추가budget RED11.82초를확인하고최초loaded계획에도원래1초settle예산침범을sticky거절하도록했다.
모든calibration/기존deadline/unique관측/계획/실제ROS 허용 관련40PASS53.82초.
N빌드12.8초(total14.3)/8패키지감사통과(task8-loaded-return-native).
이시점부터런타임/시험/REUSE동결,새native/relay100 G1한번으로물리결과를확인한다.

### loaded 복귀 수정본 G1 a35c40ac —24/24PASS

새source121 manifest8be8776fac2692be5882d696f3f7a9ce475f43dc55dce33f831b8c0460380b61의
G1a35c40ac-8c1f-4ca8-8d45-8fae6d955ce5는기존24필수검사PASS/오류없음.
원본접촉36.636s/처리36.664s 3.212N에서.01m/s를제동했고.004m/s계획으로원래preload에복귀했다.
수직candidate완료시원래deadline여유2.73679초,이후실제owner1wallsettle도통과했다.
STOP/deactivate/terminal/native/runtime/engine정상·부모회수/noForce/잔여[]확인.
ZIP13,997,456bytes SHA51e1cba40d8b820ade34769316cf1514aa34a0d5fb553dd94684c90bd394d854.
최근pre_step6000개/12초에서도팔6+gripper2기준초과없음(arm2최대.0164738rad/s,
gripper최대.00450328m/s). 이꼬리관측대조는전체이동/연속성공의대체물이아니다.
같은source/install/원본scene/profile/G1proof로새G2 d32fdf04-0417-4a7f-b9c3-b8a7b31712be 시작.
첫FAIL을제외하지않고종료/잔여확인/원본보존까지다음엔진을시작하지않는다.

### 재개·G2 d32fdf04 관측 경계 (2026-10-26)
- G1 a35c40ac 24/24 PASS와 동일한 121파일/8be8776f 고정본에서 G2는 contacts:ros_age(214ms) FAIL. 수신 후 49.679ms, DDS→콜백 171.632ms, source→DDS 5.180ms. 정상 STOP/비활성화/terminal/엔진·런타임 종료/reap/residual[] 확인. G2 성공으로 세지 않는다.
- frame 타이머는 이미 기록 전용 executor이며 JSON 변환도 기록 잠금 밖임을 재확인했다. 두 이동 가설을 폐기했으며 제품 코드를 변경하지 않았다.
- 합성 DDS 비용 측정의 병렬 cProfile은 Python3.12에서 충돌해 실패했다. probe-cost-22836da0…/FAILED_RUN.json에 원본·해시·실패를 보존했다. 실제 엔진이나 물리·안전 인수 증거가 아니다.
- 단일 대상 순차 프로파일도 서로 다른 스레드의 thread_time으로 비정상 통계(자체 CPU가 전체 벽시각보다 큼)를 생성했다. probe-cost-37fcc42c 원본을 보존하고 CPU 순위는 채택하지 않는다. 비계측 기준 프로세스 CPU 26.32%/4초만 진단 참고로 사용한다. 모든 소유 진단 프로세스·수신기는 종료했다.

### TF 변환의 최소 수정 및 판별
- 실제DDS RED14.01초에서 TF가콜백전에객체화됨을확인했다. raw=True후첫회귀는독립CDR패딩을바이트비교한시험결함으로FAIL29.12초. 원본촬영/링크/변환값비교로교정했으며 실패로그보존. 관련36PASS58.56초.
- 합성A/B probe-tf-cost-2c99dda6: 동일500Hz clock/센서/TF부하, 프로세스CPU38.16→30.32%, 기록receiver CPU0.767→0.379초/6초. 실제엔진·인수증거아님. 앞선비교helper는노드destroy뒤report조회로실패했고원본을남긴뒤수정했다.
- 다음은N설치감사후동일a35c40ac scene/profile의새G1이다. 엔진실행중소스·테스트·REUSE를동결한다. 첫FAIL은보존하며자동재시도하지않는다.

### MuJoCo G1 cb66d879 / LP2 eb4e15f3
- cb66d879: 같은 a35 원본 scene에서 FAIL. SHIFT의 arm2 측정 -.0221349, 실제 pre_step peak -.0238657rad/s >.02. lift에 도달하지 못했다. freshness/정상 STOP/deactivate/terminal/runtime/engine/reap/residual[]는 통과했다. ZIP11518119 SHA2b207f348147d55f4a820fede9b5e29a4ee896ec6dd9b98758d18b1387865055. 원래 실패 판정을 바꾸지 않는다.
- 원본 ROS34.706s의 중복 결정 뒤34.762s로 진행했다. 발행 최대49.23ms/결정 ROS 간격68ms. 원생 PID65스레드와 EGLllvmpipe를 확인했으나, 하나만 원인으로 단정하지 않는다. 고정 입력 수학 연산은 이미 단일 스레드/중앙값.827ms, 환경1 설정.833ms여서 BLAS 가설을 폐기했다.
- eb4e15f3: 제품 소스121파일 manifestfd861fe4, 같은 scene/profile에서 LP_NUM_THREADS=2만 명시했다. 24/24PASS, 모든 정상 종료/소유 회수/강제 없음/잔여[]. 원생 PID1149/start732880의 실제 mapping·환경과41개 스레드 CPU 표본을 기록했고 정상 종료로 닫았다. 아직 연속 G1/G2 성공이 아니다.
- eb4e ZIP13418664 SHAed798a0b9bbc3a153f051f2a267e76d12b9c0292f680e62a50f66e94f692c996. 다음은 같은 고정본/원본 scene/환경의 G2다. native 보간 controller는 채택하지 않았고 게인/물리/모든 기준은 같다.

### G2 e21398d8 및 센서 큐 분리
- G2는body:ros_age206ms로FAIL. 최초선택body촬영70.334s/결정70.540s/수신뒤116.798ms였다. 원본source→DDS2.260ms/DDS→callback101.005ms. 접촉도99.658ms였다. 원본상관JSON은derived-probe-rejection-native-g2-mujoco-e21398d8…에보존했다.
- 모든정상STOP/deactivate/terminal/runtime/engine/reap/noForce/residual[]는확인했다. ZIP29524242 SHA3ed6a43062559d8eafc50196b33c47bc3113605f341a765111ca609571b6930c. LP2/TF최적화만으로전체성공이라고하지않는다.
- 실제DDS의main queue차단으로센서도막히는RED14.17초를재현한뒤시계없는ingress node를추가했다. 원래6센서+body_source+COM만옮기고parent만clock을구독한다. 원본capture/firstreceipt/inbox/기준/QoS와전량기록은같다. 자식수신기오류고착/미완료시자원유지/전체join을검증했다.
- 첫관련25PASS35.68초, 전체probe/기록복구/메타데이터/원본시각/종료52PASS82.92초. 직접메타데이터시험은새ingress node도시험executor가소유하도록바꿨고assert는유지했다. 실행기G1/G2는모두bounded=True임을코드로재확인했다.
- 다음은N빌드·8패키지감사뒤새G1이다. 같은원본scene/profile/LP2를쓴다. 고정본실제효과·연속성공은아직확인전이다.

### 별도 센서 수신 큐 고정본 G1 b36709af
- 설치8패키지감사와N빌드14.3초뒤같은a35원본scene/profile/LP2로G1실행. 24/24PASS,정상STOP/deactivate/terminal/runtime/engine/reap/noForce/residual[]확인.
- main/recording/ingress 세receiver 모두closed=true/thread_alive=false/error=null, 전체join=true. 원본firstreceipt/단일clock/안전기준유지.
- 다음은원본소스/증거보존완료뒤같은본G2이다. 아직연속G1/G2성공이나Nav2완료가아니다.

### e1696f98 최초 실패의 재분석·잠금 수정
- 최초body230ms/DDS→콜백132.985ms/수신뒤98.097ms FAIL이다. raw wallage·기록포화는후속오류다. ZIP8346951 SHA9a5e8e21fd863953db5f820d510af4190766f3232ab1b59c75ce38c9876e140a. 부모회수/강제없음/잔여[]/runtime_exit/engine_exit는true지만전체기록복구가실패해전체인수FAIL/누락검사를유지한다.
- 기존CPU/잠금측정재분석은bodyCPU.401ms에잠금54.998ms,frame벽91ms/CPU1.78ms,관측프로세스71~96%를보였다. 최초거부시writer오류없음/peak65이며frames37~50Hz였다. 큐용량/프레임폭주만으로설명하지않는다.
- _dispatch의잠금전수신시각누락RED12.08초. projection시험첫준비오류22.31초도보존했고Clock/Body/Contacts전용입력으로정상RED11.53초를확인했다. 포괄잠금제거·원본receipt먼저보존·짧은상태교체·불변snapshot선택뒤복사/계산/기록분리→직접22PASS18.26초.
- 첫전체회귀는기존record-lock반례의inbox동시잠금단정에서16PASS뒤FAIL64.66초. 새수명에서실제로후속수신이200ms이상멈춤을확인하는반례로교정했고전체54PASS72.17초. 기존반례/안전age검사를제거하지않았다.
- 종료중대용량추적JSON loads→indent dumps를원본문자열보존+엔진/모든수신기join뒤검증으로바꿨다. MuJoCo전용서비스는Gazebo에서요청하지않는다. schema/동결/행/관절/유한값/시각손상은FAIL. RED14.68→관련32PASS17.79초. 기록큐크기나버림은변경하지않았다.
- 다음은N빌드/8감사뒤원본a35scene/profile+LP2의새G1→같은본G2다. 아직전체G2/연속성공/Nav2/최종commitpush미완료다.

## 재개: 699d/95df 결과 및 불변 기록 후보

고정121/5b84edb702f594936c6d74eca220c8cf4b26f16db167ee50c0e349da95295296:
- G1 699d6d73-7052-48fb-9b4e-a2dbac3975fe 24/24PASS. 저널25409 전량/오류없음/정상종료.
  ZIP12408632 bytes SHA d289986ddb77c7d6c4c29d38369771e26af5248809f05f543d318aedc5a8163e.
- G2 95dfb687-c4f6-4507-be31-42a209a63288 FAIL. 최초body ROS248ms,
  source→DDS7.578171ms/DDS→callback121.958518ms/receipt→판정116.022568ms.
  뒤의raw ROSage는이차오류. 저널94757 전량/오류없음/peak89/최대write107.399ms.
  STOP·terminal·runtime/engine종료·회수·강제없음·잔여[]는별도확인했다.
  ZIP51915944 bytes SHA8a84df0e3f38fbe36a6a89e51f02704632d5e10cf43bacbc8e95b52117713cb0.

cProfile 진단의 비정상 누적통계는 원인 근거로 쓰지 않고 원본을 보존했다.
probe-monitoring-fb76d68d의 sys.monitoring은 journal worker가 계측전 시작한 경계 mismatch1개,
다른 열린frame0이다. 반복asdict호출은 확인되지만 계측부하가 커 절대CPU점유율로 인용하지 않는다.
최신 실제GC15.4ms는 최초실패 뒤이며 그 실패의 직접원인으로 단정하지 않는다.

재개시 실제engine/pytest/profile프로세스 없음을 확인했다. RED 세션5912는 소멸했으나
원본task8-immutable-record-red.log는 보존됐다. 별도red-resume도 동일한 기능부재로1FAIL13.52초.
새 후보4시험PASS8.79초. 전체 관련회귀는7PASS 후 native ingress 실패45.52초, 단독도13.96초 실패했다.
실제FootContacts 숫자가numpy.float64여서새고정처리가거부함을직접확인했다.
실제생성메시지회귀를추가해4PASS/1FAIL12.28초 RED를확인한뒤숫자scalar호환만수정했다.
새전체관련회귀진행중. 아직실제G1/G2후보효과·연속성공·Nav2·최종commit/push는미완료다.

불변 기록 후보의 비계측 A/B(66215a66)는 baseline28.273/27.483%, 후보27.813/28.134%로 전체 비용 개선을 확인하지 못했다. 개별frame 비용은 줄었지만 실제G2 재시험의 근거로 채택하지 않는다. 후보 구현/시험/모든 실패와 SHA는 같은 evidence에 보존하고 runtime probe를 변경 전70987f... 바이트로 되돌렸다. 따라서 현재 runtime은 다시121/5b84 원본이다. 새로운 구조 판별은 G2 명령·고유촬영 판단 반복의 CPU를 엔진 없는 동일 입력에서 분리 측정한다. 최초runner-cost53b2의 매poll YAML읽기는 실제와 달라 그69% 수치를 근인으로 사용하지 않는다. 일회 설정 읽기로 교정한43343331도 source만35.32% 대 판단반복68.16%로 차이가 남았다. 이것은 합성 비용이며 실제엔진 근인 확정이 아니다.

## 실제 G2 d1434a6a: 최초 촬영과 OS 스레드 비용

현재121파일/5b84 고정본, G1 699d의 원본 scene/profile/LP2를 재사용했다.
G2 d1434a6a-8614-4a89-8ed5-b703ecee3a4f는 전진 약0.116m 후 최초 body:ros_age204ms로 FAIL했다.
결정ROS225.926s, 선택body225.722s. body source→RMW0.161949ms,
RMW→callback140.970819ms, 원본receipt→판정60.106049ms였다.
contacts는178ms이며 RMW→callback141.884327ms/source→RMW0.165867ms였다.
뒤따른raw ROSage는 이차오류다. STOP·deactivate·carry terminal·native worker/consumer/clock stop,
runtime/engine0·부모회수·강제없음·잔여[]·전수receiver/journal join을 확인했다. 전체G2는FAIL로 보존한다.

별도 /proc 읽기전용 수집기는 같은 UID/start ticks의 runner를1226회 관찰하고 정상종료했다.
최초 실패 직전2.0333초의 CPU: main13.77%, 식별확인된 parent receiver10.33%,
그밖 Python TID1140 24.59/1138 18.69/1142 11.31/1137 7.87%, DDS shared-memory9.34%였다.
자식수신기의Python thread_ident와OS TID 대응이 저장되지 않았으므로 후자의정확한역할을단정하지않는다.
합성CPU값만으로전체실제부하를설명할수없었으며, 콜백내CPU만계측하면 실행기/변환/원생수신비용을 놓친다.

원본ZIP112369324bytes SHAfd96d1750ebc9409e0f0a062ad48476af91dc142212d9ddbe13d32d66762f1ca,
원본은로컬보존하고72MB+40369324bytes 두조각과SHA원장을생성했다. byte-copy 검증 후 추가 분석을했다.

공식 rclpy7.1.12 고정소스 bd637294dd02b1c128422395c059fa06df8387a3의
rclpy/src/rclpy/events_executor/events_executor.cpp 전체를 읽었다.
https://github.com/ros2/rclpy/blob/bd637294dd02b1c128422395c059fa06df8387a3/rclpy/src/rclpy/events_executor/events_executor.cpp
spin_once는콜백뒤queue Stop→spin잠금해제→Restart→Python context.ok로복귀한다.
현재 ProbeReceiver가이를콜백마다반복한다. public spin은같은C++ queue를연속처리하며,
shutdown(0)은queue Stop을먼저요청하고활성콜백때는false/자원유지한다. 전체종료후shutdown으로해제한다.
외부원본은읽기만했다. 이를사용하는작업 helper의ABBA비교만진행하고,
전체CPU/원본시각/실제DDS종료효과전에는runtime설계로채택하지않는다.

연속 dispatch 후보 실제DDS RED243 Python복귀/14.30초 뒤 관련57PASS80.78초.
blocked callback의미완료closed=false/ROS자원유지/오류고착/전수수신기join/원본firstreceipt/기록반례를보존했다.
패키지모듈/설치라이브러리변경없이관측script만바뀌었으므로불필요한재빌드대신8패키지byte감사를실행한다.
새같은scene/profile/LP2/native controller G1이확인된뒤만새manifest의G2를진행한다.

## 최신 두 실제 실행과 구조 후보의 실패/채택 판별

연속dispatch 고정121/72a59990fedc69d69ba9dde6744fe6ba34302f6b06282a0224a19b85452a307d:
G1ba55d70f24/24PASS/normalall/archive12368102SHA69b4f437e10c36dd0f7b8982d1b82897699e4ea92f9b4c3535993457c2130e80.
같은본G2 004cf6fa FIRSTbodyROS262ms/DDS125.09299/source1.639908/receipt129.902739ms FAIL.
STOP/terminal/runtime/engine0/reap/noForce/residual[]/전수join은확인했다.
원본ZIP72319000 SHA3c0c781fa4b346a9593555157ea643d7fbf7f4d96c7a7ff6c3d6c78b752f1b14.

JSON인코더만독립프로세스로보낸후보는모듈RED14.14→3PASS22.84,
실제ROS연결RED22.08(4PASS/1FAIL)→5PASS29.58였다. 그러나동일실제값ABBA72d2eccf에서부모CPU가
42.53/41.69→47.14/54.68%로악화돼실제엔진에적용하지않았다. snapshotwire상한계산과IPC제출의추가비용을확인했다.
API/통합probe/5시험은같은evidence에보존하고실행경로에서철회했다.

그뒤전량관측기전체를분리했다. componentRED15.67→첫GREEN실패21.54(report키중복),
연결EOF고착RED29.15(2PASS/1FAIL)→3PASS26.55.
통합시험첫실행은active입력동안준비10초실패/75.99초(3PASS/1FAIL)와시험용발행스레드누수를보존했다.
소유pytest874/UID1000/start136157에SIGINT로종료요청, threading._shutdown KeyboardInterrupt를정상종료로표시하지않았다.
잔여pytest/observer/engine없음을확인한뒤관측기준비후입력을시작하는실제순서와예외정리를적용했다.
runner연결RED38.70(4PASS/1FAIL)→관측/실행기/trace관련14PASS45.00.

새비계측ABBA714067e3: integrated부모54.967/49.074% 대split36.381/36.088%,
전량child5초2.08/2.13CPU초. full bodyP95 3.348/2.996→2.233/2.335ms,
missionP95 1.644/2.261ms. 각300고유합성body/정상발행자·관측기·자식회수/원본값SHA를보존했다.
이것은물리인수성공이아니다. 전체관련회귀진행중, 새원본source/설치감사/G1→G2검증이남았다.
전체Task8 G2/양엔진3연속/Nav2/최종회귀commitpush는미완료다.

최신분리구조 전체관련회귀62PASS135.47초. 원본시각/최초receipt/오류고착/기록반례/실제DDS분리/
실행기factory/자식정상exit/EOF재호출고착/대형trace의전체join장벽을확인했다.
이후실제실행은8설치byte감사→같은a35 scene/profile+LP2의새G1→원본보존→동일본G2순서다.
패키지의모터/물리/제어기구현을바꾸지않아불필요한재빌드는생략한다. 새script도source manifest로결합한다.

## a50d 실제 실패와 다음 최소 수정

G1a50dFAIL/122source13a9098b... 원본ZIP10450559 SHA f0665ce6be3212b80b4aeae8d7f49ffa00cc624a0420f566c8571a4e28bd6913.
최초팔2속도.0355856/실제prestep.0378499>.02, jointROSage2ms/수신7.192ms로신선했다.
교정은SHIFT단계이며수직SWING조차시작하지않았다. ROS발행gap78ms/wall31.018831ms,
실제목표31.528→31.538 10ms간격의fr_thighΔ-.008297543rad가연결됐다. 원인은후속실제로판별한다.
G1 SHIFT만참조진행최대20ms로제한하고일반CRAWL/native제어·보간·게인/기한유지.
실제시각쌍/이상적geometry RED12.33→43PASS51.91→정지재개/일반유지등44PASS59.02.

a50d전체저널23867 전량/오류없음,모든receiver닫힘/childexit0/엔진·runtime0/회수·잔여[]였다.
당시teardown의probe_receiver_joined=false는운동fault를관측기error로섞은하네스판정오류이며원본을수정하지않는다.
동일문제ROS RED23.20→runtime_fault와통신error분리/정상cleanup·history복구/6PASS49.27.
물리fault는새runner에서도항상전체FAIL이다. 정상정리와과제성공을혼동하지않는다.

입력없는준비도10초실패25.74초를재현해입력순서단독가설을정정했다. 원인미확정이며
엔진전구성요소startup계측+30초명시상한을추가했다. 원래물리10초·모든안전기준은유지한다.
다음은N만재설치/8감사→새같은sceneG1→원본보존→동일고정본G2다. 아직전체G2/양엔진3연속/Nav2/최종push미완료.

### G1 68c877cc 고정본 실제 검증 및 G2 재개
- G1 24개 필수 검사 PASS, 실제 controller terminal·엔진/runtime·분리 관측기 정상 종료, 강제 종료 없음, 잔여 없음. source122/manifest a694f432f33a4a78d64cb10db532bf8ca3e86968b63e13dc34681feee8134aec.
- 원본 보존·바이트 복사 후 ZIP 16,872,061 bytes/SHA256 466599b7c7b3bdbad3d7fb65802ca309545f6f6f3991772fc98b1647d3730cae. 이 1회 성공은 연속 성공이나 절 전체 완료가 아니다.
- 동일 G1 proof·설치·장면·LP2·relay100/native 조건의 G2 7c3373df-add2-4308-9d44-a75957b61681 시작. 실행 중 소스와 설치 동결, 첫 실패를 보존한다.

### G2 7c3373df 첫 실패 보존 및 SHIFT 지연 회귀
- 최초 carry arm2 -.02046101222155071rad/s>.02. 원본 joint ROS126949999999ns/first receipt5464795483583ns/판정5464807888024ns. 신선한 물리 실패, 후속 carry:not_ready는 이차 상태.
- 정상 STOP/비활성화/controller terminal/native workers/full observer/mission receiver/journal/runtime/engine0/parent reap, noForce/residual[]. Full journal94033=94033/errornull; worker runtime_fault는 유지, 정상 정리와 구분.
- ZIP64253014/SHA13b1b9f251327e009f9955fb59bdadae7a6a3a5762300a405df98c404c9a741e, source122/a694f432. derived-command-boundaries 파일은 원본 상태를 승격하지 않는 사후 분석.
- SHIFT pub5343→5344 ROS72ms/wall52.029145ms, rl_thigh delta.006552801855918111rad. 회귀 task8-crawl-shift-clock-red13.53초에서 목표 건너뛰기 재현. 일반SHIFT 진행만 한 명목20ms로 제한하는 최소 판별 수정; 원본 timeout·safety·native motor 그대로. 실제 개선효과는 재검증 전 미확정.

- SHIFT 지연 진행 회귀 RED13.53초 → 새/명목/G1/control-gap/가속도48PASS58.58초, ROS 안전 정지·intermittent body·실측baseline·착지·회전·발속도18PASS70.75초. 물리 인수 아님. N만 재설치 후8패키지 감사 예정. source freeze 전 REUSE·설계 업데이트 완료.

### SHIFT 진행 제한 고정본25e1ac31 검증
- Nbuild14.8초/8패키지 감사PASS. MuJoCo G1 24dfb4f3-5b24-421b-9133-172bc45c248a 24개 required_checks 모두PASS. controller terminal/센서 worker/runtime/engine/mission·전체관측기/journal/parent 정상 종료, noForce/residual[].
- source122/manifest25e1ac31c28d90713faba632af89834a90f95a77cbccbb551ed22ae555ad00bc. ZIP17119321/SHA256dbc6e214ef482c41dce0a98e0d909d69e5bc4164fffafbeea6ec9946f745b479.
- 같은 고정본·장면·설치·relay100/native/LP2의 G2 a68b9c1b-b654-4cd5-a050-7a7d0a5c40f3 실행 시작. 소스 동결, 실패를 제외해 연속 성공으로 계산하지 않는다.

- G2 a68b9c1b FAIL SWING/gripper-.0056556702>.005, 신선한 촬영261546000000ns. 정상모든정리/journal199023=199023/errornull/noForce/residual[]. 원본ZIP142489236SHA84bee431260f93308c3a24af281116d121b73a4f223551c99f22be0d6f45a123,72MB+70489236조각 각각6e6a36b89e5ede6cf9a2a3f75975f5b0f48b441ff47626d3db55863fcd712f19/6a4367d873269389787f8068f7bd550de8b66bd36732b8b4407718ed6ad0c7c4.
- 실제pre_step pub12499→12502(중간12500/12501미적용),48ms 뒤rrcalfdelta-.0053718861156604. source25e1ac31 고정본 실패 보존. 이제고수준단일outstanding목표+readonlypre_step확인 설계. native motor interpolation 없음. 모든원본시각/200ms/50Hz안전/정지/게인/물리기준유지. 설계가 실제 성공을 의미하지 않는다.

- 적용 credit 순수 계약 RED16.99초 →4PASS12.81초. 모터 보간 구현 없음. 실제 plugin의 pre_step/CM 구분 RED 빌드·시험을 시작했으며 실제 엔진 개선은 아직 미검증이다.

### 적용 관측 구조의 RED/GREEN 및 회귀
- 순수 credit RED16.99초→4PASS12.81초. 실제 plugin의 echo 부재 RED1FAIL1538ms→2PASS248ms; worker/trace4PASS26ms. S 재빌드1분44초, 기존 S CTest10대상 모두PASS4.73초. 아직 실제 엔진 성공 아님.
- 원본 시각·대기 중 안전·정지·SWING 제한 커널 RED16.08초→16PASS27.88초. 실제 owner scope/DDS/G2관련 RED16.64초→19PASS37.26초.
- 추가 관련 batch는10PASS 뒤 기본 경로 foreign_guard_generation 시험의 활성화가 command_clock_step_requires_restart로 실패(41.16초). 원본 로그 보존. 같은 시험 독립 domain229에서는1PASS9.98초이나 원인을 확정하거나 첫 실패를 지우지 않는다. 적용 credit은 해당 기본경로에서 꺼져 있다.
- 변경 사건 한 번의 관측을 손실형 센서 QoS에만 의존하는 구성은 실제 endpoint 검사를 추가해 RED14.79초로 확인했다. 새 사건 topic 양쪽을 RELIABLE KEEP_LAST1으로 명시했다. 기존 일반 센서 QoS는 바꾸지 않는다. 독립domain231에서 원래 실패를 포함한 전체 관련 회귀를 재실행 중이다.
- 신뢰성 사건 전송을 포함한 관련 batch31PASS63.39초. 이전 활성화 실패의 직접 원인은 아직 확정하지 않았고 전체 기록을 유지한다.
- 대기 분기 자체 검토에서 조기 발 재접촉 시 네 발 지지 여유는>.09m지만 세 지지 발 여유는<.01m인 경우 원래 SWING 검사 우회를 발견했다. 실제 기하학 입력 회귀 RED12.30초(CRAWL로 남음)→보행/시간/정지/G1 포함48PASS49.06초. 대기 중에도 세 발 지지·원래 unload/touchdown timeout을 검사하도록 수정했다.
- 첫 신뢰성 QoS 빌드는 시험 코드가 rclcpp::ReliabilityPolicy와 rmw enum을 비교해 컴파일 실패했다. 기능 RED나 엔진 실패와 구분한다. 설치 Jazzy qos.hpp의 실제 enum을 읽어 rclcpp::ReliabilityPolicy::Reliable로 고쳤다. 실패 빌드 로그 보존. 재빌드 S1분56초/N14.6초 진행, 최종 감사·C++ 회귀 결과를 이어 기록한다.

- 수정 후 S1분56/N14.6초 재설치·8패키지 byte감사PASS, 최종S10대상4.27초 모두PASS. actual MuJoCo G1 b9956543-c3ab-4a3e-95b4-ee62366dca1f 시작. runtime/test/REUSE 동결, 같은a35scene/profile/LP2/relay100/native. G1에서는credit미사용이지만 새 관측worker의 실제 정상종료도 검증한다. 결과는 아직 미확정.

### 적용 관측 후보 e991d521 실제 검증
- source124/manifeste991d52199a6f4b1fe14d065123f4683c20410b93d114a40d54e7f078ec73028. G1b9956543 24PASS·모든 정상 정리/noForce/residual[]. ZIP16550480/SHA256d4dcfb90d8d9970eb1fa2a09c1cbabd9d83bb23492d88dcd7fe82b697a5bda5b. G1creditnull 확인.
- 실제G2 67646d9d-f9b8-4c84-9836-26f79c552520 시작. 원본a35scene/profile·relay100/native·LP2 동일. 소스 동결. 이전G2실패를 제외해 연속성공으로 계산하지 않는다.
- native_stop 응답 success는 S 구현상 센서/적용worker의 stop 반환과 두failed=false 이후에만 true다. 현 runner는 이 bool만 보존하므로 응답JSON의 세부 계수 원본은 미기록이다. 최종 Task13 계측에서 소형 원본응답도 저장하고 동결 전체회귀로 검증할 필요가 있다.

### G2 67646d9d: 적용 관측 수신과 접촉 탐색 시간의 혼동
- source124/e991d521의 G2 최초 실패는 measured unload timeout, unload6.000000001초였다. 목표 FL 참조 상승0.007502873222m, 당시FL힘1.666260758N(<2)이지만 원래100ms 고유 접촉 해제 확인을 완료하지 못했다. 최근 적용 ACK들은 발행 후7.46–11.06ms 수신됐고 실제 적용 값/원본 시각을 확인했다. ACK 미수신이나200ms 초과가 최초 원인이 아니다.
- 참조 진행시간6.497615689초/실제phase9.608000001초였다. 기다린 tick의 저속 접촉 탐색 시간도 참조곡선과 함께 버려서 원래 탐색 속도보다 실제 진행이 느려진 결함이다. 원래2mm/s·최대10mm·unload6초를 바꾸지 않고, 검증된 안정·하중 구간의 원본ROS/wall 시간만 별도로 보존하는 수정을 회귀한다.
- 새 회귀 RED10.30초:60ms 중40ms의 접촉 탐색 예산이 사라짐. 이전 목표 미확인 동안 참조는 유지하고, 확인 후 실제 경과시간에 해당하는 유계 탐색만 소비한다. 안정/하중 조건을 잃으면 저장 예산을 버리고, 원래200ms/control gap/phase timeout을 유지한다. G1은 기존 경로를 유지한다.
- ZIP19617164/SHA256f9320d5f08de12a7fb49ea6342d5ab03ed110f3a17af697046002aaff593e92a; 원본·소스·설치 보존.
- 종료 정정: engine_exit/parent_reaped/모든receiver·journal join은true, noForce/residual[]지만 runtime_exit는false다. 모델이FAULT로 들어간 뒤 crawl.stopped가false로 남아 shutdown measured_stop이시간초과했다. 다른정리단계는true다. 회수/잔여없음을 정상runtime종료로 간주하지 않는다. 앞선 진행 설명의 ‘정상정리’ 표현은 이 차이를 확인한 뒤 정정했다. 이 fault 뒤 실측정지 미확정은 남은 문제이며, 원본 판정을 바꾸지 않는다.

- task8-contact-fault-landing-green 실행은41개의 진행표시만 남고 종료요약 없이 exec code1로 끝났다. PASS/완료로 집계하지 않는다. 직후 기본권한 WSL열거는E_ACCESSDENIED, 승인된일반jinho ps조회는성공했고잔여pytest/engine없음을확인했다. 중단원인은아직미확정이며소스FAIL로단정하지않는다. 다음진단은단일실행 시작/종료UTC·monotonic·boot_id·PID/PPID/명령/로그SHA를별도저장하고재시도루프를두지않는다.
- 종료요약 부재 근인 확정: captured 실행은 same_boot=true, pytest returncode1이었다. 단일 ROS 시험을 -vv -s로 실행한 task8-domain235-diagnostic에서 FastDDS가 Calculated port number is too high / domainId over232를 출력하고 첫 ROS 초기화에서 종료하는 것을 재현했다. 잘못 선택한 진단 도메인235가 원인이다. 기본 WSL 열거 E_ACCESSDENIED는 관리된 권한 경계의 별도 관측이며 WSL/시스템 고장 증거로 삼지 않는다. 이전 환경중단 가설을 철회한다.
- domain233/234의 기존 순수 수학 시험은 ROS를 생성하지 않으므로 그 결과와 별개다. 실제 엔진 domain159와 과거 scope/DDS domain229~231은 범위 내였다. 진단 helper에0..232 사전 검사를 추가하고221에서 동일 소스 mixed 회귀를 새 UUID 없는 고유label로 실행한다. 모든 실패와 원본 로그를 유지한다.
- contact fault landing valid-domain221 회귀50PASS55.00초, start/end 동일boot/returncode0/로그SHA6570c336fa0e66c9a1bad6e1516947e25051139a40a49c2271f1d4eeb8d7167a. 원래fault reason/generation/explicit-stop 유지, stale·다른hardfault에서는새명령없음, 안전착지속도/원래deadline·실측settle 유지. 실제 fault 착지 검증은 아직남았다.
- 같은 contact-time 원인의 touchdown회귀 RED9.23초→양접촉탐색/보행/착지/G1 50PASS47.29초. unload부분52PASS55.12초는그전단계다.
- 실제 엔진 새 동결 전에 worker stop원본응답 누락을 함께수정한다. RED11.41초 확인. 최대4096byte 소형원본만 저장·검증, sensor/applied join과published+overwritten=submitted, nonnegative계수/server success/engine_exit_ack=false 모두필요. 대형 trace JSON의 join뒤검증은유지한다. incomplete/badACK로정상runtime을판정하지않는다. 이 계측 변경도새source hash에포함한다.

- Worker stop원본/두join/계수 계약 RED11.41초→기존trace/nativeprobe/splitobserver/clock 포함39PASS52.16초. 실제엔진미실행상태에서계측까지묶어동결한다. N재설치와8패키지감사 후에새G1→정리/원본보존→같은고정본G2를진행한다. 제한적fault착지는실제물리회복아직미검증이다.

- 접촉탐색·faultSTOP·worker종료원본 후보 Nbuild11.2초/8패키지감사PASS. 실제G1 7c8a6243-dfa8-4ca6-ac0f-88209afe52a3 시작. 원본a35scene/profile/LP2/relay100/native 유지, 소스·시험·REUSE 동결. actualfault착지나전체G2성공은아직미확정.

### 고정본76ca4d03의 실제 검증
- source124/manifest76ca4d03f30113b5eeb53df4636d597a3f6eb6e20b24e72693e579d3b78812f9. G1 7c8a6243 24PASS/runtime·engine·모든receiver·worker정상종료/reap/noForce/residual[]. 원본worker응답 sensor/apply jointrue, submit779/publish779/overwrite0/dropbusy4(비차단복사시도누락수). Native stop을engine종료ACK로바꾸지않는다.
- ZIP17100542/SHA2565fe6f860a7bc5659d2f785e41bca05c92e1d14247219357527bf101a6e697f51. 모든원본보존.
- 같은고정본 G2 f7810468-2f89-4ca9-a4fe-2d9eef7109ab 시작. 장면/설치/LP2/relay100/native동일. 첫FAIL은보존하고연속성공계산을중단한다. actualfault안전착지와전체G2는아직미검증.

### G2 f7810468의 최초 원인 정정과 수신 경로 분리
- source124/76ca4d03, 이동 전 최초 crawl first_stop은 guard:ros_age이다. ROS13222000000/판정wall33639757800, 선택guard13008000000/최초수신33439118900: ROS214ms/수신 후200.6389ms. 마지막joints:ros_age는후속hardfault상태로최초원인과구분한다.
- 독립전체/mission관측기에는 guard13182000000이각33627237700/33618413900에 도착해첫판정보다앞서새발행이존재함을확인했다. 이것으로Crawl이해당메시지를받았다고단정하거나선택age를대체하지않는다.
- 같은구간guard_receipts의SYSTEMcallback시각이DDS수신SYSTEM보다약2.21초작고,실제guard/crawl로그에Command SYSTEM clock backstep경고가남았다. 원본ROS/monotonic은계속증가했다. 시계역행과해당consumer지연의인과경로는아직미확정이므로최소판별측정한다. 시스템시계/드라이버/권한은변경하지않는다.
- runtime_exit=false(실측STOPPED미확정), engine_exit=true/parentreaped/모든관측worker·receiver·journal회수/noForce/residual[]. nativeworker원본join/계수검증true. ZIP6577964/SHA8ca5aa008746e3ce48538ce0278110d2a46a923cfadadc42cbe75ba432ee763a. 이전실패는제외하거나성공으로바꾸지않는다.

### 2026-10-26 재개: 시스템 시각과 수신 실행기를 분리한 최소 진단
- HEAD4e87f6f/branch13-5 및 기존 Ch13 변경을 보존했다. 사용자13.4 교육문서40723byte는 수정하지 않았다. 실제 엔진 없음/이전 f781 원본 회수·아카이브 완료에서 시작했다.
- 첫 DDS진단01a25fc0 실패는 rclpy MessageInfo가 dict인데 속성으로 접근한 helper 오류다. 두 자식 종료 뒤 receiver.json 부재로 부모가 실패했다. 원본 실패 로그/진단소스를 보존했고 런타임 결함이나 정상 측정으로 집계하지 않았다.
- 수정 helper49aceb75의97fa92d2: 동일boot/UID1000/domain222, 발행4000/수신3334, 최대발행간격22.48295ms/수신117.795013ms/수신captureage20.240504ms, 양 executor jointrue/exit0. SYSTEM 약±2.3초 변화7개가 있었지만 최대 수신 공백 근처에는 변화가 없다. 상관관계만으로 원인을 확정하지 않는다.
- receiver만 SingleThreadedExecutor로 바꾼 helperb80d8d49의5154f26b: 발행4000/수신4000, 최대발행21.0094ms/수신21.5026ms/captureage1.407ms, 양jointrue/exit0. SYSTEM 변동7개는 여전히 있다. 같은 부하·topic/QoS·주기에서 pool 수신 경로의 비용을 분리했다. 실제 제어/물리 인수로 대체하지 않는다.
- 무ROS clock관측b4fe2343:7272표본/sameboot, SYSTEM 최소delta -2294863115ns지만 MONO최소delta10050516ns, syscall구간최대105900ns. 시간 서비스 원인 단독 확정은 하지 않는다. 커널6.18.40.1/clocksource hyperv_clocksource_tsc_page/systemd-timesyncd active 상태를 읽기만 했다.
- 설치 FastDDS2.14.7/rmw8.4.4/rclpy7.1.12. upstream FastDDS5019와 v2.14.7 DataReaderHistory.cpp의 sourceTimestamp 비교, rclpy1223의 pool 성능 사례를 검토했다. 외부 소스·underlay·clock/service 설정 변경 없음.
- 새 회귀: 모델 executor를 전혀 dispatch하지 않아도 guard/contact/final command의 원본 수신만 진행해야 한다. 기존구조 RED10.65초→relay100 전용 별도 직렬 수신 후보8PASS9.67초(기존 clock/control 격리 포함). 모델/관절 명령 단일 소유권·모든 원본 age·native controller는 유지하며 수신 실패는 sticky/no restart, 종료는 stop/join 후 ROS 자원 파괴다. 실제 엔진 재검증은 아직 남았다.
- 독립 수신 remap 회귀는 처음 RED11.37초(새 토픽에 구독자0)였다. 부모 lifecycle 노드에서 기존 remap/namespace를 한번 resolve한 절대 토픽을 전달해 수정했다. 수신 노드는 전역 node-name remap을 상속하지 않는다. 이후 실제DDS 원본수신·remap·sticky callback실패/no restart/join +기존 clock/control 격리·안전/lifecycle 19PASS32.72초(-Werror). 독립 첫 회귀8PASS9.67초와 구분한다. 추가owner/credit/clockscope→N재설치/8audit 후 실제새G1/G2가 필요하다.
- 추가 owner/credit/command SYSTEM clock/scope 회귀30PASS44.44초, N재설치12.9초(total14.2), 8패키지 바이트 감사 PASS. 새 고정 소스 후보의 MuJoCo G1 608eeec8-a551-4386-990d-0b8ee0e40280 시작. 같은a35scene/profile/LP2/relay100/native이며 runtime/tests/REUSE 동결. 실측·모든 worker join·정상 engine/runtime·reap·원본copySHA/archive 전에는 다음 엔진을 시작하지 않는다.

### 직렬 수신 고정본의 실제 G1 및 G2 연속 인수 선언
- source125/manifest8715b4baa4eb87a372ab68893b127ebe485b4181b77c823331a13a229d17f253. MuJoCo G1 608eeec8 24/24PASS. 실측STOP/deactivate/carry terminal/native stop/consumer/clock/runtime/engine/parent reap 정상, 강제 종료 없음/잔여[]. 새 수신 worker 원본 로그 owned_serial_waitset/alivefalse/joinedtrue/errornull 확인. journal28708=written28708/jointrue.
- ZIP17504817/SHA256b987f7720bd425be5d295ecc7b2b4597421e49748e61fcd97b0c055f66381faa. 원본·source/install 해시를 보존했다. 같은 고정 소스·설치·장면·모드로 다음 G2를 연속 성공3회 검증의 첫 실행으로 시작한다. 하나라도 실패하면 해당 실패를 포함해 기록하고 시리즈를 중단한다. 소스 수정이나 실패 제외로 연속 성공을 만들지 않는다. 이번 G1 1회는 아직 3회 성공이 아니다.

### 고정125파일8715b4ba G2 cbe25816: 시리즈 첫 실패로 중단
- 최초 모델 실패는 shift timeout; measured support/settle not gained. ROS93461999999/최초fault wall380422770304, phase start89821999999, 계획2.625초에 실제경과3.64초이나 참조진행2.097903740초였다. 뒤의 carry:not_ready_or_binding은 후속 guard 상태다. guard age 실패는 이번 최초 원인이 아니다.
- 최근16개 실제적용 ACK 중8개는 최초수신이 판정wall보다 빨랐지만 capture가 판정ROS보다 미래여서 해당 판정에서 보류됐다. 최초수신 지연은 약3~13ms였다. 미래데이터를 조기허용하거나 timeout을 늘리지 않는다. 동일모델의 TimeSource 수신이 아직 pool에 남아 있어 원본 시각 갱신 경로를 별도 최소 회귀로 분리한다. 후보의 효과 단독 확정 전에는 성공을 주장하지 않는다.
- runtime_exit=false(실측STOPPED미확정), engine_exit/parentreap/native worker 두join/독립관측기·journal jointrue, noForce/residual[]. 새Crawl ingress도원본system.log에alivefalse/joinedtrue/errornull. 실패를 제외한 2/3번째 실행은 하지 않았다.
- 원본ZIP50893584/SHA25657e8e6b4d80040a295589066aadb6d0596e5fa7eab52e43bb69dff85ae78157a. 원본·source/install·실패회귀를 보존했다.
- 원래TimeSource의단일구독/콜백/ROSClock을유지하되 model pool dispatch 없이 실제Clock메시지가그대로반영돼야하는회귀 RED16.08초. 공개Node create/destroy_subscription만위임해기존원본clock구독을같은직렬수신노드에두는후보를구현한다. 부모clock값·시계발행자·해상도·모든age/deadline·native모터변경없음. worker는부모생성완료후한번시작하며종료/join뒤자원파괴,재시작금지. 기본native /clock은기존경로다.
- 첫 관련batch10PASS 뒤 기본native clock_pause시험에서 command_clock_step_requires_restart 활성화거부1FAIL35.92초. 이시험경로는새relay수신을사용하지않으며DDS SYSTEM역행고정검사가발동했다. 원본실패로그를보존하고PASS로집계하지않는다. 시각서비스/clocksource를수정하지않고동일부팅원본clock관측후새구독해제/재생성시험과관련회귀를판별한다.
- 원래TimeSource 직렬수신 후보의 구독 해제/재생성·원본나노초·독립수신·안전/lifecycle 회귀20PASS31.10초. owner/실제ACK/command SYSTEM/scope30PASS46.62초. N재설치13.7초(total15.1), 8패키지바이트감사PASS. 앞선10PASS/1FAIL원본은유지한다. 동일부팅clock관측3ad83ede는7302표본/최대offset변동2355437440ns/마지막변동uptime81.503초를기록했다. 시간서비스·시스템시계는수정하지않았으며관측뒤시험통과를환경문제해결로간주하지않는다. 새후보의실제G1/G2는원래profile/장면/모든인수기준으로새로검증한다.

### TimeSource 후보67377652의 G1 e0d6af30: 인수 도구 역할 매핑 누락
- 물리 교정 이전 control clock consumer scope or actual process ownership differs로FAIL. relay구독은정확히5개였으나이전인수도구가crawl_controller_ingress대신crawl_controller이름만기대했다. 수신노드변경을인수도구에함께반영하지않은구현누락이다. 원본control_clock_graph.json의passedfalse를바꾸지않는다.
- runtime/engine/parentreap/수신·nativeworker/관측기·journal 정상 종료, noForce/residual[]. ZIP7465482/SHA256a49fac5747e9f209e722ea4db676ee33403292f84f0c2ded875e4dc1fffdd736. 동일본G2는실행하지않았다.
- 새역할회귀 RED10.85초. 기대역할5개·단일producer·원본clock누출금지를그대로두고ingress노드가같은기존CRAWL PID/UID/PPID/PGID/startticks/살아있는native TID/선택설치entrypoint와연결됨을추가검증한다. 수신노드의자체보고만으로PASS하지않고실제/proc/스크립트hash를대조한다. producer의기존실제library/PID검사도유지한다. 새로운모터publisher/clockpublisher는추가하지않는다.
- 첫attestation batch19PASS/1FAIL18.15초는가짜/proc fixture의start_ticks열이한칸밀린자료오류였다. 실제process_identity구현은변경하지않고fixture열인덱스를정확히고쳤다. 실패로그는보존하고고정관련회귀후재설치/8audit를다시진행한다.
- TimeSource 실제역할/소유권 보완 고정 회귀45PASS20.68초, N재설치14.5초(total15.5)/8패키지일치감사PASS. 동일a35장면/프로파일/LP2/relay100/native의 새G1 9d296bc8-1f99-494a-83f4-2bfc0bdc3751 시작. Runtime/test/REUSE동결; 실제원본/정상종료/회수/해시보존완료까지다음엔진없음.

### 고정125파일6c8a1475 실제 G1 및 새 G2 시리즈 선언
- MuJoCo G1 9d296bc8 24/24PASS. source manifest6c8a147587c1b014518a2eab1fef384a9e8f533c2c110117aebf334fe6e8ac04. 실제Crawl PID1396/PPID·PGID1385/start19633/nativeTID1591·선택설치entrypointSHA를/proc와대조했다. 구독소유노드는crawl_controller_ingress/Clock구독1개/기존relay소비자정확5개다.
- 종료원본동일PID/TID alivefalse/joinedtrue/errornull/clock_subscriptions[]. 실측STOP/deactivate/carry terminal/native worker·consumer·clock/runtime·engine·독립관측기·journal회수정상/parentreaped/noForce/residual[]. 이전e0의도구실패를성공으로바꾸지않는다.
- ZIP17143579/SHA256a233f6cf5e60f9fd245431937288b01a8c45914e60564a2cb91b55412c58b76a. 같은고정본/설치본/장면/모드의다음G2를3회연속검증첫실행으로선언한다. 최초FAIL시실패를보존하고2·3회는시작하지않는다. 이G1도아직고정본3회성공이아니다.

### 고정6c8a1475 G2 cb59e4f3 및 촬영 시각 표현 판별
- 첫SHIFT timeout: 실제3.626초/참조2.299778583초/필요2.625초. 최초원인은guard가아닌모델SHIFT deadline이며이번시리즈도첫FAIL에서중단했다. runtime_exit=false, engine/모든수신·nativeworker·관측기·journal회수/parentreaped/noForce/residual[]. ZIP16153443/SHA256a45e8514121682f0da4f9757b84c7cc91facbcd99c9dfa3bd79b96cd058c17bc.
- 최근16적용ACK중10개에미래판정이있고4개는정확히1ns차이다. 별도의2~6ms차이도있으므로이한원인만으로전체실패가해결된다고주장하지않는다.
- 외부원본READONLY확인: /home/jinho/ch13_mujoco_ws/src/mujoco_ros2_control HEAD c261f5552edf124d1000a23fb25b6c07cadeb807/statusclean/LICENSE Apache-2.0. mujoco_simulation.cpp1681~1695 publish_clock은floor(정수초)+소수부*1e9의uint32절단이다. Ch13새appliedACK는llround(data.time*1e9)라동일물리capture가1ns앞선표현이될수있다. 외부source/clock/underlay수정없음.
- 최소plugin회귀에35.29/35.33/35.59/93.284 capture를추가해고정underlay표현과정확일치를요구한다. 미래허용오차나now/최신clock치환은사용하지않는다. 첫inline셸호출은PowerShell인자확장으로WSL출력경로가비어root쓰기거부로build전실패했다. 안전한전용스크립트로고쳐원본plugin상대RED를실행중이며아직제품변환코드는수정하지않았다.
- 실제고정plugin RED160ms에서35.29/35.33촬영의ACK가원본Clock표현보다각1ns앞서는불일치를확인했다. Ch13pre_stepACK의시각표현3구문만고정원본의sec/fraction절단과일치시켰다. NASA2025원본저작권·Apache-2.0·외부clean커밋c261f555·원본파일/함수를수정파일/양REUSE에보존했다. 외부/clock·underlay·기존관측/trace/camera·controller/물리변경없음.
- 별도순수credit5PASS27.95초는진짜미래1ns를여전히거부하고원래deadline/firstreceipt를유지함을확인한다. 미래허용오차로문제를덮지않았다. SN재빌드/일치감사/실제pluginGREEN/센서CTest를진행중이며새실제G1/G2의단독해결은미검증이다.
- 적용사건capture표현 수정의 실제plugin회귀 RED160ms→GREEN416ms. 기존SCTest10target 전부PASS5.42초, SN재빌드S2분22초/N23.1초(total2분46초)/8패키지source-install감사PASS. 빌드stderr의tl_expected제거예정경고는외부ROS기존의존성deprecation이며원본을수정하지않았다. 순수credit5PASS27.95초(진짜미래1ns거부)와구분해기록한다. 새실제G1/G2를동일장면/조건/모든기준으로검증하며아직물리성공을주장하지않는다.

### 2026-10-27 SYSTEM 시각 역행 시동 실패와 잘못된 종료 전이
- 새capture표현 고정be70bbd827c8865fb68a99906000cc66ee0c7a2ad3bbec50be6f175a10c08e89의 G1 d332482d는시동중Final command SYSTEM clock backstep을감지했고activation rejected:command_clock_step_requires_restart로거부됐다. 물리교정전실패다. startup의기존‘no response’문구는ChangeState응답success=false에message필드가없어서붙은잘못된기본표현이며,응답부재로단정하지않는다. 새문구는실제부정응답과None을구분한다.
- 이후runner가이미INACTIVE인노드에DEACTIVATE(4)를보내rcl_lifecycle unregistered transition 예외로Crawl프로세스exit1이발생했다. 실제상태GetState와소유자active보고를맞춘뒤ACTIVE에서만전이하는수정을별도진행한다. 미활성해제는실측STOP을대신하지않는다. 잘못된/일시적/모순상태는거부하며자동활성화·재시작은하지않는다.
- runtime_exit=false, engine_exit/parentreaped/nativeworker/관측기·journal회수정상/noForce/residual[]. ZIP7794751/SHA256f186a0114b2bf5e9d7412fc39be5d0511a4e88755154903f13ce98b4acb608cf. 이실행과이전연속실패모두보존하며G2는시작하지않았다.
- lifecycle상태별실제RPC 회귀 RED16.47초. 수정batch의최초4RPC상태와종료순서시험은통과했으나기존startup bootstrap_empty 사례가WAIT_CARRY에남아batch15PASS/1FAIL24.63초로끝났다. 원인미확정이므로PASS로집계하지않고실패로그를보존한다. 고정sleep만늘려통과시키지않는다.
- 새 read-only ClockStabilityGate 회귀 RED10.57초→게이트/실제 lifecycle RPC/기존 종료순서15PASS12.69초. 현재제품변경은Ch13 clock_preflight.py와명시적사전관측script, GetState기반유효전이종료, startup부정응답표현이다. clock서비스·시스템설정/실제ROSclock·미래거부·모든인수기준변경없음. 기존bootstrap_empty WAIT_CARRY 실패는별도동일부팅안정관측후같은관련시험을원본clock변화기록과함께판별하고성공으로간주하지않는다.

### 2026-10-27 재개: 시각과 오류 종료의 독립 판별

- HEAD4e87f6f/feat/ch13-section-13-5 및 사용자13.4 문서40723bytes 보존. 중단된 엔진 잔여 없음.
- `preflight-mujoco-pairs-cd782528-3efb-405e-8c83-6e753f4f9d4e`: 원본 시각40초 READY 뒤 실제 시동/종료 회귀19PASS30.51초. 같은 부팅 uptime131.280초의 SYSTEM offset +1,594,437,682ns로 엔진0회에서 시리즈 중단. 서비스 설정 변경 없음. 40초 사전 관측은 이후 시각 안정 보증이 아니다.
- 사용자가 WSL timesyncd 일시 중지·복원 비교만 추가 승인. `timesync-comparison-fa3e279b-5db5-4176-a0e1-ee42f9a0305b`: root 래퍼는 서비스 stop/start만 수행하고 검증은 UID1000. 75초 관측7319건, uptime40.863초 SYSTEM offset -7,327,677,899ns 한 번. 엔진0회, child1, finally 서비스 active/enabled 원래 상태 복원 확인. ‘서비스를 끄면 모든 변동이 사라진다’는 가설 기각. 다음은 기존40초quiet/150초deadline 게이트로 초기 보정 뒤 안정 구간을 평가하고 Windows 원본 시각과 비교한다. 첫 원본은 보존하며 초기75초 변동0회라는 추가 진단조건을 실제 인수 조건으로 오해하지 않는다.
- SHIFT timeout 뒤 FAULT 즉시 반환이 measured-stop 평가 자체를 막는 독립 결함을 재현. `task8-fault-hold-stop-red`16.55초; `...-green`26.47초와 `...-diagnostic`16.71초 실패는 시험 입력이 아직 -0.015695/-0.010326m/s로 이동 중인 오류였고 보존. 이상적 hold를 실제0 속도로 고친 뒤 기존 반환 분기에서 `...-stationary-red`17.41초 실패 확인, 수정 후 `...-stationary-green`15PASS26.16초. 실제 ROS 상태 경계 `task8-fault-hold-status-red`20.77초 FAIL을 확인했다. 후속 관련 회귀/설치 감사 진행 중. 물리 성공 주장은 없음.
### 고정127파일 884f2171: 실제 G1 PASS, G2 물리 실패와 정상 종료

- 같은 시각 서비스 일시중지 세션511bb764: 원본75초7371건, offset 최대50,876ns/1ms 변동0. 이어40초quiet 및 시동 회귀19PASS35.39초, 관측 중 변동0. Windows 원본150초 관측 host-clock-f895fb3f 별도 보존. 이 비교는 부팅/시점 차이가 있어 서비스 단독 인과를 확정하지 않는다.
- G1 a15f63f9:24필수 PASS, source127 manifest884f2171036b944d56e95c6714f983f13d326555188a6ccd172fee4d8116e6f2. runtime/engine/회수/journal/terminal 정상, 강제 없음/잔여[]. ZIP17347797bytes SHA3a431ab2fa4b27b1dad51015408b4f3e8bafdf29ad08073f9f5c341104dc4ce2.
- 같은본 G2 45d1585f: 최초 SHIFT timeout ROS34.887999999/phase31.257999999=3.630초, 참조2.227365359/필요2.625초. FAIL 유지/시리즈 첫실패 중단/2·3회 없음. 새 읽기전용 오류 정지는 실제 measured_stop·비활성화·carry terminal·native worker·consumers·clock 모두true, runtime_exit/engine_exit/parent_reaped/journal_writer_joined true, forced_cleanupfalse/residual[]. ZIP16134405bytes SHAd64f5665ea98ac3f34ed965b92a54dec35d6c10c014d13b23c8fed64065ab3fc. 서비스 finally active/enabled 복원 확인.
- 적용16건 중4건은 당시decision보다미래. 원본176발행/117변경의 step 합2.227365359초가 실제참조와정확히일치. 마지막변경시각을쓰는 단순후보2.330834832초도필요2.625초미달로기각/제품미적용. 파생 analysis-reference-progress/analysis-ack-clock JSON은 원본 밖에 저장했다.
- 별도 cadence DDS RED13.57초: 같은 원본ROS1.1초에서 walltimer가100ms에5회실행. MuJoCo G2 relay100에만 원본ROSTimer50Hz+200ms별도wallwatchdog 최소수정. 첫관련배치 새두검사등10PASS 뒤 기존native deactivation회귀가 SYSTEM역행 latch로 활성화거부, 전체FAIL29.92초 보존. 이 실패를 새cadence 성공으로 집계하지 않는다. 동일승인일시중지세션에서 회귀→N빌드/8감사→코드동결→새실제G1/G2를 이어검증한다.
### cadence 고정본의 실제 결과 및 허용 참조 시각 분리

- timesync 비교 d0bb3423: 초기 보정1회 뒤40초quiet, 관련33PASS54.66초, N14.9초/8감사PASS, 재차40초quiet/시동19PASS23.77초. 모두원본시각/일반사용자검증. 서비스active-enabled복원확인.
- 고정127/6e207d5701b3572a27c4e8c10bad46b234d6e6e2f01ed6044e0fa996536da929의 G1 b94f2264:24PASS/전체정상. ZIP17252144 SHA d2a0419892ccf707875cd89db8e89cb898d147a74c664bb23f10dcfaa73b6d1a.
- 같은본G2 4c5a8bb8:FAIL SHIFTactual3.626초/ref2.654710865초(필요2.625). 실제settled시작34.263999999→fault34.287999999로24ms만확보/요구100ms미달. 제어주기단독으로해결됐다고쓰지않는다. 마지막16ACK중future1건. measuredSTOP/terminal/runtime_exit/engine_exit/reap/journal정상, noForce/residual[]. ZIP16194889 SHA817a3a4acb99714aef049a6a7743d70bc6e8ec8bd2b4dce6d5b76144996a6b10. 2·3회없음.
- 새 최소회귀: 대기tick20ms 뒤 확인tick30ms에서 참조가10ms만진행하는 시각결합 RED11.33초. 원본안전clock과last_advanceclock을분리해확인된출력마다최대20ms1단계만진행. 누락단계catchup금지/60ms대기뒤에도20ms상한회귀추가. pure50PASS42.50초(기존expiry/phase/보행/FAULT포함). 이50PASS는실제엔진인수가아니다. 새설치/실제G1/G2필요.
### 고정27969d82 실패 후 이벤트 기반 확인 일정 재검토

- G1 b854d75124PASS/정상 종료. source127 manifest27969d827ef0096029ced7376d6e3763f9155843cdb5766188ef8ae082105d81, ZIP16391002 SHAd974fc062d1c647f7f07c0779da528a199a7b982e3f4069f3ee0f9dd25d675d0.
- 같은본G2 b248ef1b: 더뒤SHIFT ROS59.084→62.714,3.630초/ref2.232406058,FAIL. 원본166발행/112변경,최근16ACK중미래2건. 초기단계개선만으로전체해결X. 정상measuredSTOP·terminal·runtime·engine·회수/journal/noForce/residual[], ZIP31461195 SHA002b06e3dd243859ef8dbe155076e6ae53135c4624a6dc20df5c77a0c4b8fd29. 서비스822bb697finally active/enabled복원true. 연속2·3회미실행.
- 구조 검토: 최소132단계와100ms안정이3.625초안에필요한데50Hz주기조회와singlepending직렬대기가단계들을다음주기로미룬다. 기존modelgroup GuardCondition1개와기존Clock/ACK수신자가알림만보내는구조로재설계. 원본header/첫receipt/단일Clock·모델소유자/기존native controller/200ms·20ms·phase deadline모두유지.
- Puregate RED13.07초→첫greenFAIL18.53초(False take가wait를지움)→수정8PASS13.08초. 실제DDS Clock/ACK 알림 RED15.26초→미래보류·단일깨우기등12PASS31.63초.
- 추가활성소유자회귀 첫배치2PASS1FAIL32.27초는고정0.8초를계획완료로가정한시험준비오류. 실제첫제출까지유계대기로바꿈. 후속FAIL15.13초는ROS가먼저200ms만료해wall197.56ms에정지한올바른동작을시험이거부한것; 원래max(ROS age,wall age)>200ms로고친뒤1PASS17.24초. 두실패원본보존/제품기준완화없음. 후속일시중지세션관련회귀/설치감사/새실제G1/G2필요.
### 이벤트 고정본33f66671 판별과 계산 시작 기준 보정

- 승인서비스656b3944: quiet/합동50PASS80.07초/N15.7초·8감사/추가quiet·19PASS24.10초. source128 manifest33f66671131a1abf2941aa63b6d9a64dd4b30b355df45278f68c56db366806c9.
- G1 c5a1e9ea24PASS/정상종료, ZIP17044066 SHA7cedbd400d47f0103290c522fc996d8e53474f6e2595ccbfda156069a2e49591.
- 같은본G2 a2edc08a FAIL: 첫SHIFT3.628초/ref2.080초, notification109/issue123. 정상measuredSTOP·terminal/runtime/engine·reap/noForce/residual[] 유지. ZIP16266057 SHAff5e49b35f87144caf855a9c3e47cc605cc539724e68fdda3633ba4ffdb8ec3e. 다음회차미실행, 서비스active-enabled복원true.
- profile-held-reference-2fdea813 사후수치: actual상태측정/IK중앙값0.6687/0.6292ms, 실제판단→발행중앙값7.040098ms/최대28.831901ms. live profiler가아니고실제GIL/lock/DDScost를식별하지않는다. IK19ms가설로제품최적화안함.
- 새gate가실제발행시각뒤로20ms를더기다리는오류를 확인. 실제ROS15ms계산입력RED22.38초. 기준을기존제어주기의판단시작ROS/wall로수정하되실제발행의원래ACK200ms기준유지. 원래required_checks/ctrl_hz50/raw-smoothed실발행≥20ms/팔5Hz/물리조건불변. 관련12PASS36.82초. 새설치/실제G1/G2필요.
### 고정ec0c7d85 판별과 기한 알림 후보

- 서비스3a09c489: 합동51PASS88.80초/N16.4초·8감사/추가quiet·시동19PASS24.43초. G1 0e8c5bd024PASS/정상종료. source128 manifestec0c7d853107a0056751da3e5ca9bd0c77e197b93e99a68569ccce82b92d6771, ZIP17609970 SHAabaa5c9742b6b91cc84c65b2cb20d6510f16c3a234d2c54cbd588e7c5fac33c9.
- 같은본G2 258e04e1 FAIL: SHIFT3.626초/ref2.660초/settled46ms(요구100ms). STOP/terminal/runtime/engine/reap정상/noForce/residual[]. ZIP15398968 SHAd86594f6b3d5a0ec2371fbfcebeb27826011aa5b3196ccc81b30f37ca57df428. 첫실패시리즈중단/서비스active-enabled복원true.
- 원본Clock 339발행/2표본차337중16건이20ms미만. analysis-clock-spacing-... JSON에원본SHA와분포저장. 시각해상도를wall rate 필터로중복사용하지않고원본양의진행+wall판단20ms를분리한다. 궤적은원본18ms만진행/외삽없음. 새일회성due timer는자료수신과별개로기한에알림검사만수행/소유자가모든원래gate재검증/종료시취소.
- RED기한누락11.74초와ROSrate필터9.98초. 첫green3PASS1FAIL25.42초는이전ROS20ms시험가정한곳잔존, wall경계로수정. 수정된원본18ms진행/DDS/Clockpause/lease/취소26PASS42.70초. 도구의--maxfail=1이추가옵션뒤에있어첫묶음은1FAIL에서멈췄고두번째RED는별도로실행했다. 실제엔진성공아님. 새합동회귀/빌드/8감사/실제G1/G2필요.
# 2026-10-27 재개: 5805faa8 실제 결과와 종료 확인

- 서비스 비교 `timesync-comparison-d1b9b4c0-a500-4aff-b21a-772d6a55be4a` 종료: restored=true/restoration_pending=false, 원래 active/enabled 복원. 검증은 UID1000. 관련54PASS80.55s, N build15.1s, 8패키지 설치 감사PASS.
- G1 `832d0582-dcce-46a6-8877-ad097f1a8e23`: PASS24, source128/manifest5805faa8bbf210c0503088aa3f849b3bb6e1817e5090d97686962a4173898e8f. ZIP17423124 bytes/SHA3d9a86c3e3a435d143b8aa4cf0e1c6cf7a64354f334ab88b555a636f78d5d538.
- G2 `5400af69-d166-4623-84f4-0ab9d97dba55`: FAIL 후속SHIFT64.130→67.764/ref2.636/required2.625/settled10ms. 기존 required_checks 유지. 정상 실측STOP·terminal·runtime/engine/회수, 강제종료없음/잔여[]. ZIP33497576 bytes/SHA03502bcd68112617799f1975713d09fc48cf42c6203233401a8fbd10d3f55c5c. 원본 보존. 첫 실패에서3쌍 시험 중단, 성공만 선별하지 않음.
- 현재 엔진 없음. 이른 ROS 주기 callback과 예약 wall 판단의 경쟁 가설에 대해 실제ROS 회귀를 먼저 실행한다. 물리·phase·시각·native controller 변경 없음.


## 고정d6ddf9b8의 후속 실패와 고정 예정 주기 후보
- G1 528d7e3e-2551-4d43-ba5b-f387bc7ac148 PASS24. ZIP17207379 bytes/SHA b7279f0e688c4a3b798a51ca229e5c4bc3d398b3dec3f199677902612801ece3.
- 동일128소스 manifest d6ddf9b8f8c8c18a11d17d89632b8555d15119de3224d3ff136997ec30ff303a의 G2 16bf2676-36a7-4d22-8cea-77cfb202e46d FAIL: SHIFT116.632→120.264/ref2.652/settled42ms. 모든 이전 기준 유지. 정상 실측STOP·terminal·runtime/engine·reap/noForce/residual[]. ZIP64046172 bytes/SHA c1a673b4a06115dbb9183d6f06d0cba61ae6001e41712eeee664dda2fef18bcc. 첫FAIL에서 중단. ed32d7d0 서비스 active/enabled 복원 true.
- 누적 rolling20ms 예약의 drift RED10.37초→기존 예정 위상 유지/놓친slot 건너뛰기 후보와 관련34PASS62.35초. 원래 required_checks·200ms·phase/물리·원본 시각·native 모터 불변. 기존 신규 순수 gate 시험의 경계 한 곳만 고정 위상으로 교정하며 동 slot 조기 결정 거부는 유지.
- 실제 후보 판별 wrapper fbbcb0c8 진행 중: 빌드/8감사→원래40초quiet/150초deadline→원본시각감시19시동종료→새G1/G2. 수신자 없는 빌드 전 중복 사전관측만 제거. 실행 완료/물리 성공은 아직 주장하지 않는다.

## 고정1e075591 실제 실패와 실제 판단 경계 진단
- G1 dcd79bdd-1acb-4183-bd64-6eae4c2eb780 PASS24; 128source manifest1e0755913b3c0b3a7744b0be7569eb05e340de921ec9a17539f8dab9862650ad. ZIP16275199 bytes/SHA8b0baebc510987e0c4b914c189746c0c007619f30ac9740e4630a3b7d6b1c126.
- G2 38127c13-b99f-4016-b7c7-6fd5944d617e FAIL SHIFT48.720→52.352/ref2.347309254/required2.625/settled없음. 평균 판단간격29.958ms. 첫FAIL중단, 정상STOP·terminal·runtime/engine·회수/noForce/residual[]. ZIP23456364 bytes/SHA7a924ae993248a0d1d6c5a395e33d307ccf2ab29c4c9ed6c46e4768238c55b40. fbbcb0c8 서비스active/enabled복원true.
- 무엔진 owner-cost 비교는 거부. 상세 diagnostic-owner-cost-assessment.json: 시험ACK 충돌 및 여러worker profiler집계, serial guard만료→pstats예외→정리실패. 소유1112/UID1000/실행인수/boot 확인 뒤 SIGINT, C++abort. 정상 종료 아님/엔진0/이비교로제품실행기변경없음. pgrep으로두소유진단잔여없음 확인.
- 실제owner 경계 기록 RED12.40초→관련19PASS47.79초. 기존시각/관측/명령/판정은그대로, 숫자512개고정ring만추가. f922cdfe 서비스비교안에서 Nbuild/8감사·40quiet150·19시동후 새G1/G2진단1쌍 진행중. 최종연속인수나물리성공으로미리세지않음.

## 실제 model 비용 판별과 미발행 IK 생략 후보
- 고정baa3fdb58ce25a3d8aaf05146b120c1d6a8cc92ac2da229104c85ed9ee57ff79/128: G1 02376984-2ed7-4215-9a01-ef6e7ec879e4 PASS24, ZIP17180757/SHAffca8167f44133ee4e54b749e3eb900e2bb45610d35f73fbae154d3434278029. G2 71eb7444-4a56-4d7d-9dea-147e8d112f82 FAIL SHIFT149.032→152.664/ref2.697461240/settled72ms. 정상STOP/terminal/runtime·engine·회수/noForce/residual[]. ZIP82073838/SHA7ff8db4d849c63a68d6a4fc9f54133ce9108422bb33d86479c323f1a9e715191. f922cdfe 서비스복원true.
- 사후실제경계196개/전단계포함: published139 model평균7.187ms·whole8.690, held56 model8.495·whole10.099. 원본reportSHA24567173f76384804f1c76fbd1b139a523e9eb64e9b739000b94ca626c74ba4b, 분석JSON SHA04405a041f74986190820c2b03b98c72670d38a7dc9acb05d4928ee6fbf45efc. wall경과이므로CPU만의비용은아직미확정.
- 적용대기의미발행IK생략 RED10.40→32PASS54.55. 같은callback의CPU시각/nativeTID관측 RED12.07→8PASS28.15. 새스레드/실행기/physics/clock/기준변경없음. 구32회귀이후추가는관측숫자뿐이며관련8회귀로확인.
- 6ba8bc8d 승인서비스비교안에서N13.3초/8감사통과후 새G1/G2진단1쌍 진행. 최종3연속성공/완료로미리집계하지않는다.

## 실제 CPU 대조 뒤 고정 질량 형상 컴파일
- 고정1df5e300 G1d4a99361 PASS24/정상회수. G217c2e988 FAIL SHIFT425.062→428.704/ref2.438803596/no settle. 정상STOP·terminal·runtime/engine·회수/noForce/residual[]. ZIP237174841/SHA336fe61b99f4ae7e1eea12a139e57abe4a7dd34db9342c7f73d36515f2a21a7c, 원본+4part보존. 6ba8bc8d 서비스복원true.
- CPU사후분석: published126 model평균CPU4.468/wall7.969ms, held55 CPU2.607/wall4.317ms. 원본reportSHA74b1178db4be3b3a52de91e6e55a0999548d09e4b8a5fd16ed5a939b5bd64c85. 분석JSON은원본과분리보존.
- 고정 질량점 재구성 RED10.59초→초기23PASS18.91초. URDF/정확질량점 key bounded32, static moments/fixed transforms compile, currentq/pose매회갱신. 임의100관절/월드pose의독립fullFK가중합2e-12m내일치·질량변경·NaN/음수·지지·보행·정지 등69PASS57.40초.
- benchmark-static-mass-a6c48026-64db-4334-9d1e-6d91ab5edd5e:200회씩교대/동일실제상태, before431a426c→after4395c14c. CPU평균.4693705→.2404515ms, 최대값차5.55e-17m. offline수학비교이며실제엔진인수대신안됨. 비교도구import오류1회는별도실패JSON에보존/도구만수정.
- 승인서비스비교4884d54c 안에서N빌드12.6초/8설치감사PASS→40quiet150→19시동종료/시각감시→고정본G1/G2세쌍진행. 첫FAIL중단. 아직물리성공/최종연속성공을주장하지않는다. 기존모터/physics/50Hz/phase/모든측정기준불변.

## fad0dc84 실제 결과와 G2 모델 직접 실행 비교
- G1 08d04232-ac69-4c96-94e8-5967e05d1229 PASS24 incl.nativeCoM; 고정128manifestfad0dc8405e802f70c3da7f83d34d1917993775208e39e2964f37ff3e19593b1. ZIP17795333/SHA11a4f5b7b1972e2bd28de80f67dd8e885bf499077fa8fe7837f096df038d6c54.
- 동일본 G2 bad1d687-6ffd-4d1a-b968-2573e12792cb FAIL SHIFT56.430→60.060/ref2.470689023/settled없음. 정상STOP·terminal·runtime/engine·회수/noForce/residual[]. ZIP30914260/SHA7435a34fcef0b705c223fe74e1175596706e8dd39ab25fecc90704f2d4085977. 첫FAIL에서세쌍중단/나머지미실행. 4884d54c 서비스active/enabled복원true.
- 실제188판단의published125 wholeCPU6.295/wall10.618ms,modelCPU4.496/wall8.557ms. held62 modelCPU2.228/wall4.242ms. reportSHAd7f6f35d8715a1de75d15427d8c00fde8296d1bf09336ec8a49b979cffc35055. CPU최적화만으로G2성공못함. 특정GIL/스레드원인은아직확정하지않음.
- G2 모델 callback pool 경계 제거 scopedSingleThreadedExecutor RED11.39→24PASS44.66 실제DDS/clock/ACK/pause/transition/stop. 모델lock 작업중Clock/contact/guard/command독립수신을G1/G2두scope에서확인. 다른role/native/G1/GZ/모터/physics/50Hz/phase/모든실측기준유지. cProfile실패비교는근거로재사용안함. 시험alive조회는실제snapshot API사용.
- 0abec70a 승인서비스비교안에서새빌드·8감사·원본시각검증·19시동회귀뒤G1/G2세쌍진행. source/tests/REUSE고정. 다음실제source실행기TID와물리결과로판별하며성공을미리집계하지않는다.

## 2026-10-27: e5 관측 종료 실패 보존·전체 기록 사후 검사

고정128/2cb4 G1 0f84fe58 PASS24. G2 e5f0aea4는 전체 이동 시퀀스 후 full observer 20초 join 미확인으로 FAIL/teardown 미작성이다. 엔진/runtime clean exit0 로그와 현재 잔여[] 확인은 소급 정상 종료 증명이 아니다. root wrapper0abec70a는 restored:true. 새 엔진은 아직 없다.

원본/소스/시험을 incomplete-observer-recovery-4652fb42-cbe9-4f65-84d4-0a837f1a3faf와 ZIP/6parts로 보존했다. ZIP381439173bytes/SHA6951d3b95532ada642b3aaa7e9d547b543089c10d7c6f2f64d82c261b6287e84. 원본 result FAIL·teardown 없음 유지. 재현 JSON34.552s→pickle/hash41.870s→해제42.957s; 압축 동시 실행이므로 원래 시간과 동일시하지 않는다. OOM 증거 없음.

후보 수정: child receiver/writer/ROS 종료→실제join→parent 전체 원본 JSON/hash/count 검사, 중복 mission 객체 복원 제거. 20초/기준 유지. RED10.21→첫ROS회귀 invalidHandle(7PASS/1FAIL)→capture report before destroy 수정→68PASS162.26s. runner 예외 시 partial teardown 기록과 G2 direct owner metadata 포함. 아직 설치 감사/새 엔진 인수 전이다.

기존 e5의58619 운영 프레임 전부 사후 평가: CoM/slip/지지/자세/관절/고유촬영 PASS, sensor_freshness FAIL. body만3건: ROS706.498/capture706.268/age230ms, 수신 후15.873~24.821ms. 원본→odom 발행2.352ms/전달0.156ms/관측콜백213.556ms. 해당 GC span 없음. 같은 구간 frame callback은 wall75.90ms/CPU12.41ms, 다른 frame은 wall60.95ms/CPU44.77ms였다. journal frame JSON 직렬화 max60.40ms도 기록됨. trace 부재를 콜백 부재로 단정하지 않는다. 원본 FAIL을 승격하지 않는다. 파생 근거는 observer-postmortem-e5f0aea4에 있다.

공간: native 원본과보관ZIP·각파일SHA를검증한 미추적중복17개/12185003903bytes만 압축보관전환. storage-compaction-1044f6af-666d-443d-b8d6-4ecae12f671b.json에member/path/복원방법. 원본삭제·실패선별없음. Cfree20.77GB.

다음: 관측 ingress 지연의 계산/대기 최소재현·해결 → 관련시험 → 새8패키지설치감사/고정본G1/G2연속3 → GZ/후진 → Nav2 Tasks9–14/최종회귀/commitpush. 모든안전/물리/권한범위유지. native controller interpolation은구현안함/에이전트없음/사용자13.4문서40723untouched/HEAD4e87branch13-5.

## 2026-10-27: 관측 기록 경로 고정·새 MuJoCo 세쌍 시작

원본 e5 전체 검사에서 body 신선도3건 실패를 발견해 장기 실행을 바로 반복하지 않았다. 같은 구간의 frame JSON 최대60.40ms와 콜백 최대75.90ms/별도 CPU44.77ms를 확인했다. 원시 pickle 비교 ac4983c3는빠르지만 전체 Python 검사39b70e74 후보는JSON보다느려 엔진 미투입으로 기록했다. 최종은 실시간 제어 검사 그대로, 전체 증거 검사/JSON 변환만 종료 후에 수행한다. 전체 관측기의 바이너리 원본과 모든 JSON을 보존한다.

ROS 고정 배열 하위형과 순환 입력을 각각 실패 회귀로 확인했다. 과거 코드의 전체Python검사39b7 후보는거부했고, 최종 C Pickler의 숫자 하위형 정규화와 post-join 전체 검증을 구현했다. 관련76PASS 뒤 최종79PASS/115.22초. 모든 실패 로그 유지. 최신 소스가 포함된 ad0099b4 비용 비교: JSON평균CPU0.344131ms, capture0.0276186ms; 코드SHA dc83d221eb1c0badbbbb7f68c8e9a3d51a4de86b77da43781c4bf84cae7d9f85. 실제 엔진 성공을 의미하지 않는다.

root wrapper36137/서비스비교36054a3a-0993-4dab-b133-74ffa69f08a2는복원대기다. 일반사용자로 N빌드15.8초/8패키지설치감사PASS. preflight3034ef50-68e8-4e62-b914-1dc9a1b87856, boot ef7d210f-442e-4b49-be57-dafc6e13f783. 초기1회시각변동후원래40초quiet/150초관측PASS. 이어19시동회귀/새고정본G1→G2세쌍을순차실행한다. 첫실패에서중단하며재시도/성공선별없음. 소스/테스트/REUSE동결, 실제 엔진 중 CPU시험금지. native모터/원본시각/물리/모든인수기준유지. 새 실행의 UUID·SHA·종료·전체 결과는 이후 기록한다.

## 2026-10-27: 4163의 참조 진행 예산 판별과 고수준 시간 법칙 후보

129/c675 고정본G1aade PASS24, G24163 FAIL94.094→97.726초/참조1.954639684초/필요2.625초/발행101회. 신선도·지지·자세·q·slip·CoM·액션terminal·전체관측join/exit0·runtime/engine정상·회수/noForce/residual[]는통과했다. G2ZIP50403732/SHA1ed0b25bc7220b1c311a09608ffd7be4d6bc8d1a0136394a11af4585a63d4304, 원본FAIL보존/2·3쌍미실행. service36054a3a복원true.

관측기예약상실가설은실제ROS1PASS14.30초로기각(시험labelred의실제결과PASS). 기존controller797행에defer복원이이미있어제품수정없다. 원래native control/TF검사기는사후재실행bothtrue(assessor-diagnostic8bc4fc07); 원본은조기fault로출처인수단계를마치지못해checksfalse유지. carry는raw측정true/owner는crawl fault전파로false. 이를소급PASS로바꾸지않는다.

정확한프로필/실패상태의오프라인profilec33207ad는measureCPU.419ms/solve.615ms다. 실제callbackmodelCPU5.267ms와다른범위이므로오프라인결과만으로엔진을설명하지않는다. 직접예산계산: 101회×20ms≤2.02초라2.625초곡선을3.632초기한안에끝낼수없다.

새후보는MuJoCo G2/relay100의고수준곡선만ACK확인후두원래시계경과시간의작은값안에서샘플링한다. 기본/G1/Gazebo20ms·native모터/100Hz·50Hz목표·200ms·단일pending/ACK·geometry/phase예산·기존물리기준을유지한다. native보간없음. 원본101시각의fixture5100bytes는보고서SHA589518c98cd9d0d6b081842fd75bc2e921084ef1491ff4e4018853ee93d8530a로출처기록. 초기PowerShell배열추출실패는전용Python추출기로바로잡았으며엔진/원본수정없음.

API누락RED13.03초→관련25PASS36.30초→추가scope의G1에G2전용프로필을준fixture4PASS/1FAIL→올바른scope입력후43PASS61.53초. 두시계범위/18ms보존/기존마감·ACK·센서/정지·quintic와bump속도·실제ROS범위확인. 단위시험은새엔진인수가아니다. 다음은새8패키지설치감사와고정본G1/G2세쌍, 첫FAIL중단이다.

## 2026-10-28: SWING 참조 상한 복구 후 재개

직전 129파일 manifest1b50624e의 G1 45772380은24PASS였으나 G2 242efeba는238.624초 SWING에서 그리퍼 실측속도0.005889m/s(상한0.005)로 실패했다. 다른 인수 결과와 관계없이 원본FAIL을 유지한다. 실제 액션 terminal·전체관측join/exit0·엔진/runtime 정상종료·회수·강제종료없음·잔여[]를 확인했고 서비스4ca978fa는복원true다. 첫FAIL에서2·3쌍중단. 원본과 고정소스 ZIP SHA b9bbccbc7305b967c1aa90a3251cf9f108f5beb1643a98d955d9f491f118c4d5 및 두분할을 보존했다.

보고서8391540a의 원시 명령구간에서 SWING에도 변경된 시간법칙이 적용된 것을 확인했다. 새 applied_shift_elapsed는 시간 보정을 SHIFT에만 한정하고 SWING을 원래20ms로 복구한다. 실제90.239003ms 간격의 SWING 회귀는 수정 전FAIL20.64초, 수정 후 관련44PASS77.35초다. native100Hz controller/보간·물리·게인·시간/속도 인수 기준은 변경하지 않았다. 현재 수정본의 실제 엔진 인수는 아직 미확인이다.

저장공간 정리는 원본과 검증된 압축본을 모두 보존하고 git 미추적 중복 복사만 제거했다. 두번째 storage-compaction-e0466b15-6622-470a-b107-3bc59ef9b52e는49파일/12,082,811,462bytes, 모든 항목에 native원본·복사·ZIP멤버 SHA 일치와 복구 위치를 기록했다. 재개 시 해당 작업 종료·서비스active·관련 엔진 프로세스없음을 확인했다. 다음은 새 빌드/8패키지 설치감사→원래 clock preflight→고정본 G1/G2세쌍이며 첫FAIL에서중단한다.

## 2026-10-28: 새 고정본 사전 검사 실패와 공유 시계 차단 요인

N빌드12.8초/전체13.8초와8패키지설치감사PASS. wrapper1899/서비스e4d9e6b6는24.04서비스만중지하고일반사용자검증을실행했다. preflighta386ee08는원래150초deadline에5회+2.926~2.958초step으로FAIL. 엔진0회·시동19회귀미진입·G1/G2미진입이다. finally에서서비스active/enabled복원true. 원본samplesSHA7304de7b5b188dfd278519aba91333c424c73849462ae1ed477f78bec1719e7f보존.

단순재실행대신원본시계와adjtimex(modes=0)를일반사용자로측정했다. clock-discipline18ba439f의150초6414표본: tick9166µs/freq32.221710ppm일정, MONOTONIC/RAW중앙값0.916994, REALTIME+2.9초step4회. host43de3fba의UTC/QPC는0.99999885. cross-boundary12e96348은Windows QPC로각Linux조회전후를감싼7표본/60초: 호스트59.777~60.093초에RAW59.93584초/MONOTONIC54.97213초. 오차구간을포함해게스트MONOTONIC약8.3%느림확인. 분석2fd204f1에방법·원본SHA·호출구간과비율구간보존. 시각설정변경없음.

추가readonly환경2fe63f82에서22.04도실행중이고별도timesyncdPID108 active/enabled,24.04와boot87c3/time:[4026531834]동일확인. 원격Docker컨테이너0개. 24.04만중지한비교는공유커널전체NTP중지가아니었다. tick설정주체·특정프로세스인과는미확정이며외부성공사례로대체하지않는다. 공식Linux/Microsoft자료를참고한추가범위/복원설계를기존CLOCK_BLOCKER문서에추가하고, 두서비스·커널tick임시보정은사용자승인을요청했으나아직미실행이다.

현재129파일+실패회귀/진단의체크포인트7b3d3197: manifest8740e8e417be2cf860d1f0cae711ef5df98e2b5621a1fa270009731e58bf7428, ZIP1031095bytes/SHA3339e3396e06d421953d59dd83aac4082e1cd87f9bb499a37e0ac9fec1a33a04. ZIP전멤버SHA/CRC검증. 보존helper의첫실행은ROSsetup과set-u미호환으로진입전실패했고,helper만set-e/pipefail로맞춰수정후성공했다. 제품·엔진·설치소스변경없음. gitdiffCh01~12없음/사용자13.4문서40723bytes유지/HEAD4e87유지/remote13-5부재/commit·push미실행이다. 다음의공유커널조작은기존24.04서비스승인으로실행하지않는다.

## 2026-10-28: 추가 승인 비교와 단일 시간 소유자 판별

사용자는 두 Ubuntu 서비스와 커널 tick의 임시 보정·복원 비교를 명시적으로 승인했다. 실제 조작 전에 가짜 시스템으로 부분 실패·응답 유실·외부 쓰기·부팅 변경·복원 실패를 재현했다. RED0.12초 뒤11PASS0.19초. `temporary-clock-safety-c4b30d6b-fe37-4f22-9b05-157e1bbd5b84`에 명령·출력·수정 전후 방법을 보존했다.

수동 비교 `clock-normalization-7f639ebf-9e7b-430b-8126-8b28355e76f3`는 두 서비스 중지와 tick10000 적용을 확인했으나3.706442초에9166으로 바뀌어 조기 QPC 비율에서 실패했다. 전체150초 원본6433표본을 끝까지 기록했고114.8044167초에10000으로 자연 복귀한 것을 발견했다. 반복 덮어쓰기는 하지 않았다. 엔진0회, 두 서비스·소유한 tick 복원 확인, 잔여[]다. 외부 서비스 재개 뒤 최종 tick10000은 별도 기록했다. 원본FAIL은 유지한다.

WSL 관리 영역의 일반 사용자 chronyc 응답은 PHC0를 선택한 별도 시계 보정기를 보여줬다. 공식 WSL init의 StartTimeSyncAgent(blob4970608d)와 chrony 기본 maxslewrate83333.333ppm을 참고했다. 8.3%의 느린 진행과 약115초 자연 수렴은 큰 위상오차의 slew에 부합한다. 개별 syscall 발신자를 추적한 것은 아니다. 원인 분석을 ‘고정된 tick 오염’에서 ‘놓친 관리 영역 시계 보정기와 배포판 NTP의 복수 소유권’으로 갱신했다. 분석 `clock-normalization-analysis-2cccc73f-b146-4be4-b020-b8541dbd4150`에 원본 SHA·전환 시각·관리 영역 실제 응답을 저장했다.

다음 판별은 승인 범위보다 좁게 두 서비스만 중지하고 kernel/chrony는 바꾸지 않는다. 초기 helper가 정상 보정값9167을 거절한 ffcb399d는 조작0회다. 원본의 잘못된 ‘복원 미확정’ 문구는 보존하되 실제로 복원할 변경이 없었음을 이 기록에 명시한다. 서비스 전용 모드의 정상 보정 범위와 조작 전 거절 수명을 회귀로 재현했고, 추가8FAIL→19PASS 뒤4FAIL→최종23PASS0.20초다. 기존 수동 쓰기의 엄격한 소유권 검사는 유지했다. 보행/엔진 인수 기준 변경은 없다.

현재 `clock-single-owner-ef602f86-39a8-4c04-bf60-ccc346ac010e`(일반 사용자 부모3848)의 두 서비스 복원은 **대기 중**이다. tick쓰기0회다. RAW180초 이내의 읽기 전용 수렴은129표본·정상 진행률/명목tick40초 연속으로 통과했다. 지속 QPC 연결의60초 측정에서 RAW/MONO/REALTIME 비율구간은 약0.99888~1.00009, 추가150초 전체 기록은tick10000/step0/PASS다. 원래 preflight40초quiet/150초deadline도0jumps로 통과했고19시동·종료 회귀26.18초 PASS다. N빌드10.6초/8패키지 설치 감사도 통과했다.

같은 고정129파일 manifest8740e8e4의 실제 MuJoCo G1 `08d56c64-466b-42d1-8511-30ffd4bc76f7`는24/24 PASS다. 실제 terminal·전체 관측/엔진/runtime 정상 종료·회수·강제 종료 없음·잔여[]를 확인했다. source/archive를 다음 엔진 전에 검증했으며 ZIP19,639,389bytes/SHA55a4cfc275ab1d42f3cefd5ba199894ca05ffc9180c5c34fbedbfa879f744a22다. 이후 새 G2 `095dc500-a35b-48c5-b81c-cef60e90f964`를 첫쌍으로 실행 중이다. G2 성공이나3회 연속 완료로 아직 집계하지 않는다. 첫FAIL 중단·실행 중 source/tests/REUSE 동결·CPU시험 금지·순차엔진 원칙을 유지한다.

## 2026-10-28: 095 전체 판정과 다음 최소 수정

위 G2 095dc500은30/31PASS·전체FAIL로종료했다. 전진0.40m·좌우0.30rad·최종STOPPED·모든원본센서/TF/소유권·실제terminal·관측프로세스/engine/runtime정상종료·회수·강제종료없음·잔여[]·finalization_complete를확인했다. 유일한실패는carry_measured_settle이며,raw최대grip속도0.005524331430764654m/s>0.005다. arm오차0.0193214rad/속도0.0196135rad/s,grip오차0.00013474m는기준안이다. liveowner는PASS/firstfaultnull이지만독립rawFAIL이우선한다. 전체원본을검사했으며나쁜1프레임을제거하지않았다.

source129/manifest8740e8e4, G2ZIP680294215bytes/SHA150cc22e532d9b06092c875205540b2257554a2c37c874aebe5f4a9dd0205ba6와10분할SHA를보존했다. ce6d5429시리즈는첫FAIL에서중단했고2·3쌍미실행이다. ef602f86부모3848/exec79586은exit1/두서비스복원true/수동tick쓰기0회로종료했다. 새엔진·서비스임대없음이다.

메모리에전체JSON을올리지않은2회스트리밍분석에서60,137운영프레임·56,970고유관절촬영중초과1프레임/고유1건을찾았다. carry-spike6bcb0034에방법·전체초과·first/max·±0.6초관측/관절115/native56/carry59/frame60을보존했다. 발생은right/SHIFT1061.613999988초다. 약10ms전FRcalf목표변화0.0055214877rad,그리퍼목표는전구간0.015m. 기록된native표본간격과정확한publisher시각은구분한다. rootshutdown구간이아닌실제운영초과다.

한가설: 지연뒤SHIFT참조가한번에진행하며실제다리목표단차가몸체/팔에전달된다. 후보는SHIFT상한200→40ms두주기로만축소,SWING/G1/GZ20ms·nativecontroller/게인/30Nm·200ms센서·기존phase/900/600기한유지다. 과거4163원본101시각의40ms예산2.934486726초≥2.625초를먼저계산했다. 7998bytesfixture출처를기록하고RED16.26초→순수관련6PASS13.57초다. 물리성공은새실제실행으로판별해야한다.

보존공간이약8.7GB까지줄어, native원본·ZIP·복사SHA가같은git미추적중복만압축보관전환했다. a2ffb224는107파일/16,007,123,812bytes,3d8e6fc2는189파일/8,020,721,200bytes. 원본native/ZIP은삭제하지않았고파일별복구위치를보존했다. 현재가용공간은약35.45GB다. 다음G2는종료후native원본에서ZIP으로직접스트리밍해큰저장소복사본을만들지않는opt-in을사용한다. required_checks와압축본내용/경로는유지한다.

새저장경로는누락assertionRED0.17초→6PASS0.16초,엔진시작전FAIL보존RED0.25초→최종7PASS3.11초다. 실제archive-storage-parity-c75ed6de에서095의42파일/7,390,227,745bytes전체SHA가이미검증한원본ZIP멤버와일치함을확인했다. 원본파일삭제0/원본FAIL유지다. 실행방법을각보존본에추가하며,이검사는새엔진인수가아니다. 다음은수정본N빌드/8감사→관련ROS회귀→원래시계preflight/19시동회귀→고정본G1/G2세쌍이다.

## 2026-10-28: 실제 엔진 전의 추가 관측·시험 준비 결함

0277506f는追加읽기전용수렴180RAW초에서FAIL했다. 원본152.1984667초에9167→10833으로보정방향전환,엔진0회/관련ROS미진입/두서비스복원true다. 관리영역chrony는변경하지않았다. 원래ClockStabilityGate40초quiet/150초deadline은그대로두고,서비스전환직후의추가진단대기만명시300RAW초로분리했다. 기본180과명시300선택/같은40초정상진행률조건의회귀RED0.19초→복원/수렴24PASS0.58초다. 같은조건을무조건반복하지않고chronyc잔여보정량을8초마다읽기전용기록한다.

후속e75bf5b7은수렴135표본·QPC60초·추가150초tick10000/step0를통과했다. N빌드18.2초/전체19.9초와8패키지설치감사도PASS다. 관련8파일회귀는42PASS/1FAIL76.57초였다. 실패는탐색용ACK깨우기시험의활성화준비단계로guard:ros_age다. 엔진은시작하지않았고e75부모6844/exec38914는exit1·두서비스복원true로종료했다.40ms보행후보의실제실패로집계하지않는다.

이한사례를분리해구성콜백에시험용250ms지연을주니guard:wall_age로동일한활성화전제누락을재현했다(RED11.94초). 구성전피드백이200ms임대를넘었는데즉시활성화를요청하던시험준비순서였다. 프로덕션의거절은올바른동작이며코드를수정하지않았다. 구성완료뒤새시험용피드백을보내고활성화를한번만요청하도록해같은ACK시험1PASS14.13초다. 거절된활성화재시도·오래된수신메시지의stamp갱신·프로덕션허용오차변경은없다. ACK대기예약/terminal검증assertion은그대로유지한다. 새전체관련회귀와실제고정본인수는이후진행한다.

### 2026-10-28 dd4d2f4a: 새 고정본의 실제 G1 통과, G2 진행
두 서비스만 임시 중지한 비교다. 읽기 전용 수렴117표본·QPC60초(.998870~1.000093)·150초tick10000/step0 PASS. N빌드15.9초/전체17.1초·8패키지 설치 감사·관련43시험69.03초·원래preflight·19시동/종료31.42초 PASS. 새 manifest a5e10a9c7efefe1ae0e967cd3e3370c6b00a2e1d5c17876862c2a807cec8ab66의 실제 MuJoCo G1 f703c47f-e832-4f37-9c7e-fa63006f2d03은24/24 PASS, 실제terminal/정상runtime/엔진종료/부모회수/강제정리없음/잔여[]다. 다음 엔진 전 source/archive를 검증한 뒤 G2 1e495a5d-5316-400c-bbdd-9bd70dfb47e6을 시작했다. 첫FAIL중단·세쌍 사전선언은 유지하며 아직 G2 또는 연속 인수 성공으로 세지 않는다. 두 서비스 복원은 부모 세션 종료까지 대기 중이다.


### 2026-10-28 dd4d 종료 및 후속 판별
G2 1e495a5d는SHIFT3.636초에서ref2.145161177초/필요2.625초로FAIL이다. required31중24true/7false. 원본gripmax0.002177m/s·armmax0.010202rad/s는PASS지만owner는model fault를sticky하게유지하므로carry전체FAIL을그대로기록했다. 실제terminal/runtime/engine정상종료·parentreaped·noforce·residual[]; ZIP8a27fc518d74361023c0505118cbf056c4eb7ea31a192ce12e06b8d8a10d6673로보존했다. dd4d부모는exit1·두서비스복원true다. 2·3쌍무실행. 분석reference-progress/decision-cost-1e495를추가했으나원래FAIL은변경하지않았다.
순수exact measure/solve profile7c133과전체syntheticadvance ed4db는약1.0ms, 합성DDS116db는127callback/중앙2.93ms로실제model9.42wall/5.55CPU차이를재현하지못했다. 시스템GIL/renderer/수식하나를원인으로확정하지않는다. 선택적세부model경계를RED13.17→중간ROS기대목록1FAIL/6PASS24.99→관련46PASS54.89로검증했다. 새실제판별은한쌍만사전선언하며기존최종3회연속을대신하지않는다. 기존시계·물리·모든인수기준유지/새행동수정없음.


### 2026-10-28 204f 종료: 실제 세부 구간과 최소 산술 수정
G10401afc3은24PASS·ZIP18,238,915/SHA c0428651ef71d5c2a4980f87499b8b92267ce64a55dad23f275a9f595e80b6e0다. 같은129 source manifest58f57b9664aa8256f70e37fc6647913784010bb47dc8a1659113fbf12144ed35의G20deb6465는약0.12m전진뒤SHIFT3.636초/75발행/ref2.521346294<2.625로FAIL이다. ZIP137,123,186/SHA5d9831c2055ce81cd1d970027dff970c1fe5bdd3c55dfe7d9b4e32d862198ac9와분할목록을보존했다. 실제terminal/정상runtime·엔진종료/reaped/noforce/residual[]·두서비스복원true다. tick쓰기0/chrony수정없음. 원본FAIL과진단한쌍을최종3회인수로세지않는다.
190.956초에기존읽기전용report를한번호출하고,호출전512숫자행의JSON SHA988b34e42a5c42622c6c9f833f0c1b997ddc5f6bf97da0d37606c94567f8c1ff와stdout/stderr를native보존했다. repo diagnostic-live-0deb6465의method/result로분석했으며이후서비스부하영향을관측원본과분리한다. 실패구간model_total9.553wall/4.917CPU중앙, solve2.622/2.246ms. 다른구간에도tail분포가있어단일원인으로확정하지않았다.
다음최소수정은같은충돌기하의작은NumPy배열을scalar3원소로계산하는것이다. native 모터보간은구현하지않았다. tuple/기하계약RED10.46→geometry16PASS9.44. 동일q CPU기준은기존1.139배FAIL(43449340)→수정후3.230배PASS(4d52b18d). 다음관련회귀/설치/실제검증은아직미완료다.


scalar기하후속75시험60.18초PASS: 회전/오프셋URDF360자세·선분1,500개/반전·실제PythonMuJoCo기하·IK/지지/보행/참조/ROS관측. 성능후보의새native성공은아직미검증이다. 반복CPU측정/범위확대없이새N설치감사→원래clock/startup→실제한쌍으로판별한다. G20deb분석생성방법을derived artifact 옆 .method.py로기록했다.


### 2026-10-28 scalar 후보 고정본 실제 재검증 시작
clock99789a33은수렴174표본/195RAW초·QPC60초·추가150초tick10000/step0, N빌드20.3초/전체22.0·8패키지감사·원래preflight0jumps·19시동/종료29.07초를통과했다. 같은129 runtime source fb10a4f945a4fc53f4460e8589f58bad3c7267db33cbc47afafeb697dce724ce의G1462d6ed4-24ae-4d1f-9823-dbfd66f741f6은24/24 PASS·정상runtime/engine종료·실제terminal·회수/noforce/residual[]다. ZIP17,671,250/SHAa6a22a671a3427fab7c1dd0fcca6362c8c4ca5f5962e4893435866445d754557로보존뒤G2cf1fad26-0963-4c37-bc9b-8853e982aba0을시작했다. 결과미확정/한쌍진단이며연속최종인수로세지않는다. 두서비스복원대기;원본·안전기준·native모터유지,실제엔진중추가CPU작업없음.


### Task8 같은 고정본 연속 시험의 중복 방지 규칙
기록시각(호스트UTC): 2026-10-27T18:53:32.4638022+00:00. 현재cf1fad26의전체원본/종료판정은아직확인하지않았다. runtime source fb10a4f945a4fc53f4460e8589f58bad3c7267db33cbc47afafeb697dce724ce·동일설치·동일물리의G1462d6ed4/G2cf1fad26이모든기존required_checks·실제terminal·정상종료/회수/잔여없음·archive까지PASS하면이완전한한쌍을같은고정본3회연속의첫회로삼는다. 그뒤변경없이다음두한쌍을기존--single-pair-diagnostic 실행기로순서대로추가한다. 한쌍만으로3회완료를주장하지않는다. 모든실행/부모/UUID를집계하고어느회든FAIL이면남은회중단·원본보존이며성공만선별하지않는다. source/install/profile가달라지거나다른실패가끼면세회연속의연결은무효다. 같은조건에서이미완료한성공한쌍을별도로버리고네번째반복을추가하는중복만피한다. 기존Nav2추가후최종동결전체회귀나양엔진조건을대체하지않는다.

## 2026-10-28 사용자 보존 정책 적용 완료

Evidence 논리 크기100,187,356,195 →11,960,433,874bytes. 감소88,226,922,321bytes/88.06%. Windows C: 실제 여유24,945,872,896 →47,137,292,288bytes. 306사본·793대용량 관측을 처리하고 원래 판정 SHA를 유지했다. 대표5종 전체 원본·현 G2실패 pin·미정리 실패 원본은 보존했다. 비대표 압축144개를 metadata 중심으로 바꾸고240샘플을 남겼다. 정책 도구55회귀33.35초·8패키지 설치 감사 PASS, 새 실제 엔진0회. 전후·보존·무결성 보고서는 `retention-storage-result-f0071251-c9d2-4332-81c2-589b6af8d67f.json`, `retention-application-0700e254-6fa8-4f0f-a773-3a5dcd4d0673.json`, `retention-trial-audit-b5897ba5-3923-4245-b53d-438180959db7.json`, `retention-archive-audit-30ac6066-a164-43f0-943e-9677476667df.json`이다. 이전 '모든 원본 보존'은 역사 기록이며 현재 재생 가능성은 retention 원장을 따른다.


- 2026-10-29 per-engine validation tooling: task8-engine-plan-root-red.log -> root-green 6/6. Correct native pytest lease/convergence/distro/model preparation 45/45 in15.03s; Windows harness import errors retained separately, not product verdicts. Gazebo explicit approved relay100/ramp20ms/50um/native_cdr profile is selected; MuJoCo keeps native motor reference. Generic serial driver exports only after owned normal reap and preserves first failure. Source/test/helper freeze before new clock admission; no automatic retries or section completion claim. Old interrupted52c0 lease stays unacknowledged; new baseline recovery is separate.
- e0f1c7bd engine0 stopped before child admission: exact copied Bash payload contained CRLF (set -e
 error). Original convergence/QPC/150s continuity PASS; validation_exit2; services restored=true, foreground_closed=true, residual[]. Preserved original payload and result; no engine PASS. Regression task8-engine-plan-posix-red7 with one intended failure -> green7/.175s. File bytes corrected to POSIX LF; root now rejects invalid line endings before service/platform operations. Actual Ubuntu24 bash -n and three Python compile checks exit0. Source/physics/control criteria unchanged. Next new root uses corrected frozen tool, not an automatic retry.

## 2026-10-29 Gazebo G1 복귀 정책의 범위 회귀

새 고정137소스 `3bdbec12...`의 실제 G1 `c1eec4a8`는 첫 고유 재접촉 때 원래 wall 예산이2.437초 남았지만, MuJoCo용 loaded 복귀 제동/느린 tail과1초 안정화가 들어가지 않아 실패했다. 실제 lift49고유 관측·carry 원본 오차/속도는 통과했으나 owner FAULT와 실측 STOPPED 미확정으로 정상 종료 인수는 실패다. 모든 프로세스 exit0·reap·강제정리 없음·잔여[]와 root8904913a의 두 서비스 복원/foreground close는 별도로 확인했다. G2는 실행하지 않았다.

가설 판별: 원본 controller_report에서 request/stages/vertical 및 SHA를 최소 fixture `native_c1e_gazebo_return_budget.json`(SHA677c2afa...)로 남겼다. 기록된 시각에서 공통 loaded 정책의 동일 budget fault를 재현했다. Gazebo의 기존3연속 성공본 `af6da055` 보존 ZIP의 calibration.py SHA `3751c16b40dc6fff7fef803f484f309323b3b94e114228f84463d666e9f731f4`는0.02m/s·0.2m/s²의 bounded preload 법칙이며 loaded 제동이 없다. 이후 MuJoCo의 실제 충격 대응을 공통 G1에 적용한 범위 회귀다. CPU나 llvmpipe를 이 실패의 원인으로 단정하지 않는다.

결정: InPlaceCalibration/CrawlMachine에 명시적 return_policy를 전달한다. Gazebo owner는 기존 성공법칙 `bounded_preload`를 선택하며 MuJoCo 및 순수 계산 기본은 기존 `loaded_quintic`을 유지한다. 알 수 없는 값은 거부하고, fault 뒤 정책을 자동으로 바꾸거나 재시도하지 않는다. 일반 CRAWL·모터 적용·게인·30Nm·접촉·물리2ms·원래10초·측정 안정화와 인수 기준은 유지한다. Gazebo는 과거 성공법칙을 사용하지만 수정 후 현재 설치/소스로 실제 검증하기 전에는 성공으로 승격하지 않는다.

RED: 원본 budget 재현 통과 후 정책 인자 부재 FAIL(11.49초), 실제 ROS owner 설정에서 정책 부재 FAIL(14.09초). GREEN: 엔진별 설정/기록 시각 재생/force와 고유capture/속도·가속도/원래끝점·wall budget/MuJoCo loaded·jerk12시험27.28초 PASS. 이 재생은 동일 입력에 대한 참조 계산 비교이며 바뀐 궤적의 물리 접촉·carry·엔진 성공을 예측하지 않는다.
- Gazebo return-policy neighbours:81/81 PASS66.67s (inplace/preload/clock/gait/reference credit/ROS safety/native mass ownership/finalization), after12 targeted PASS27.28s. Freeze candidate sources/tests/REUSE/helpers before new actual Gazebo series; current engines/leases none.

## 2026-10-29 접촉 노드 종료 경계

Gazebo G1 `00facc19`(source137 manifest e2f838d2...)는 수정 후 교정·carry·하중·관절·TF·단일 소유권21개가 true, 실측 STOP/실제 terminal과 엔진/부모 exit0·회수·강제정리 없음·잔여[]였다. 그러나 contact adapter PID1975가 종료 중 RuntimeError(pybind call argument0 conversion)로 exit1이어서 공통 clean_shutdown이 정상 runtime/engine 두 항목을 false로 유지했고 전체23/25 FAIL이다. G2는 시작하지 않았다. rootf521의 서비스 복원·두 foreground 정상 close를 확인했다. 원본을 PASS로 바꾸지 않는다.

단순 실제 ROS service→SIGINT3회는 모두 정상으로, 같은 문구의 예외를 결정적으로 재현하지 못했다. 이 로그를 RED로 주장하지 않는다. 실제 Clock 콜백에 test-only gate를 넣고 SIGINT를 보내자 `CLOCK_CALLBACK_ENTERED` 뒤 본문 완료 없이 main이 정상처럼 반환하는 수명 위반이 재현됐다(19.42초 FAIL). 따라서 이 최소 재현이 pybind 내부의 정확한 throw 위치를 입증한다고 쓰지 않는다.

설치 rclpy7.1.12 wrapper와 공식 bd637294dd02b1c128422395c059fa06df8387a3의 events_executor.cpp(blob3b50f8892f74aa9ccc44aa6979559c9ca6b1e6a4)에서는 spin이 context 상태를 조회하고 shutdown exception 경로로 연결된다. contact adapter만 기본 rclpy signal 처리와 무기한 spin_once를 사용했고, 다른 navigation 역할은 기존 Ch13 vision.execution의 deferred SIGINT 계약을 사용했다. 통합 수명을 맞추는 최소 보정으로 contact adapter에도 같은 계약을 적용했다: signal은 종료 요청만 남김→진행 콜백 완료→joiner stop→executor join→node destroy→ROS shutdown. 일반 RuntimeError를 잡아 숨기거나 외부 rclpy를 수정하지 않는다.

실제 service/일반 SIGINT3회·진행 중 Clock 콜백 완료·접촉 값/원래capture/순번/거부·EventsExecutor metadata18시험21.71초 PASS다. 이는 엔진 전체 종료의 대체물이 아니며 새 고정본 실제 Gazebo에서 판별한다. Source delta는 contact adapter1개뿐이므로, 직전73개 참조 회귀의 소스를 SHA로 대조한 뒤 반복하지 않는다.18개 직접 회귀와 매번8패키지 설치 감사·원본 시계·19시동/종료 검사를 유지하며 최종 전범위 회귀는 별도 필수다.

## 2026-10-29 전체 G1 통과와 G2 원본 증거 경로

같은137소스 manifest `afbbe4834376d7156032b24851c27e3e5706afe4dcbcc25587527113c28c85a4`의 Gazebo G1 `65ce2fad-60da-41cf-b37b-8c3b9f9f706d`는25/25 PASS다. 실제 terminal·실측 STOP·contact adapter 포함 정상 runtime/engine exit·launch 부모 회수·journal join·강제정리 없음·잔여[]를 확인했다. ZIP1,843,620bytes SHA458dcfb4e8fb1faa9726f2b8cfd0ed5ea1ff0a2291a2b88ff0f404aa52c199d4다. 이는 현재 고정본 G1 한 번이며 G2/3연속/절 완료가 아니다.

후속 G2 `9affb1fd`는 engine_started=false/preflight_install에서 G1 증거를 거부했다. 새 bounded export는50MB 초과 원본을 native canonical 위치에만 두는데, G1→G2 도구가 원본 형제 파일이 없는 요약 복사본의 result 경로를 넘겼다. 원래 인수 검증기는 모든 artifact의 크기/SHA를 확인하므로 이 거절은 올바르다. no-engine teardown에 residual 필드가 없어 export도 거부됐고 이를 정상 회수로 바꾸지 않았다. rootae219023의 서비스 복원/foreground close/관련 프로세스[]를 확인했다.

최소 판별 `proof-root-discriminator-5b5cabaf-e31b-4c4b-886d-56426d19077f`: 같은 result SHA8bef76820fb306527d49bb6a4b04f2584891ca7a7e15789a685f74dac605a079를 입력하고 기존 전체 validate_profile을 그대로 사용했다. 요약 경로는 invalid_native_evidence, 실제 원본 경로는 accepted=true였다. 엔진은 시작하지 않았고, 거부된 G2의5개 작은 원본 메타데이터도 별도 바이트 복사/해시로 보존했다.

도구 수정: 요약 descriptor가 가리키는 동일 UID·이름·한정된 native 증거 경로를 확인하고 result/source/install/teardown의 원본·복사본 해시를 대조해 canonical result를 반환한다. 실제 제품 인수 검증은 그 원본 경로에서 다시 모든 artifact를 검증한다. FAIL 결과를 PASS로 만들거나 대용량 원본을 다시 복제하지 않는다. RED(경로 연결 함수 부재0.33초)→17개 보관/바인딩 변조/경로 이탈 거부 회귀0.37초 PASS다. 런타임137개 소스는 G1 통과본과 같고 새 실제 연속 시리즈로 진행한다.

## 2026-10-29 G2 세 번째 발의 지지 참조·정지 경계

G1 `8b8d0fce`가25/25 PASS한 같은137소스 afbbe483...에서 G2 `bd67d364`는 실제 전진 중 세 번째 FR 해제에 실패했다. ROS58.340초, SHIFT50.344초 시작/명목2.625초, unload53.200초 시작이다. 원래0.002m/s로10mm 참조 상한에 도달했으나 FR하중18.213N, 관절/몸체 FK의 발 중심은 초기 바닥보다 약0.000000116m 높아 여전히 지지 중이었다. 앞선 FL/RR은 이미 정상 swing/착지를 수행했고 참조z는 각각 측정 바닥 .0199497477/.0199497927이었다. G2 전체 FAIL/정상 정지 인수 미달을 보존했다. 프로세스 회수·강제정리 없음·잔여[] 및 root5abc의 서비스/foreground 복원은 확인했다. ZIP1,963,162bytes SHA17ace163862bf95fb95f92e260561ea701f35d0e8d65e95389d8e6286b2d3106이다.

`stance-preload-discriminator-1780e1a3-d30f-4f85-b9ad-3871cf8a8d8e`는 report SHA2773cf.../고정URDF/선택q·body·contact를 대조했다. 그 보고서의 held-q FK는 **실패 시점의 명령 몸통 좌표**로 평가한 값이므로 초기 활성화 프리로드 자체로 해석하지 않는다. 센서 촬영 시각 차이도 명시했다. 코드에서 확인된 참조 계약 결함은 reset이 보존한 모터의 하중 참조를 보행의 미래 위치 예측/실제 swing 종점에서 측정 floor로 덮어쓴다는 점이다. 이 결함이 남은18N의 충분 원인인지는 새 물리 실행으로 판별한다.

최소 단위 재현은 명시적인 이상 피드백+0.025rad encoder load offset이다(물리 엔진 아님). 초기 유지 높이 .0212087191 대신 측정 floor .0242733741을 종점으로 계획해3.065mm 참조를 잃었다(RED11.66초). 별도 contact-search는 기존 floor clamp 때문에 .0212087191→.0222733741의 위쪽 불연속을 만들었다(RED11.32초). 공통 원인은 명령 프리로드와 측정 바닥의 수명/의미 혼동이다.

변경 결정: flat scene 전용으로 reset에서 각 발의 held-command 세계z를 별도 보존한다. 향후 지지/IK 예측과 동일 연속 swing의 종점에 이 값을 사용하며, 실제 floor·anchor는 측정값 그대로 두어 slip/접촉 판정과 섞지 않는다. 별도 탐색은0.002m/s·기존1초/2mm 범위로만 내려가며 새 하한이 이전 참조를 위로 밀지 않도록 두 기준 중 낮은 높이를 사용한다. original10mm unload·2cm swing·8cm step·게인·30Nm·2ms·소유권·모든 실측 인수 기준은 유지한다. G1의 자체 original-preload 복귀 계약은 그대로다. 초기/이전 장/외부 모델은 수정하지 않는다.

별도 종료 결함: 높이 상한도 실제 네 발이 이미 하중을 지탱하는 실패인데 기존 read-only FAULT-stop 관측 대상에서 빠져 있었다(RED9.86초). 해당 SHIFT+알려진 unload 단계에만 기존 관측을 재사용한다. 명시적 STOP 이후에만 원래 신선도/네 발 하중/지지/속도·양 시계1초/고유capture를 확인한다. FAULT/원인/세대는 유지하고 모터 목표를 전혀 발행하지 않는다. 한 번의 센서/지지 손실 뒤 자동 회복하지 않는다.

9개 직접 참조/정지 회귀14.10초, 보행·착지·활성화handoff·ROS·교정77개108.70초, 지지 제약/몸체 이동·가속도11개27.62초 PASS다. 다음은 공개 ROS stopped 경계와 설치 감사 뒤 고정 소스의 새 실제 양 엔진 판별이다. 단위 통과를 물리 성공으로 세지 않는다.
- Public ROS FAULT-stop boundary after stance candidate: SHIFT timeout and known loaded-unload height bound2/2 PASS15.95s; explicit-stop/fresh measured lease required, no motor publications, reason/generation/FAULT retained, lifecycle deactivation verified. Source/tests/REUSE/helpers freeze before next actual engine series; no physical acceptance inferred.


## 2026-10-29: G2 하중 해제의 구조 판별과 제한된 지지발 어드미턴스

고정137소스219258b0...에서 GZ G1 `676f7637`은25/25 PASS지만 G2 `1a27f18c-e6c7-4d36-b7f4-99a245f79d0f`는 두 번째 RR 해제10mm에서4.797N이 남아 FAIL이다. 프리로드 참조 보존은 필요한 명령 연속성 수정이지만 물리 문제의 충분한 해결은 아니었다. 이전 실패bd67의 세 번째 FR18.213N과 구분한다. 이번 실패 뒤 명시적 STOP의 실측 정지·terminal 결과·runtime/engine 정상 종료·부모 회수·강제정리 없음·잔여[]는 모두 확인됐다. root2eb 서비스 원상복원과foreground 종료도 확인했다. 실패를 성공으로 재분류하지 않는다.

리서치: [SEIKO 논문](https://arxiv.org/abs/2312.16465), [저자 공개 코드](https://github.com/hucebot/seiko_controller_code/blob/main/inria_model/src/SEIKOController.cpp) (조회blob0a693326647acc76b79ace97ec8f8f42e7d8b5f6, BSD-2-Clause). 이 실험은 위치 제어 로봇의 유연성 모델로 접촉력을 간접 조절한다. Talos 실험은 우리 4족 모델의 성공 증거가 아니다. 외부 코드·QP·의존성은 복사하지 않는다. 아래 계산과 제한된 피드백은 Ch13 자체 설계이며 SEIKO 구현이라고 부르지 않는다.

원인 가설: 정적 지지 삼각형 안의 CoM은 세 발 지지의 가능 조건이다. 네 발이 모두 접촉하는 동안 힘·roll/pitch 모멘트를 만족하는 하중에는 한 차원의 자유도가 남는다. 순수 기하학 IK와 한 발만의 유계 들어 올리기는 이 자유도를 명시적으로 조절하지 않는다. 따라서 기하학적 안전 여유와 실제 무하중 판정은 같은 사실이 아니다.

판별 `contact-load-discriminator-1141accd-f0a1-4115-91f0-75b0528cc449`: 원본 report SHA1109c5f7..., source219258b0..., 실제 URDF kp=[200,500,750]와 현재 관절/몸체/접촉을 사용했다. 수직 Jacobian과 관절 강성으로 `c_i=J_zi K_i^-1 J_zi^T`를 산출한다. `H_i=[1,y_i,-x_i]`의 전치 영공간 n은 총 수직력과roll/pitch모멘트를 보존한다. `deltaF=-F_selected*n/n_selected`로 RR0N일 때 목표분배[73.798,10.461,0,65.006]N을 얻었다. 선택발 명령은 그대로 두고 지지발 참조만[-0.18497,+0.12442,0,-0.15109]mm 바꾼 선형 예측에서 RR1.327N이다. 이는 작은 변형·평면·준정적 가정의 계산이며, 비동시 센서·중력관절토크·마찰·감쇠·동역학 오차가 있어 엔진 성공으로 세지 않는다.

구현 결정: 명시적인 Gazebo G2 검증 프로필만 `stance_admittance`를 선택한다. MuJoCo/G1/기본 프로필은 geometric 그대로다. 기존 단일 CrawlMachine 소유자가 몸체 이동을 마치고 실제 삼각형 지지·정지 조건을 만족한 unload 중에만 보정한다. 선택발은 기존2mm/s·최대10mm·원래6초unload deadline으로 계속 관리한다. 나머지 세 발은 실제 힘 오차와 현 관절 Jacobian에 의한1초 시정수 보정을 받으며 각 참조 속도도2mm/s 이하다. 각 발의 reset 참조 대비 추가 보정은 누적±10mm로 제한한다. 이 추가 보정 한도는 선택발의 원래unload 상한을 대체하지 않는다. 한 접촉capture의 재사용으로 적분하지 않으며 이전 명령 적용을 기다리는 동안 보정하지 않는다. 무하중100ms·실제 lift·지지/슬립/관절/팔/몸체·단일 소유권·기존 시간/힘 기준은 모두 원래대로 판정한다.

측정 floor/anchor는 보정하지 않는다. 완성된 swing 경로를 중간 수정하지 않는다. FAULT·STOP·SWING·G1에서는 새 피드백이 없다. 접촉값/모터강성/엔진상태를 조작하지 않으며 게인·30Nm·2ms물리·100Hz CM·50Hz제어도 유지한다. 부족하면 원래 상한/시간에서 실패해야 한다. 보정 수학·실행 소유권·설정 범위의 RED→GREEN 후 설치 감사와 실제 GZ G1/G2를 한 쌍 먼저 판별한다. 실패 시 다음 반복은 자동 시작하지 않는다.


### Stance load candidate focused verification
RED missing contact-transfer model12.93s; math8PASS16.04s. RED missing serial owner15.57s; math+owner+actual ROS configuration18PASS27.06s. Existing relevant gait/landing/preload/fault STOP/ROS/G1/mass/scope/cadence88PASS130.15s. One mistyped test path produced0 tests and is retained as harness error, not product failure. Decision before engine freeze: predeclare3 identical Gazebo G1/G2 pairs, treating first pair as the discriminator and stopping at first FAIL. This avoids rerunning an already accepted first pair; no retry after failure. Installation audit and original-clock checks precede every actual engine series. Source138 includes new own-written contact_transfer.py; no acceptance yet.


### 2026-10-29 actual source138/223e5d49 discriminator
GZ G1 7c1a1f92=25/25 PASS, normal runtime/engine/noForce/reaped/residual[]. G2 ae04a225-410f-4f76-8c49-f4992703422e=FAIL at ROS41.704 forward: guard_state:scan:wall_age, no first CrawlMachine FAULT. First FL swing/landing sequence completed; second RR unload started. This does NOT establish full physical load-transfer success. G2 archive1936317B SHA5e892ead3aaf9ba240775653784e40716e1cac3a704ed930d7f303394977a7b3. Root562010f8 restoredtrue/restoration_pendingfalse/foreground_sessions_closedtrue; no next pair after failure.
Independent full observer scan41.6 receipt965635281033 -> scan41.7 receipt965993379626:358098593ns WALL for100000000ns SIM. Guard independently held scan41.6 until its300ms lease expired; this is not inferred from an absent trace. The engine and capture progress slowed; body capture arrivals also show the slowdown. Neither stale-target reuse nor a longer lease is acceptable. Process metrics show GZ59threads/~1.75cores, crawl17/~0.77cores, guard18/~0.55cores over the sampled4sec window; previous candidate had similar totals. This does not locate a unique CPU bottleneck and does not justify blaming llvmpipe alone.
Budget decision: existing10Hz SIM acquisition cannot satisfy300ms WALL at observed0.279RTF. New Ch13 Gazebo navigation scenes will acquire actual360-ray scans at20Hz SIM, leaving nominal179ms acquisition plus121ms delivery allowance at that measured slowdown. This is a producer-schedule change with new capture headers, not header rewriting or a timeout relaxation. Existing raw Xacro/legacy models and MuJoCo stay unchanged; RGB-D320x240/15Hz and all300/200ms safety leases, physics2ms, gains/force caps remain unchanged. Native scene hash changes, so create a freshscene/G1 proof and invalidate old proof reuse. Test real converted SDF schedule and camera/legacy invariants before actual comparison; actual timing and added cost must still pass.


### 2026-10-29 scan 촬영 시간 예산 검증
scan-age-discriminator-4ec06822-b54a-4b0a-8fc9-f21b09fda2ca에 종료된ae04 원본의 촬영/수신 행과 SHA·재현 방법을 저장했다. 독립 관측의 최장100ms SIM 구간은358.099ms WALL, 비율0.279253이다. 첫 crawl STOP에서 scan wall age338.157ms이며 가드의 최초 정지는 그보다 앞선 시점이다. 가드의 정확한 callback 수신 간격을 독립 관측과 동일하다고 주장하지 않는다.
실제 변환 SDF의20Hz 촬영 스케줄 RED20.63초를 확인한 뒤 scene.py의Gazebo navigation 장면 생성만 수정했다. 원본 Xacro10Hz/legacy opt-out·MuJoCo·360ray·마스크·카메라320x240/15Hz·변경 없는 모터/힘/명령 인터페이스·장면 해시/실제 파일 일치·하중 소유권35개 회귀39.57초 PASS다. 앞선138파일223e 소스의18+88회귀는 보존하고 변경 없는 보행 전체를 반복하지 않았다. 새실제 실행은 새장면/G1부터 시작하며 고정본3쌍을 첫 실패에서 중단한다. 실제 인수 성공은 아직 아니다.


## 2026-10-29: 보정 수명의 재검토 — 실제118초 실패와 임시 참조 복귀
새20Hz 장면의 고정138소스 a509df68...에서 GZ G1 6bb9ed4b=25/25 PASS(원격게시용ZIP1880388B SHA04de1211...), G2 7adc9a39-ed88-487b-b905-dc339bfee976는 ROS118.088초 FR 해제10mm에서2.087850867N이 남아 FAIL했다. firstfault에 마지막 하중 보정·현재stance 참조가 기록됐다. 해제 시작112.106초, 마지막 관측117.964초의FR2.290946N에서118.088초2.087851N으로 감소 중이었지만 기존2N 기준을 만족하지 못했다. 원래 높이/시간을 늘리거나2N을 완화하지 않는다. 이 실행은 G2 전체성공이 아니다. 실제 정지·액션terminal·runtime/engine 정상 종료/noForce/부모회수/잔여[] 확인, rootf258 서비스restoredtrue/pendingfalse/foregroundACK 확인했다. G2 ZIP1679732B SHA6a2c9f050f5451dae944f00dd558429eb126e3774e5c92303f09c753a016cf51.
충분 원인 판별은 계속 필요하다. 다만 코드 수명 결함은 직접 재현됐다: 임시 어드미턴스가 _stance_reference_z를 덮어써 다음 swing의 기본 프리로드로 계속 누적됐다(RED12.18초). 실제 실패 참조도 FR.013399/FL.014417/RR.011383/RL.013600m였다. 평면 대칭4접촉 근사에서는 선택발의 위쪽 해제는 swing 착지 때 되돌아오지만, 나머지 세 발의 보정만 남으면 한 주기 뒤 네 발 모두에 공통 하향 편향이 남을 수 있다. 이것이 이번 물리 실패의 충분 원인이라고 단정하지 않는다.
변경 결정: 1초 어드미턴스 시정수와 힘/높이/속도/원래6초해제deadline은 그대로 둔다. 각 해제 때 보정 전 지지발 참조를 별도로 저장하고 _stance_reference_z는 수정하지 않는다. 실제 착지 뒤 SETTLE에서 세 발의 임시 오프셋만2mm/s 이내로 정확히 복귀한다. 발의xy·측정floor/anchor·완성 swing 종점은 수정하지 않는다. 네 발의 실제 하중·신선도·지지·관절·slip·몸체/팔 기준은 계속 검사한다. 복귀 완료와 실제 몸체 정지 전에는 다음 SHIFT를 시작하지 않는다. 기존SETTLE의.25초는 최소시간이었고 새복귀는 임시 오프셋10mm/2mm/s+.25=최대5.25초로 유계 처리한다. 이를 넘으면 별도FAULT, 자동복구 없이 원래 안전정지 소유권으로 처리한다. 기존 전체 실행 시간 상한과 향후Nav2의240초 기준은 그대로다. 이 추가 복귀시간의 처리량 영향도 실제 결과로 평가해야 한다.
명시적으로 허용된 velocity pause 뒤에는 남은 임시 오프셋을 복귀한 후 중단했던 같은 발을 계획한다. STOP/FAULT 중에는 복귀 모터 명령을 새로 내지 않는다. 이 수정은 Gazebo G2에만 적용되며 G1/MuJoCo/일반모드에는 없다. 단순히 강한 피드백 게인으로 바꾸는 실험과 섞지 않는다.


## 2026-10-29: 고정 발을 포함한 네 접촉의 결합 역산
중단 전 root18c5fa08의 실행은 완료됐다: G1 01b714c5=25/25 PASS, G2 afa0c4d9-0a46-4393-a123-4b1dbc2a4545=ROS133.658초 RL 해제 상한10mm에서2.103419209N이 남아 FAIL. 소스138 manifest8eb0aa70..., G2 ZIP1707443B SHAb79936b95b0b4dd399104bb86266de2215d4f5cf9c8c513a94de048e16b025b7. 원래 neutral참조는 FR/FL.0167051576, RR/RL.0177270467로 보존됐다. 따라서 임시 보정의 수명 수정은 참조 계약을 고쳤지만 물리 해제 실패의 충분 해결은 아니었다. measuredSTOP·carryterminal·deactivate·consumers/clockstop 모두true, runtime/engine 정상/noForce/reaped/residual[], 서비스복원/foregroundACK도true. 앞선 읽기전용모니터 명령은 자동검토 사용량 한도로 실행되지 않았으며, 새 사용자 재개 뒤 기존 세션 결과를 회수했다. 승인 검토를 우회하지 않았다.

새 판별은 임의의 시정수 튜닝이 아니다. 수직 컴플라이언스 C=diag(c_i), H_i=[1,y_i,-x_i], H.T*n=0일 때 자유 몸통을 포함한 힘 반응은 P=n*n.T/(n.T*C*n), deltaF=-P*deltaZ이다. 독립 스프링의 deltaZ=-C*deltaF_desired에서 선택발 참조만0으로 고정하면 실제 선형 반응은 mu=(sum_{i!=selected}c_i*n_i^2)/(sum_i c_i*n_i^2)만 남는다. 기존 코드는 이mu를 빠뜨렸다. 독립행렬 평형 회귀에서 -0.096N을 요청했으나 -0.071059N만 나와 RED15.62초였다.

실제 실패의 고정URDF·현q/몸체/접촉으로 재계산한 contact-load-discriminator-18adc0c9-2803-4b4c-ac19-d0ce58a293ad는 mu=.730140274, 역수1.369599837을 얻었다(report SHAb2810f15...). RL2.103419N을0으로 하는 평형분배는 [11.054776,75.278806,62.855875,0]N이고, 원래 지지발만 조정한 선형 잔류 예측은.567628N이었다. 조정량을mu로 나눈 독립 평형 예측은 RL≈0이다. 이는 비동시 센서와 평면/작은변형/준정적 가정의 모델 판별이며, 마찰·중력관절토크·감쇠·동역학을 모두 검증한 물리 결과가 아니다.

구현은 현q/회전/실측접촉점에서 네 발의c_i와mu를 산출하고 세 지지발 보정을mu로 나눈 뒤 기존2mm/s 상한을 최종 적용한다. 고정한 선택발의 원래2mm/s·10mm·6초·2N/100ms 조건, 단계별 임시보정/착지후복귀, 게인/30Nm/2ms/100HzCM/50Hz제어, 카메라와모든안전기준은 유지한다. 실제 적용된mu·역수·컴플라이언스·속도제한배율과 선형예측(실측힘과구분)을 진단에 남긴다. 모델/소유권/복귀/안전정지35개44.07초 PASS; 네발선택/큰입력속도상한 추가 검증 뒤 설치감사와 새 실제 고정본3쌍을 첫실패중단으로 실행한다.


## 2026-10-29: 최종 해제 확인 동안 제어권이 끊기는 이산 상태 결함
결합역산 고정본ad56ec17...에서GZ G1 056a1c76=25/25 PASS, G2 b9c835b2-0b3d-4365-a56e-3dc7a9a65ce7는ROS104.126초 RR의원래6초해제deadline에서FAIL했다. 마지막하중2.057016N, 선택발참조상승8.975mm로높이여유는남아있었다. 마지막선형모델mu.728731/역수1.372249/속도제한배율1.0,18ms당예측하중감소-.037026N을기록했다. 이것만으로물리성공을주장하지않는다. ZIP2202589B SHAa7d55285792367ed649d1d8a0db6476beeb5e11d073d0f284c77f82acf94c17f. measuredSTOP·terminal·runtime/engine정상·noForce·reaped·잔여[] 확인, rootf0b28f11복원/foregroundACK확인.

추가측정 unload-threshold-discriminator-fd72c7bf-a4e3-43c7-9789-612f7d1b0625는닫힌원본의해제구간에서298고유접촉을선택했다. RR최소1.862998N,최대28.864625N,2N교차36회,연속기준미만최장80ms였다. 독립관측은정확한controller선택cache와같다고가정하지않지만,코드의prematurestop을판별할근거가됐다. 고정수치시험에서1.9N첫관측후100ms확인전선택발참조가정확히멈추는문제를재현했다(RED13.05초). 첫호출은시험파일경로오기로나오기전0건실행됐고하네스오류로그를보존했다.

원인은2N이라는지지판정문턱을제어소유권종료로재사용한것이다. 첫2N미만관측때선택발해제적분·지지발힘조절을모두멈췄는데,실제해제는100ms유지후에야확정된다. 순응성있는계에서문턱주변으로재반등하면확인시간이반복초기화된다. 모델역산만고쳐도이상태논리가남으면해제가끝나지않는다.

최소수정은명시적인GZ G2의stance_admittance모드만100ms확정완료까지기존제어를유지하는것이다. 힘이2N미만이라도확정전SHIFT동안은원래세발실측지지·몸체정지·신선도조건을만족할때기존2mm/s해제와실측힘조절을계속한다. 실제0N은힘보정0이며,SWING/STOP/FAULT에서는이피드백을종료한다. 원래2N판정/100ms유지·10mm상한·6초deadline은유지하고다시시작하거나오래된목표를재사용하지않는다. 일반geometric·MuJoCo/G1동작은유지한다.

관련보행·수학·복귀·안전정지75개70.95초PASS.추가로확인시간100ms보다이른handoff가없는지와일반모드원래동작/G1ROSscope를검증중이다. 계산·단위통과는실제인수성공이아니다.


## 2026-10-29: 높이 상한과 해제 완료 deadline의 분리
100ms확인제어 고정138소스18ad2630...의G1 3265d2ed=25/25PASS, G2 c6ee257f-512c-487b-9a1f-1f2be2ac05e1=ROS131.786초RL10mm상한에서FAIL이다. 이번최소하중2.100403N/283고유접촉/2N교차0회로,앞선b9의36교차/최장80ms와다르다(unload-threshold-discriminator-3d92d60c-4788-4c93-831e-cf18390a838e). 확인제어수정만으로충분하지않았다. 실제STOP·terminal·runtime/engine정상/noForce/reaped/잔여[], root1f3d서비스복원/foregroundACK확인. ZIP1701070B SHA34b66ccca02d878315b914245e948e4e429faf081f462101927b264d4616ea57.

원래해제시작126.030초,상한실패131.786초로6초deadline까지244ms가남아있었다. 높이상한도달은추가상승금지조건인데,제어가그즉시종료되면이미허용된시간내힘조절/100ms확인을완료할수없다. 최소회귀는높이10mm·경과5.75초에서FAULT가발생함을재현했다(RED15.07초). 수정은명시적GZ G2모드만선택발높이를동일10mm에유지하고남은원래deadline동안세지지발피드백을계속한다. 상한초과는여전히즉시실패,6초초과도원래실패이며일반geometric/MuJoCo/G1의기존동작은유지한다. 상한·시간을늘리거나힘판정을낮추지않는다. 기한후실패·확인시간·보행·복귀·정지·G1scope81개83.90초PASS다.

새물리실험전기존원본으로추가경계를확인했다. native-boundary-discriminator-c3c7ba73-3a08-4fae-8f15-51e3aebe302f는131.784초원본패킷을보존했다. ROS명령은controller관절순서와네이티브source_input에대응하며20ms적용참조가지연을보존했다. 네발의URDFFK와네이티브센터차이는1.95~5.92µm(근접시각비교)이므로대규모좌표/매핑오류근거는없다. FLcalf의force_command는-30Nm상한이다. 이는의도한입력이며실제일반화힘측정은null이다. static-wrench-discriminator-933b62bb-1ca1-4011-8150-9549630b64ab의-66.84Nm는미제한Kp오차역산이므로실제모터토크나583N실측힘으로해석하면안된다. 포화때선형강성모델이적용범위를벗어날가능성은남아있다.

full-contact-discriminator-d018b994-f5bf-4920-b465-7c89505b0d83는새실험대신기존120.174초접촉전환원본을추출했다. 그시점FL힘은[2.191,-2.304,70.880]N,RR[3.931,-.263,59.202]N이며최종실패시점과다르다. 따라서최종실패의수평힘이과도하다고단정하지않는다. postphysics force_command0은명령소비뒤상태이며적용토크0이라는증거가아니다.

실제설치버전gz_ros2_control1.2.20/controller_manager·hardware_interface4.48.1을확인했다. 해당공식태그의gz플러그인은PreUpdate마다CMwrite,PostUpdate100Hz에서read/update를호출한다(소스blob04a674cda4c776054748dbc8427dbf594524836a). RM기본rw_rate경로는write를직접호출한다(blobd720785039cb9c7136fab01112f653a0c495ce27). 소스확인만으로설치바이너리의모든실행을증명한것은아니지만,단순100Hz/500Hz비율만으로1/5토크적용이라고단정할근거는없다. 외부원본·설치파일·설정은수정하지않았다. 현재물리비교변수는상한에서남은시간을보존하는N커널수정뿐이다.

## 2026-10-29 — 재개 4342c86d 실패의 판별과 검사 수정

- 이전 세션78198/root75d37780의 종료를 실제 세션 출력과 session.json으로 복원했다. restored=true, restoration_pending=false, foreground_sessions_closed=true. 다음 엔진을 임의로 중복 시작하지 않았다.
- Gazebo G1 d14e51f0 PASS. 동일138소스 manifest cc9f67c5783cf6fbdf08ac6f126a861e32fbf4801389f48aa1b90d73dae7be1a의 G2 4342c86d FAIL. source archive e4a3907e10e5a3b50e7fb1447458689a2b66d2b280d70ffb2b7c35d072c9c125/1949354B. 원본 보존. arm4 원본39.980초 0.025548rad/s >0.02; 선택 시각39.984초. carry terminal 수신/정상 engine-runtime 종료/reap/no-force/residual[]은 참, 실측 STOPPED는 미확정.
- carry-boundary-discriminator-3398c3ae-906b-4fbe-ad16-a6382dc41376: 전후2초 원본 대조. 서로 다른 시각의 네이티브39982ms 속도0.005544를39980ms의 ROS 표본 대체로 사용하지 않는다. 명령 최대 단일관절 변화0.001857rad/20ms, 몸체 실제 최대속도0.055990m/s. 이 숫자만으로 팔 과속의 원인을 단정하지 않는다. mission_probe에는 joints 항목이 없어 해당 분석의 unique_arm_captures=0이며 callback 부재의 증거가 아니다.
- 별도 확정 결함: DART 설정 인수 함수가 모든 시나리오에 stand/calibrate를 요구했다. G2에는 calibrate가 존재하지 않는다. G1은 기존 두 단계, cycle은 stand/forward/left/right/stopped, reverse는 stand/reverse/stopped 각 단계의 원본50µm 증명을 모두 요구한다. 각 필수 단계의 누락·설정 변조는 실패를 유지한다. task8-g2-dart-witness-red=1FAIL/14PASS(12.71초) → green=31PASS(31.61초). 원래 required_checks 삭제/하향 없음. 이 수정은 운동 실패를 해결했다는 뜻이 아니다.
- 다음 판별: 평면 수직 강성 근사는 수평 힘과 모터 포화의 영향을 생략한다. 기존2ms contact 요약에 정확한 충돌 ID 쪽의 signed3D 힘 합계만 추가한다. 모터/게인/접촉 설정/접촉 판정/시간 기준은 그대로이며 full-contact payload를 매번 저장하지 않는다. 모호한 충돌 ID는 valid=false/null로 표시하고 임의 부호를 정하지 않는다. CPP RED는 새 필드 부재의 실제 실패(6개 중1FAIL,0.14초). 실제 비교 전 GREEN·설치본 감사가 필요하다.

- 접촉 벡터 회귀: task8-native-contact-vector-green은 빌드 성공 후 기존 overlay의 설치 라이브러리를 읽어 동일 실패했다. 이를 제품 수정 실패로 숨기지 않았다. pre-install 시험의 LD_LIBRARY_PATH를 정확한 build 경로로 지정하고 ldd 기록을 보존한 green-linked는6/6 PASS(CTest0.11초)다. 이후 실제 colcon 설치 S5.43초+N12.0초(총18.3초), 8패키지 source/install 감사 PASS. 전 관측 패키지 시험은 task8-contact-vector-sensors에서 진행한다.

- task8-contact-vector-sensors: 62 tests, 0 errors/0 failures/0 skipped(15.0초), 8패키지 설치본 일치 감사 PASS. G2 시나리오 검사31PASS와 합산해 고유 시험 수라고 주장하지 않는다. 다음 비교는 single-pair-diagnostic, 제어·물리·안전 변경 없이 기존 높이 HOLD 후보/새 접촉력 진단만 실행하며 한 번이라도 실패하면 중단한다. 실제 엔진 시작 뒤 소스·시험·REUSE·helper를 동결한다.

## 2026-10-29 — 15382b7e 실제 실패와 계획 구조 판별

최신G1 0f48f304=25/25PASS, G2 15382b7e는RL 하중 해제127.352→133.354초(원래6초기한)에서FAIL했다. 마지막선택ROS하중1.981N은2N미만이지만100ms확인을마치지못했다. 상한HOLD만으로충분하다는가설은기각한다. engine/runtime정상종료·실제carryterminal·reap·noForce·residual[]은확인했으나 measuredSTOPPED는실패했다. e363root서비스복원/foreground종료true,원본과실패를보존했다. G2 ZIP1706170B/SHA b24811f9ff30de9c43efecac4bd7408324f48e36f83c05b5c03323e4f08240af. 이번시리즈를성공횟수에넣지않는다.

spatial-contact-discriminator-899b3200-ee49-491f-be21-4a1f4c3ab31d는원본JSONL을한번순차읽어6초구간301개20ms요약만추출했다. RL마지막힘[-8.316,2.055,1.975]N, FL[9.879,-3.645,72.999]N이며FLcalf명령-30Nm포화다. 진단합계는정규화접촉판정이나실제모터일반화힘이아니다. 공식gz-sim Physics.cc의Contact ExtraData와세계축부호정의를재확인했다. 근접원본postphysics관절참조의write_capture가133.322/324/326/328초로2ms마다증가하는구간을확인했다. 단순100/500비율로1/5토크를주장하지않는다.

support-load-feasibility-5c1b9ab7-b66f-440c-87be-71af134bc95d의오프라인판별은현재CoM의세지지발수직하중비중최대50.4%를기존IK/관절/발점유/허벅지충돌제약안에서39.9%까지낮출위치가존재함을보였다. 모델이접선힘·포화·동역학을생략함을명시하고실제성공으로세지않는다. 분석초기tuple뺄셈오류는분석스크립트의오류로수정했으며제품RED로세지않는다.

수정설계: 명시적GazeboG2 stance_admittance에서만기존최소안전후보부터centroid방향의9개유계후보를비교한다. 세발준정적 평형 [x;y;1]f=[CoM_x;CoM_y;1]의최대비중을최소화한다. 모든기존margin/IK/발점유/충돌제약을적용하고 개선후보의중간3점·미래착지점도검사한다. 경로거부시기존검증후보를유지한다. 한yield당전체모델계산1회로기존안전callback을막지않는다. 같은방향에검증후보가없어기존constraint projection을쓴경우에는그원래경로를유지한다. 이는WBC/SEIKO구현도,포화의실제해결보장도아니다. 물리/게인/30Nm/해제2mmps10mm6초2N100ms/G1 10초는유지한다.

실제실패기하를고정한회귀는초기fixture시각오류(18.63초)를바로고친뒤 최대49.85%vs43% 조건의제품RED(17.88초)를확인했다. 첫GREEN시도는단위plant의예전원점에미래발을놓아새경로가정당하게거부됐다(28.28초). 원래오프라인시험의정지재계획의도대로미래착지XY를현재발위치로고정했다; 기록에없는실제travel상태를가공해채우지않았다. 이후새계획/기존G1/기본모드/계획분할/실제on_configure scope17개36.62초PASS. 추가무효후보RED16.68초,세대초기화RED및전체관련회귀를진행한다. 실제새모델인수는아직미실행이다.

- 하중 분배 계획의 무효후보RED=1FAIL/3PASS16.68초와 세대초기화RED=1FAIL16.90초를 확인했다. 모든예측무효시기존후보를조용히승인하지않고FAULT경로로오류를반환하며, 수동reset은이전세대계획기록을지운다. 최종관련회귀 task8-support-load-balance-regression=85PASS116.01초(모델분할/G1·기본모드/ROSscope/해제/복귀/정지/가속도 포함). 하중 계획이실제물리를해결했다는뜻은아니다. 다음은N설치/8패키지감사후 새고유single-pair Gazebo실험이다; 다른제어·물리기준을함께바꾸지않는다.

## 2026-10-29 — b82af967: 점 자세와 후속 발 참조 영역의 차이

고정138소스 d7fd39fffead4f2d8316522e009a8afe0c27e9396d227c6cb4267092d634d870에서G1 5fcfafb3 25/25PASS. G2 b82af967은51.014초 FR해제시작후94ms에 thigh/trunk clearance 참조검사FAIL. actual unexpected contact를실측했다는뜻은아니다. 원래100µm검사가새명령을차단했다. load_balance_plan=null은centroid방향후보대신기존constrained projection을사용했다는실제기록이다. 하중목표최적화결과라고오인하지않는다. G2ZIP2023881B/SHA5dfdd0792ee8cef9845c5be80d932c2a71fe11b0808cc9ab69271e1cc9fc0ac8. 정상engine/runtime/reap/noForce/residual[] 및rootfcd3의서비스복원/foreground종료true; measuredSTOPPED는FALSE.

reference-clearance-discriminator-d8d0ba2b-048c-4ab3-b4f7-652fac2b0840에서실제실패참조RL clearance=99.921µm로원래100µm를넘지못했다. RL지지발을원참조보다약68µm올린구간이다. +10mm허용높이보정에서는clearance가음수이며, 다른발의반대방향보정은calf범위에도영향을준다. 기존계획은평형몸체의nominal/착지점만검사해이후admittance/해제/swing높이영역을포함하지않았다. 기한·여유를늘리는방법은쓰지않는다.

다음설계는명시적GZG2계획의같은후보검사와constrained fallback 모두에원래허용참조영역을포함한다. 평면네접촉영공간의부호로세지지발보정의단방향범위(원래10mmcap)를정하고, 선택발은원래해제·swing최고높이·착지탐색하한을포함한다. 선택발XY의기존시작→착지선분과높이극값/중간값을검사한다. 개별발의최소clearance/관절여유를집계해기존최대64개2D제약차원은유지하고전체mass계산은후보당1회로유지한다. 몸체이동중에는원래nominal발경로,이동완료자세에는후속발참조영역을적용한다. G1/MuJoCo/default geometric,형상·질량·게인·힘·속도·기한·충돌기준은그대로다. 유한표본검사는물리성공이나수학적연속구간증명의대체물이아니다. 기존계획이허용범위전체를수용하지못함을원본last-safe command FK의작은fixture에서RED로먼저재현한다.

- 참조 범위 회귀 task8-reference-envelope-red=1FAIL14.82초: 기존 계획이 허용한 RR의 하강 참조에서 calf0.77237rad<0.8을 확인했다. fixture는 실제 마지막 안전 관절 명령을 FK했으며, 기록되지 않은 운동을 재현했다고 주장하지 않는다. 새 reference_envelope.py는 유한한 참조 격자의 최소 여유를 기존2D제약에 집계한다. G1/default 범위와 기존 하중분배43% 조건을 포함한10개 시험18.70초PASS. 물리 성공이나 연속 공간의 엄밀한 증명으로 세지 않는다. 관련86개 회귀는 task8-reference-envelope-regression에서 실행 중이다.

- task8-reference-envelope-regression=86PASS111.37초. 새모듈/기존G1·geometric·50Hz·하중분배·해제/복귀·정지·ROSscope를포함한다. 코드연산은nominalmass후보당1회이며, 참조격자추가IK의실제callback비용은다음native실행계측으로확인한다. git diff --check에서는기존S/REUSE_MANIFEST.md:195의EOF빈줄1건이남아있어전체diff검사통과라고쓰지않는다. 런타임무관문서형식은최종정리시다룬다. 실제후속참조영역수정효과는미검증이며다음고유singlepair에서확인한다.

## 2026-10-29 — 사용자 중단 뒤 f228 별도 복구

기존 exec92410 연결은 사라졌고 f228 원본session은 validation_exit=-2, restored=false, foreground close=false로 남았다. 이를 정상 종료로 고치지 않았다. 원래ea5bfb20 부팅과 다른2014a61b 부팅이 관측됐고 남은소유runtime은없었다. recovery-f228-7e494830-73db-41f1-bbd7-082f34499664는새일반권한foreground에서22.04/24.04 두서비스 active/enabled가원래기준과일치함을확인하고두확인세션의정상closeACK/회수/잔여없음을검증했다. replacement_baseline_confirmed=true, 원본메타데이터SHA불변, 설정변경0이다. 원래lease의복원이성공했다는뜻이아니다. 최신참조영역코드는86PASS이후수정하지않았으며actual후보시험완료로세지않는다. branchfeat/ch13-section-13-5/HEAD4e87f6f6031d0ac5e73b2575bcee261e92a0e59e를다시확인했다. 기존작업트리를유지하고새고유시험으로재개한다.

## 2026-10-29 — b8360ed1 실제 실패와 구조 검토

고정139소스 manifest c41684c67f0fe5d430cee3a304aa5a928173ce2cf2641b4f71fb65e118af7d5b의 G1 e75bb1cf-4425-4d2e-afef-32d155fb00c0는25/25 PASS. G2 b8360ed1-0caf-4a98-91bb-c80eda79f1ac는ROS59.532초 FR 하중 해제 timeout으로 FAIL했다(시작53.522초, 선택발2.160507N, FL80.809166N). load_balance_plan=null을 코드 경로와 대조하면 하중 목적이 없는 constrained fallback 사용이다. engine_exit=true/실제 engine returncode0/액션 terminal/회수/noForce/residual[]이며 measured_stop=false로 전체 정상 종료 인수는FAIL이다. 이를 새로운 엔진 hang으로 보고하지 않는다. G1 ZIP1901396B SHA e4b005ece7f720a30df9dac9823ee9d4c78592b91366cbbc0c724462a3a19a8c, G2 ZIP2060643B SHA de767e862c9a036ed9f3d24f7e4ec06f085bb1134bb424552f91523da1f94772. root74f8cd84-315a-44ce-aac3-3ed5d8b0293c는restored=true/pending=false/foreground_sessions_closed=true, validation_exit=1을보존한다.

사용자 구조 검토 요청 뒤 새 엔진·런타임 수정 없이 종료된G2 8건을분류했다: 하중전환6/carry1/참조기하1. architecture-review-5e477e12-0cd1-4ecf-b6f0-85aa0a75bdc1/{method.py,result.json}은입력/소스SHA와실제커널고장전이반례·명령시간산술을보존한다. result SHA256 bd6b5ce0a4a26468245c075124cbd78fa3dba4d43070e5a993944506651b7951. _fail의두번째오류가착지대상을지우는코드반례는확인했으나실제최신실행의후속오류발생증거로대체하지않는다. 소스테스트의수직스프링근사와실제포화/공간접촉응답사이의검증공백, 대체계획목적누락, 시간여유부족을SECTION_13_5_ROOT_CAUSE_REVIEW_KO.md에정리했다. 다음은공통실행가능성·힘모델유효범위·고장복구·시간예산의부분재설계와작은실제접촉전환부품검증이다. 원래인수기준은유지하며Task8전체성공·양엔진고정3회·후진·Nav2·최종회귀·게시미완료다.

## 2026-10-30 — 부분 재설계의 실제 네 차례 판별

모두 service-only/compensated-tick-read-only 단일 Gazebo G1→C1이며 tick 쓰기는0이다. 서로 다른 소스이므로 고정본 연속 성공으로 합산하지 않는다. 원본 G2 결과는 C1이 생략한 거리/회전까지 포함해 FAIL로 남는다. C1은 별도 부품 진단이다.

| root UUID | 실제 G1 | 실제 C1 | 결과/판별 |
|---|---|---|---|
| c8261d16-fc9d-4842-9537-5d78ba73709f | 7e966373-c6cf-46f8-9e54-5180317420bd,25/25 PASS | 26a3a7d1-3f95-4ff3-ad46-dc235a6a0822 | 첫10ms 계산 FAIL. signed 벡터는 유효, lift 없음. |
| 29ba2fc2-4434-4856-ab5b-ac7c124bcd03 | 945fe319-f629-407f-9d2b-9550e365663f,25/25 PASS | ccf0b474-3a49-490f-b467-a43e4eed5f16 | 해석 Jacobian/중력으로도 첫 호출 FAIL. |
| c94bfd7d-73b4-4448-ad01-ba20d461264e | 56acce2d-083c-4014-b4da-037bcb22133c,25/25 PASS | b09405c9-8ebb-4a34-91e9-0a76d273eed8 | 준비1.52ms 성공 후 공간 CPU7.34ms, 전체15.39ms FAIL. |
| 84e52d32-d58a-43d8-82c3-f03f9c0b838d | 027edf99-68f1-452c-9434-578b6f8602d7,25/25 PASS | ce729fb3-cbf0-4648-9036-dd44cbc3693a | native 공간 계산 뒤 CPU4.50ms/경과13.21ms FAIL. |

네 root는 복원완료/복원대기false/foreground종료/잔여없음으로 종료했다. 실측 STOP·비활성화·실제 팔 terminal·소비자/시계 종료는 확인했지만 하중 전환 성공은 아니다. 각 root/session·원본 보고서·manifest를 보존한다. 마지막 manifest143 SHA8ae599bf7e51e2f8cdf5cce22147ecacfc7257525490293de258ce6117521ea4다. 수치 비용 축소와 실제 경과 마감은 다른 문제다.

수치 자식/원본 문맥 파이프라인·명시적 ACK/reap·종료 순서를 구현한 뒤 `task8-load-process-related-regression.log`는257PASS204.66초였다. 추가 spawn 실패 소켓 누수/실제 수신 wall age 회귀의 RED 뒤 `task8-load-process-boundaries-green.log`34PASS22.51초다. 당시 설치본 이후 새 수정은 다시 빌드/감사한다.

## 2026-10-30 — 재개 후 비동기 경계와 XYZ 설계

- 취소된 실패 은폐를 `task8-async-cancel-failure-red.log`(17.89초)로 재현했다. `task8-async-cancel-snapshot-red.log`는11FAIL24.31초이며 속도0 취소 누락·동일 capture 재제출·전송 원본 보존·계산 인수 누락을 포함한다. 수정 후 `task8-async-cancel-snapshot-green.log`46PASS31.80초다. 취소된 solver 실패는 poll/close 양쪽에 실패로 남고 정상 종료와 별개로 `numeric_worker_job_contract`를 검사한다.
- 다섯 번째 엔진을 시작하기 전에 저장 입력의 도달 가능성을 분석했다. `task8-load-force-reachability-01/02.json`과 정확한 `.method.py`를 보존한다. 높이rank1/최소Fn1.872178N, 선택발XY 고정·지지발XYZ rank6/완화해Fn0. 모터/변화율을 생략한 완화로 물리 성공이나 높이 정책의 절대 불가능성을 뜻하지 않는다.
- XYZ 미구현 RED19.77초 후 첫 곡면 벡터 제약/선형 L1 제약이 각각 iteration32에 실패했다(`task8-stance-xyz-green-01/02.log`). 수치 진단 `task8-xyz-solver-conditioning-01.json`의 Hessian 고유값은 약2e-10~6.724로 조건수가약3.4e10이다. 단순 상대 정규화만으로 변위 경계 반복 실패가 남았다(green-03.log). Cholesky 변수 변환으로 같은 엄격 볼록 목적함수를 단위 Hessian 좌표에서 풀고 원래 primal 제약/잔차를 재검사한다. 반복32/계산10ms는 유지한다.
- `task8-stance-xyz-green-04.log`의 새 XYZ8개는 통과했지만 기존 높이 실제 입력 재생1개가10ms를 넘어 전체는FAIL(14PASS/1FAIL24.19초)이다. 이 실패를 지우거나 새 XYZ 성공과 합산하지 않는다. 관련 최종 회귀에서 다시 확인한다.
- 부모 XYZ 미연결 RED20.38초 뒤 `task8-async-xyz-owner-green.log`21PASS20.51초다. 실제 process mode 미구현 RED16.17초 뒤 첫 설치 시험은 JSON 목록 산술 오류로FAIL16.09초였고 reference_envelope 입력 정규화를 수정했다. native N install은12.3초/여덟 패키지 감사 통과(`task8-stance-xyz-json-install-*`). 실제 자식 및 관련 회귀는 새 설치본으로 실행 중이다.

아직 새 XYZ 실제 엔진 성공·Task8 고정3회·후진·Nav2·최종 게시 완료가 아니다. 현재 HEAD4e87f6f6031d0ac5e73b2575bcee261e92a0e59e와 기존 사용자 변경을 보존한다.

최종 `task8-stance-xyz-related-regression.log`는37파일287PASS222.99초다. 중간 높이 재생 실패를 보존하며 새 소스 변경 없이 이 관련 회귀에서 다시 확인했다. `task8-stance-xyz-old-input-replay-01.json`은24회 실패0/3.874967~6.264262ms이며 원본 힘·q를 변환하고 기록되지 않은 미래swing XY는 고정한 **수치 비교**다. 방법·정확한 변환 입력·소스/라이브러리 SHA를 같은 기록에 남겼다. 물리 증명이 아니다. 소스/설치 감사8패키지 통과 뒤 다음 고유 service-only/tick-read-only G1→C1에서 실측한다.

root `3f787837-c96e-48c4-8921-575ef8a2d053`는 수렴/교차/150초 원본 시계 검사 뒤 **엔진 시작 전 설치 감사에서 차단**됐다. sensors/REUSE_MANIFEST의 마지막 EOF 공백 정리를 설치 감사 뒤 수행해 설치본과 달라진 것이 원인이다(`task8-gazebo-applied-elapsed-clock-stable-clock-single-owner-3f787837-...-install-audit.stderr`). 시험 기준을 완화하지 않고 정상 패키지 재설치/여덟 패키지 감사를 수행한다. 이 root의 engine_attempts=0이며 5차 C1 실패/성공으로 세지 않는다. validation_exit1/restoredtrue/restoration_pendingfalse/foreground_sessions_closedtrue/final_related_runtimes[]를 확인했다. 기존287회귀 이후 런타임 변경은 없다.

## 2026-10-30 — G1 330b055b와 실제 단계 비용 판별

root26344774-559c-4e5f-baa3-5326cf7060ec/preflight6a55fca7에서 G1 330b055b-0cb9-4db5-872d-06e2613fe447은21/25 FAIL, C1 시작0이다. source145 SHA29c3b8765316561c2f7126b54acf778053f863d9861149ee1ee8707f62e219ae/installba93175a36c080ff8920772e796b8dad388b9329283640a5254c8187db78a28d. ZIP2033313B SHA c6100170062a957398b188b45c171e8a0033e9685cdd4dda610f3fcddbc59956. 원본 report SHA90909de0ab9c2b4e0431af5706fe0e6e69eb790b6b7784a215fa72887b63b3a2.

최초오류 calibration original wall deadline. 원래 preload 복귀/actual lift 완료 후 STAND 진입8.98633초에 남은1.01367초, 필수1초정착 이후 약14ms여유라 마감에 도달했다. 원시팔측정은PASS, 액션terminal/모든프로세스exit0/강제0/회수/잔여[]지만 측정STOP미확정으로normal runtime/engine인수는FAIL이다. TF중복 새증거는없으며 해당완료검사가 미확정이다. root restoredtrue/pendingfalse/foregroundclosed/residual[] 확인.

닫힌 통과027edf99 대비 분석 task8-g1-deadline-comparison-01.json+method는 같은Gazebo .so/env와 거의같은ROS궤적에서 벽시계1.47642초 증가를 보존한다. SHIFT ROS/wall .8798→.7107. 운영체제CPU주파수/권한설정 원인으로 단정하지 않는다.

task8-g1-numerical-default/one-thread-01: 각120회 고정관측+IK 중앙값wall0.70798/0.84436ms, 수치스레드 설정 개선없음. task8-g1-executor-pool/direct-01: 비활성 실제ROS소유자+고정계산 각150회, CPU17.23/17.63%, 개선없음. task8-g1-ingress-waitset/events-01: 별도시험영역211에서 비활성노드, Clock약100Hz/네센서각50Hz, CPU18.11/17.21%, 단회차이 작고 원인분리불충분. 모든자원join/모터발행0. 세설정 모두 미적용. 실제엔진 성공으로세지않는다. 수치/실행기 원본방법은 계획폴더, 수신기방법은각JSON옆 .method.py에도 보존.

기존 actual owner 단계CPU/wall 관측의 Gazebo 누락 RED task8-gazebo-owner-trace-red.log=FAIL17.21초. 실행기/주기/모터/시각을 바꾸지 않고 검증relay100에 계측만 연결. 관련 네파일 task8-gazebo-owner-trace-green.log=26PASS48.24초. 새전체287반복은하지않고 다음새소스고정 G1→C1에서 실제단계비용을판별한다. 아직XYZ실제성공/Task8fixed3/Nav2/최종push미완료.

root280ff810-a986-441b-91d3-e41470052afa는추가수렴300초FAULT/엔진0회, restoredtrue/pendingfalse/foregroundclosed/residual[]로종료했다. tick10001/freq-6556270의대칭보상표기누락을판별했다. 반사실원본재생task8-clock-upper-encoding-replay-01: 기존301.026초FAULT, 대칭경우동일40초기준165.660초READY. 원본SHA c7989d0f125112234d00cb1394e7d0e3abd0529598cf51ba4471e3df0d153d35, 방법SHA094fdbff68d26ca7984902cc09a17077fb6eaefa72109e480f6b5433d8401c63. 추가read-only검사만동일2ppm의대칭인접표기를인식하며원래clock/engine인수기준·설정쓰기는불변. REDtask8-clock-upper-encoding-red.log 1FAIL/1PASS0.39초. 새관련회귀/실제판별을이어간다.
대칭보상 수정 후 task8-clock-upper-encoding-green.log는 원래 복원/배포판/엔진순서 포함45PASS0.72초다. 실제시계/엔진인수 통과는 별도 새 UUID에서 확인한다.

## 2026-10-30 — c371 정확한 형상 비용과 적용 간격 재설계

root49b2a01c-256e-432b-a840-2292d7eb22b5/preflightd8898a3c-791d-45d4-a1f0-106c23fe71c9의 원래 clock/8audit/19startup PASS. source145 manifest45e1b79118428de3bc9ae98643ac67b572d12a3225830de9e11099a8b337fdb3. G1 47892299-1722-4a76-acdb-942585899d39은25/25 PASS, ZIP2218602B SHA5a3e928fb84ff878e08a0420ba9599ac5affa3ebec51af541c09b515101869d0. C1 c3719b6e-a20f-43a2-b8bf-2edeb0353737은 첫10ms FAIL. solver5회/status0 경과7.3314/CPU5.0287ms, exact geometry 이후14.659699/CPU12.3584ms. 형상만CPU7.3297ms. 입력dt18ms/부모12ms, 거부/적용0·실제lift0. numeric_worker_normal_close=true(ACK/부모reap/exit0), job_contract=false(1submit/0complete/1failed), carryterminal/runtime/engine/reap/residual 모두정상. root restoredtrue/pendingfalse/foregroundclosed/residual[]. 원래 전체G2 미실행거리/yaw FAIL도 그대로보존.

원본실제JSON+문맥 fixture native_c371_xyz_budget.json과 같은report의 실제부모표본 native_c371_parent_reply.json을별도보존. profile100회에서2800IK/11200FK 중복. baseline3소스는 c371-geometry-baseline/에보존. 새 compiled_reference는Python불변기구학계획이며 q/측정캐시·표본삭감·machinecode주장없음. 원래28격자/독립oracle/물리기준유지. RED task8-compiled-reference-red.log→10PASS14.44초, 소유자연결RED→task8-compiled-reference-owner-green.log25PASS20.57초. task8-c371-batch-comparison-01.json+정확method는교대24회잔차차이0/형상중앙2.730350→1.006800ms, fullkernel24회0fail/2.4854~5.5245ms. 엔진밖성능이며실제deadline성공아님.

실제부모12ms에18ms후보의36µm를모두적용할수없다는반사실결함을다음엔진전에재생. 원점선형증명+공통α축소+현재28격자/Kp effort재검사, 미사용변위폐기, nextfresh관측/검증참조제출. 기존높이경로는변경없음. task8-xyz-application-time-red.log1FAIL16.04초/원점증명RED16.68초→task8-xyz-application-time-green.log42PASS32.90초. 실제부모측정재생 task8-c371-parent-replay-green.log1PASS16.03초. source/설치일치 Nbuild task8-compiled-time-policy-build.log16.5초+8패키지감사PASS. 최종관련회귀후새실제G1→C1예정. Task8/fullG2/fixed3/Nav2/최종push 미완료.

39파일 관련회귀 task8-compiled-time-policy-regression.log는24PASS 뒤 기존높이커널 actual_first_transition의 spatial_response10ms예산FAIL(179.86초)로중단했다. 이전체회귀를PASS로고치거나원래10ms를완화하지않는다. 첫실패의CPU세부가pytest에없어 동일실패때last_attempt를출력하도록테스트진단만추가했다. 유일한최소계측차이이며런타임/판정불변.

엔진밖고정입력진단 task8-kernel-budget-diagnostic-f3bead2d-736b-46a0-b139-8657fd94b173.json+method는첫호출포함기존Python높이12회(2.160~4.060ms), native높이12회(1.270~2.103ms), 현재XYZ12회(2.729~4.654ms) 모두실패0이다. 이것으로앞선간헐실패를지우거나원인을CPU/파싱/스케줄링으로단정하지않는다. 같은전체회귀를반복하지않고 실패높이·변경형상/XYZ·실제프로세스·실제configure/시계경계표적시험을진행한다. 새실제시험은진단이며최종소스고정전체회귀는여전히필수다.

표적 task8-compiled-budget-targeted.log 7파일85PASS73.23초. 원래높이13개·현재형상/XYZ·수치자식·실제configure/시계범위를원기준으로검증했다. 전체39파일의앞선FAIL을이결과로대체하지않는다. 런타임은N설치/8audit후변경없고테스트실패진단출력만추가했다. 소스/설정/도구동결후새service-only+compensated-tick-read-only+single-pair Gazebo G1→C1진단실행. 기존안전/인수·MuJoCo native불변, 전체G2/Task8승인이아니다.

## 2026-10-30 — 7개 후보 적용 뒤 실제8번째 예산 실패

root36d2615d-8f4a-4d98-9e57-54dcfd3e757a/session67868 종료exit1/restoredtrue/pendingfalse/foregroundclosed/residual[]. 시계수렴90표본READY·교차PASS·원본40초READY·N설치10.4초/8audit·시동19PASS36.78초. preflight840e8699-2df2-4058-adc9-f5eab00ef2c9. G1 4187f73b-9cfb-4c0b-9e2e-586c48650f68 25/25PASS, source146 SHA1aa043b2f2fea3783595f55c3ccd806ab4e8e7776902e8141b07a11d396094cd, ZIP2222804B SHA650722c429c2ae3d06af8a637bb394f7f02d242d74b1a330725cdd8f0ef9d4e4.

C1 8d4fff0e-975b-4301-bdc7-d4e1e0a0c60d은submitted8/completed7/failed1. 일곱실제참조적용후8번째가exact_ik_validated에서10.888501ms/CPU7.902ms로FAIL. inputbounds.225/spatial.927/constraints3.307/solverfinished5.955601ms, solverstatus0/nit5. 형상CPU증분2.8714ms/전체대기약2.9865ms. 최초예산실패로중단/재시도없음. actuallift최대약29µm이며5mm성공아님. fullG2=false/기존미실행거리·yaw FAIL보존. numericstop ACK/reap/exit0/강제false, carryterminal/runtime/engine/parent/noresidual 모두true. job_contract=false·STOP미확정·하중전환실패 유지. 정상종료를물리성공으로해석하지않는다.

최종실제전송입력 fixture native_8d4f_xyz_budget.json49848B SHA6a1bcdcf2a9bb8b2e82777140876ccaa70f72e92525986f0159cc26def93e3c0. URDF SHA113a4bb3e0852eb4e47f5f032a8ebfb8f13f296b7eb95e5f549d694661aa5651를report와대조, 원본report/source/install와불변limits출처fixture SHA포함.

남은Python형상CPU를현재28표본의동일C++수식으로옮기는구조판별. 신규 test_native_reference RED13.48초→core+기존기하/접촉27PASS26.03초(두실제입력/100자세/비정상입력/핸들/차원). reference_geometry.cpp와native_reference.py자체작성, 외부코드/새라이브러리0, 기존mass/contact ABI불변, reference ABI1. 원형상격자/잔차/여유/10ms/40ms/모터/시각/명령권한불변. 초기GCC범용정렬8배열의경고를보존하고최대8절점의유계삽입정렬로교체해후속빌드에서다시확인한다.

실제owner미연결 REDtask8-native-reference-owner-red.log13.63초. 부모/자식동일library SHA준비대조, 정상ACK전reference핸들해제, 부모소유자종료뒤동기핸들해제, 오류뒤Pythonfallback/자동재시도없음. 최종S/N설치·회귀·실제엔진검증은진행중이다. 기존S/REUSE추가내용을빌드전에완료했다. 아직Native형상경로의실제성공/Task8/Nav2/최종commitpush아님.

## 2026-11-01 — 완료 회귀 재사용과 C++ 실제 판별 준비

task8-native-reference-owner-build.log I/S/N65초+8auditPASS. 기존generic sort경고제거확인, 고정외부tl_expected CMake deprecation만남음. task8-native-reference-related-regression.log는41파일324PASS246.80초로완료했다. 재개때이전PTY는없었지만원본종료로그를확인했고시험을다시시작하지않았다. HEAD4e87/feat13-5/사용자13.4문서40723바이트보존. task8-native-reference-resume-nov1-audit에서현재소스/설치본8패키지재확인PASS.

task8-native-reference-comparison-aa297ed9-279c-4e89-93af-1a6887aa0c33.json+정확method: 두실제고정입력각24회fullkernel 모두실패0. c3712.524783~6.463287ms/8d42.646339~3.822271ms. 같은입력기하의교대24회 원래/축약Python/C++중앙 c3715.7222175/1.831873/.273724ms,8d45.421777/1.5889075/.235275ms. 최대잔차차이0. 원래324회귀·48회수치비교를엔진성공/연속인수로세지않는다. 런타임동결후원래service-only+compensated-tick-read-only+singlepair Gazebo G1→C1실제판별, 첫FAIL중단/정리·서비스복원확인. 검증기준/외부원본/MuJoCo native불변.

rootaeb37ac7-a2d5-474c-8839-65bb508efe4a/session87593는정상close/restoredtrue/pendingfalse/foregroundclosed/residual[]. 추가시계118표본READY·교차/원본40초PASS·N설치19.1초/8audit·시동19PASS38.00초. preflightd7005896-e4e1-4c26-8485-3bbda522c9e8. G1 7057d83b-0627-43da-9dd6-1b091822c61a은21/25FAIL, C1시작0. source148 SHAfdddba5400156f7e626e58394836674da3919f3a31e7138591e63c860aad491d. ZIP2288591B SHA f21f11e7c3c030afd6787321d14df34998398d02a4faef8c01bbbc8fe6f3708d. 최초원인calibration10wallsec, 원참조복귀0.1397mm남음·lift고유3표본/정착미완료. 프로세스all0/강제false/액션terminal/회수/잔여[] 확인. 실측STOP미확정때문normal_runtime/engine인수는FAIL유지. 새C1커널물리성능은아직미검증.

닫힌G1세건 유계trace+process_metrics만비교한 task8-g1-owner-cost-bcbc49bc-3821-4ac8-b1bd-ce565c9d68a3.json+method. 최신487판단 CoM.595758/IK.645355CPU초, 전체2.639202CPU/4.227920wall초. SHIFT4.642ROS/7.200270wall(.644698), 앞선두통과.780794/.805616. 엔진190%core전후·전반CPU증가이며특정하드웨어/renderer/주파수원인확정아님. Windows일반권한읽기counter현재2995MHz는실제시험도중기록아니므로원인으로사용하지않음. 이후stdJSON분석은기존WindowsPython3.11을사용할수있음을확인(불필요한WSL시동회피).

정확G1fault q/측정pose/같은fault의reference+targets와같은URDF/limits 비교 task8-g1-native-arithmetic-2af0aaa2-528d-4b7a-bfae-8737ef043f74.json+method48교대 중앙Python.857450/native.227350ms, IK차이0/CoM6.94e-18m. 명시적GZG1validation/relay100에만같은NativeMass+명목NativeReference연결. 기존moving/관절/간섭/10초/물리/시각검사그대로, MQ/기본/G2정책그대로. REDtask8-native-g1-arithmetic-red.log20.14초→영향7파일66PASS100.65초(task8-native-g1-arithmetic-green.log). 이전324PASS는이G1변경전이며최종전체회귀필수. 중복수동N빌드/324반복없이다음root의필수N빌드·감사한번으로설치/확인뒤새G1→C1판별한다. 외부/sources/Ch01~12변경0, 사용자13.4문서보존, Task8/Nav2/최종push미완료.

## 2026-11-01 — 실제 aa1 종료, 네이티브 QP 표적 검증

root clock-single-owner-aa1cfe71-85f2-467e-96e6-f76bda15337b/session78610 CLOSED: restored=true, restoration_pending=false, foreground closed, residual[]. G1 aa3fdca8-5f42-40a8-adbc-185e9293a892 25PASS, source148 SHA915ec2b4668df6b93525a3d90a09611538fcf54b408756cfacd8e15c47b673e4, ZIP2262857B SHA101764f3b2d6a1ecc1b6b224dc3659f876613b0744ab89a3f8ebe9445bd57f4e. C1 141b0434-e22a-4c13-be15-c37e7e46e887 completed17/submitted18/failed1: solver_iteration12.542302ms/CPU4.456ms, inputdt14ms. 실제5mm 들기 미완료/fullG2=false. 수치worker ACK/reap/exit0/reference해제·팔terminal·runtime/engine정상exit0·잔여없음·서비스복원 확인. job contract=false/STOP미확정은FAIL보존. preflightc06705bb-0b10-4000-a68d-06bc74e2ac01.

G1유계trace비교task8-g1-owner-cost-f1921c61-...json: CoM+IK CPU1.241→0.394초, owner2.639→1.512초, SHIFT비율.77562. 단회성공/다른환경이므로연속성공이나인과확정아님. 141b정확fixture49522B SHA6ef36c0313ca91b6f32632d6321945cd6e117d65fa875b91328806af9d4e084c. CPU할당읽기는8core/제한없음이나별도boot사후관측. 닫힌idle/shared/reserved각48비교는모두성공, reserved최대9.036ms로악화해affinity미채택. 배경14자식정상exit/배정복원.

QPMAD1.5.1@11602ec9f87a62a97ba8318ebd81da6646f3c631 최소14원본79301B+LICENSE/NOTICE/UPSTREAM을Ch13안에만복사, Git blob/SHA대조. S native_xyz C ABI1, 같은12변수132제약·32반복·10ms·40ms·28격자. I/S/N빌드1m54초+8auditPASS. RED13.90→정확입력/core5PASS18.87. 54섭동의신규2nm비교FAIL/진단보존, native목적값3.133e-11개선으로강볼록거리상계+독립전체primal검사로신규시험교정(실제기준변경없음). 최신task8-native-xyz-convex-properties10PASS13.13초. native부하비교idle/shared각48실패0/중앙.3644/.697ms/최대2.7065/6.1484ms, 배경정상종료. 실제엔진성공아님.

재개HEAD4e87/feat13-5, 기존변경/사용자13.4문서40723B보존. task8-native-xyz-process-red14.28초: 실제자식은기존SLSQP선택. stance_xyz만native연결, backend+optimizerSHA고정, 두handle해제전ACK불가, 정상close와작업실패별도판정. N빌드11.1초+8패키지auditPASS. task8-native-xyz-process-green은관련6파일59PASS50.73초. 전체고정본회귀·실제C1/전체G2·연속3·Nav2·최종push는아직미완료.

## 2026-11-01 — 35d 실엔진 판별과 하중 목적식의 최소 재현

clock-single-owner-35d24877-8f58-4e4a-894c-3a893796d42b/session5428 CLOSED/restored=true/pending=false/foreground_sessions_closed=true/final_related_runtimes[]. 시계수렴96/교차60초/원본40초PASS·N10.5초+8audit·시동19PASS28.59초. preflight ad3f3dc8-1909-4962-9e19-90887f2e3f0d.
G1 a71d1e8a-044f-490d-99a0-8cadba545045 PASS25, source166 SHA63479b0880ac2723495e4cad5ea116733edfc4690db5d465daf53fab69f07daa; ZIP2280191B SHA529156a82032cbe4965abfb1da30fa6a264c763a0bcb6393bd6f202240fc6979. C1 76b1aac2-c54c-4178-8ac1-6b77616792de 최초FL measured unload timeout(25.728→31.732ROS초), 실패이후재시도0. 수치289/완료288/폐기1/실패0, backend/qpmad SHA88283f0e..., reference SHAaf982840..., 두handle해제/stopACK/reap/exit0/강제false. 팔실제terminal결과·runtime/engine정상exit·parent회수·잔여없음확인. 기존실측STOP/손상되지않은전체required_checks FAIL은유지하고C1/전체G2성공으로세지않는다.

닫힌297고유촬영만한번분석(task8-contact-76b-series-ddc2934b-...json): FLFn29.509→22.867→17.464→13.325→10.163→7.441→5.577N, 참조상승2.719mm/10mm. 마지막수치전체1.231ms. native경계task8-contact-76b-native-boundary-20e10186-...json은직접원본1732패킷/해제구간300개,요청/적용/write_capture/force_command/constraintwrench를보존했다. actual_generalized_force=null이므로5배torque오류/1/5실제적용주기는단정하지않는다.

정확76b회귀fixture45566B SHAf30c847d15dfa79f2a3e01403051cebbbfaa850d8908fd2ed932279193347de5. 같은URDF/modelSHA와실제validated_profile limits를확인했다. 목적식진행부족을같은입력으로검증하는test_terminal_force_objective 미구현RED14.74초확인. 승인된부분재설계범위에서bounded_terminal_force를명시적GZG2자식에만적용, 기존rate_1_per_s는독립oracle로보존. 기존H/132제약/32반복/10ms/40ms/28격자/2mm/s·10mm·6초·2N100ms·모터게인과힘상한불변. S/REUSE를빌드전에갱신했고I/S/N설치중이다. 아직새목적식수치회귀/실제인수성공아님.

최종설치 task8-terminal-force-build 3패키지1m43초+8auditPASS(기존tl_expected외부경고만). 신규목적식3회귀통과후기존Python oracle의8d4섭동이constraints_ready10ms를넘어 task8-terminal-force-green은1FAIL9PASS40.63초로보존했다. 기존check-load-redesign과동일한명시적단위시험1스레드설정으로표적7파일을실행한 task8-terminal-force-related-singlethread는69PASS62.83초다. 사후새프로세스읽기task8-unit-numeric-threads-0204cae7-...는환경변수미설정·import후프로세스1스레드/열린openblas경로없음이었다. 따라서스레드수가그원인이라고확정하지않는다. 실패순간스케줄러증거가없고원본실패는그대로남긴다. 실제런타임설정변경0/기준완화0.

정확76b한입력두목적식비교 task8-terminal-force-comparison-bf35515e-954d-47f7-a662-d4588dce9fc4.json+방법: 기존/최종힘의선택참조증분1.746748→24µm, 최대요청속도0.639263→2mm/s(원상한), 예측FL5.526742→4.475807N, 계산0.751245/0.747049ms. 독립전체primal검사는69회귀에포함되며예측힘을실측힘으로사용하지않는다. 준비응답/각작업/닫힘기록에force_objective를남긴다. 이제새소스동결후원래G1→C1단일판별을시작한다.

## 2026-11-01 — b6 실제 종료와 C1 촬영 조합의 원인 재현

root clock-single-owner-b6e10b19-70d1-4bdc-8465-f5a5f996c6d3/session91328 CLOSED/restored=true/pending=false/foreground_sessions_closed=true/final_related_runtimes[]. preflight afa4b85c-5d86-4db1-b4fe-be5286268022: 수렴79·교차60초·원본40초PASS, N10.3초/8audit, 시동19PASS28.69초.
G1 28109276-099f-41fa-865f-9738562e737d PASS25, source166 SHAf793b410b037cbcc4d17a94b437ea245e19f8ee8e336086b57f9685bd990a4bb; ZIP2301561B SHAa6672aef06a3be3ca871eeb4a5f5912f13e6f9cfbac70102228f6fe94de5343d. C1 bcec91e5-cb9c-4559-90ff-3ee7fb32ad77은관측_component body/joint/contact capture mismatch로중단됐다. crawl/carry first_fault=null, 수치43/완료43/실패0, 마지막1.6449ms/반복30, 두handle해제/stopACK/reap/exit0/강제false. 팔terminal/runtime/engine정상exit0/잔여없음/서비스복원확인. 전체required_checks의실측STOP/ownership/미실행방향FAIL은보존하고실제4발들기완료로세지않는다.

같은mission_probe수신journal한번분석: 497수신중독립latest조합3개44~56ms불일치. 40ms는기존소스기준(앞선20ms설명정정)이며실제센서손실로단정하지않는다. 회귀fixture는240ms/36수신74058B SHAeb3c66510f4ae536d9f007a98cac9ae84ac5287db094ca713d05c743cba01f3c. 원본journalSHA와축약전921900B/SHA를보존했다. 원본actual은그대로남긴다.

ComponentCaptureJoiner 미구현RED13.88초→N설치11.5초/8auditPASS→관련4파일22PASS34.16초(task8-component-capture-join-green). 이어최신3채널모두fresh여도앞선미완성접촉만료를건너뛰면안되는조건으로보강한4회귀11.51초PASS(task8-component-capture-join-expiry). C1문법ASTPASS. 채널32/접촉FIFO/전체span40ms/dual200ms/첫receipt/중복·중간고하중·역행·overflow실패고정/close후차단. C1만기존_sensor의같은callbackreceipt로읽고새publisher/executor/worker/명령0. 모드RPC대기전에는arm하지않고ACK뒤원래4접촉기준baseline을정한다. 모드상태발행대기중에도FIFO를소비해관측공백을만들지않는다. 원래FK·2N100ms·5mm·180초/50Hz·모든G2required_checks·모터/물리/힘목적식불변.

이번수정은C1관측경계뿐이므로이미완료한힘/수치69회귀와324전체를중복실행하지않았다. 최종고정본전체46파일회귀와기존최종matrix는이후필수다. 다음은코드동결후새G1→C1한번판별,최초실패시종료/복원/원본보존이다. Task8실제4발/전체G2/양엔진고정3+reverse/Nav9–14/최종push미완료.

## 2026-11-01 — FIFO 소비 수정과 사용자 재부팅 뒤 재개

root a16d4ef6-b91d-420b-9213-84f7e47d563f CLOSED: restored=true/pending=false/foreground_sessions_closed=true/final_related_runtimes[]. 원본시계 수렴120표본/교차60초/40초quiet PASS, N10.7초/8패키지audit, 시동19PASS28.59초. G1 51dfcb66-a6a6-4526-89e8-a84292852953 25PASS, source166 SHA96b724fb0bd822c148c371ca30008fb14eccd226891d0aedcac85050d1d4e8e8, ZIP2305812B SHA3fa01908deeb6500be0e732477eaf5ea458c466efd9327a8ff1369a572435ecd. C1 36900d72-1047-4687-b1e9-67ea54ae4385은 pending contact wall_age로 실패했다. 결합175회/최대차16ms/대기0/close시9접촉, 실제4발완료0. 수치17제출16완료1폐기실패0, 두 핸들해제/ACK/reap/exit0/강제false. 실제 인수 FAIL은 보존한다.

실패는 한50Hz관측wake당 한 접촉만 처리하던 소비 경계였다. C1만 기존 FIFO를 한 주기 최대32개 소비한다. 원래 age200ms/차40ms/고하중 리셋/2N100ms/FK5mm/50Hz/180초 및 모든 G2 checks는 유지한다. RED task8-component-cycle-red.log1FAIL12.73초, N설치10.5초/8auditPASS. 이어진 회귀는 WSL 무응답으로 결과 미확정. 일반 종료와 승인된 WslService 정상 정지·시작도 StopPending으로 실패했고 로그를 보존했다. 준비한 서비스 PID 강제 종료 helper는 실행하지 않았다.

사용자 Desktop 재부팅 후 boot8c545a6f-8ccd-42a2-b2d3-7b0ef577bf04, WslService Running, native 관련 프로세스 없음 확인. task8-reboot-20261101-audit 8패키지PASS. task8-component-cycle-green.log는 관련5파일24PASS60.60초다. 전체검증 목록에 신규2회귀 파일을 추가하여47파일이 되었으나 현재 전체를 반복 실행하지 않았다. 다음 고유 root460fee6d-a09a-4bf6-8b7a-1df5d5a35f03/session42585에서 원본시각을 다시 관측한다. 커널 쓰기 없이101표본/40초안정 READY, 이후 교차 및 원래150초 witness 뒤에만 G1/C1을 시작한다. 엔진 성공·고정3회·전체G2·Nav2 완료로 세지 않는다.

## 2026-11-01 — G1 8500 시계·trace 수명 판별

root460fee6d/session42585 CLOSED/restored=true/pending=false/foreground_sessions_closed=true/residual[]. 교차60초·연속150초·기존40초quiet·시동19PASS36.96초, N10.6초+8auditPASS. G1 8500b070-e207-43ec-bf3a-d3b34aa42a06 FAIL, source166 SHAb32098dcea1dac0e5ac04ee03ca35db4df972cb9391f8967fe815966a3eceb91. ZIP2679176B SHAbc613a921156a0fab4837b20afe8a12e82b677e494580243983c6dd81ccbf91e. C1 시작0/첫실패뒤재시도0/강제false/잔여[]. relay exit1·측정STOP미확정 때문에 정상엔진/runtime 인수FAIL은 보존한다.

최초 crawl fault는 imu:wall_age, 제어ROS19.210초. 그러나 pending IMU19.220~19.280초와 새body/contact가 callback 원래receipt로 있다. 마지막 relay trace 보조구간216.189195ms(563789719265→564005908460)가 같은 executor를 막았다. source_stalled는564005962260에 기록됐다. 경과시간에 스케줄링도 포함될 수 있어 디스크 단독원인/정확한write syscall 시간으로 단정하지 않는다. 원본SHA·최소 선택자료·방법은 task8-clock-trace-8500-34ef586c-21c6-44fc-b39d-d7c6bf76abc9.json 및 task/analyze-8500-clock-trace.py에 고정한다.

동일 시계/안전기준을 유지하며 보조 파일IO만 bounded AsyncTrace로 분리했다. 미기록/in-flight 합128개·4MiB 고정, FIFO, 초과/쓰기오류terminal, 무시/자동재시도없음. relay자원 종료→queue차단/drain/join→fd닫기 순서. 실제 .writer.json과 기존 clock/exit/STOP/ownership를 모두 요구한다. RED 첫 시도는 신규target 구성 누락으로 빌드 전 실패(task8-clock-async-red); 후속 구성 뒤 missing header RED(task8-clock-async-red-header)와 writer-assessor RED1FAIL27.04초를 별도 보존했다.

I/S/N task8-clock-async-build 2m8초+8패키지auditPASS. task8-clock-async-cpp-green: worker3+gate10+실제ROS8=21PASS,230ms sink지연/원본subset/100Hz/실제pause고장/취소/경쟁소유자 검증. task8-clock-async-runner-green은6파일100PASS45.21초, 실제 drain/join 부재·잔여·오류·누락기록을 거절한다. 전체목록은48파일로 확장했으나 전체/물리 성공을 대신하지 않는다. 이후 새 root762c380a-7d36-4ac1-9a2d-96909aacc780/session20724에서 동결된 원본시계→G1→C1 판별 중이다. 일반 사용자 idle연결38615는 검증 사이 동일 부팅 상태를 유지하며 설정을 바꾸지 않는다. Task8·Nav2·최종push 미완료.

## 2026-11-01 — 로그 분리 후 G1 05379a5f, 처리량 비용 분해

root762c380a-7d36-4ac1-9a2d-96909aacc780/session20724 CLOSED/restored=true/pending=false/foregroundclosed/residual[]. 수렴102표본/교차60초/연속150초/기존40초quiet/시동19PASS36.11초, N12.6초+8auditPASS. G1 05379a5f-1b5a-4a68-a12c-8de58f463e2d FAIL, source168 SHAa761f9937e0dfadfc0e0f8d75e96fc7d114c29ce5e821f3a8ead0d9e3c685bce, ZIP2381603B SHAad4a0a0d366cecbf59a23d6189e2abd3bde2466e48bc8ce0da3689669be6b695. C1 시작0/첫실패뒤재시도0/강제false/잔여[]. clockcontract=true, writer3883/3883·pending0·drained/joinedtrue·error빈값·peak1record/1552979B. 보조 trace 최장4.6672ms. 이전216.189ms와 다른환경 단회 비교이므로 성능인과 확정/고정3회로세지않고, 주입230ms 회귀의 구조 판별과 구분한다.

실제 최초 실패는 calibration original wall deadline. 요청790026649002, SWING796859379832, TOUCHDOWN797640467561, 원래preload복귀/3고유착지/STAND799440654100, deadline800026649002. 동작완료9.414005098초로 원래1wall초 settle에0.585994902초만남았다. 실제5mm 들기·복귀가 있었지만10초인수/실측STOP·전체정상종료조건 FAIL은 그대로다. 동작기준/게인/시간을늘리지않는다.

닫힌 두사례의 제한된 cost/proc메트릭만 비교한 task8-g1-owner-cost-2d5be54b-38a4-45ef-91fa-b247ce8c327e.json+동일method. 앞선51dfcb66 PASS와현재05379a5f의SHIFT ROS/벽시각4.616/5.220→4.636/6.801초, SWING.544/.600→.538/.781초, RETURN1.242/1.300→1.220/1.800초다. ownerCPU합1.129→1.783초/주제어프로세스60.88→73.48%onecore/Gazebo185.44→193.11%onecore. 모델·제어 변경이없는경로도CPU시간이늘었지만 호스트하드웨어/열/스케줄러 단독원인을확정하지않는다. 사후WMI는시험중측정이아니므로인과근거로사용하지않는다.

다음 판별은 Ch13 observer의 Update/PostUpdate CPU·경과와 두단계 사이 경과를 고정카운터로 분리한다. 미구현header RED task8-observer-cost-red 보존. 자체observer_cost.hpp/3회귀와기존Gazebo관측6회귀=9PASS, I/S/N task8-observer-cost-build1m25초+8auditPASS. 기존50Hz native_controls에직전완료callback누적값만추가, 센서header/주기/데이터·명령·형상·접촉·모든인수불변. 별도이력/worker/파일없고단계사이경과를physics CPU로오인하지않는다. 이계측의성공은보행해결이아니다.

root3e617975-1891-4db8-a505-4ad368c5d470/session4286의한번판별을시작했다. 동결소스·첫실패중단·서비스복원·잔여검사는그대로다. G1진입때호스트합산CPU읽기90초/최대18표본/64KiB를추가할계획이며기록자체부하·조회불확실성을함께남긴다. 설정/관리자/드라이버변경은없다. 기존지나간전체회귀를반복하지않고지배적비용판별뒤에만런타임을수정한다.

## 2026-11-01 — 3e 시계 witness 실패와 기준 결정 대기

root3e617975-1891-4db8-a505-4ad368c5d470/session4286 CLOSED/restored=true/restoration_pending=false/foreground_sessions_closed=true/final_related_runtimes[]. 수렴200표본/40초stable·QPC교차60초PASS 뒤 연속150초 witness FAIL, validation_exit=null/엔진0. 기존2ppm표현조건을낮추거나무시하지않았고실패뒤자동재시도0. tick9999/freq6228026scaled=95.032135ppm의합성보정−4.967865ppm이119표본/2.5822844초였고시각step0이다.

오프라인 task8-clock-witness-comparison-52e09829-5ee0-46a0-b966-603ee2390729.json+동명method는원본6915표본/SHA를고정했다. RAW조회 전후 불확실성을포함한1초이상 실제진행률6868구간은0.999875444~1.000125353, 기존±0.1% 실패0이다. 원본FAIL을고치거나새실행성공으로세지않는다. 공식chrony/adjtimex설명과세부결정은 CLOCK_BLOCKER_DECISION 문서첫항목에남겼다.

기존2ppm 추가필수조건을150초전체 실제±0.1% 연속검사로교체하는읽기전용opt-in안을제안했으나 아직검사소스를변경하지않았다. 사용자‘기존기준변경금지’및문서‘2ppm유지’에해당하여 async로구체결정을요청했다. 원래1msstep/QPC±1%/40초quiet·150초원래기한·추가300초/로봇안전·물리기준은유지하는안이다. 단순2→5/10ppm 임계값변경이나커널/chrony조작은제안하지않는다. 승인전새engine없음. 측정용observer_work와hostCPU기록자는이번engine0때문실제관측미검증이다.

자체방법소스5개/SHA·크기manifest는 task8-trace-methods-f92d330d-65e0-4d01-8261-e96d86df1e66/에보존했다. 사용자13.4문서40723B보존, HEAD4e87f6f6/feat-ch13-section13-5 이력불변, commit/push없음. Task8 실제C1/전체G2/양엔진고정3+reverse/Nav2 Tasks9–14/최종회귀는여전히미완료다.

## 2026-11-01 — 승인된 실측 witness, 실제88 실행과 CPU 경계 선택

사용자 후속답변으로 실제 진행률 기반 witness 교정을 승인받았다. 기본/기존2ppm 실패는 그대로이며 --measured-clock-witness는기존service-only/compensated선택과함께명시해야한다. Ch13 navigation/clock_witness.py는512이력/1초이상RAW불확실성구간/원래±0.1%/1msstep/원본150초완료를검사한다. 실행전소스·설치일치/실행UUID복사고정. RED17.04초→N9.45초/8auditPASS→관련59PASS10.68초. 오프라인task8-approved-clock-replay-6da5586e-f318-4336-ba6f-6b0d3a34255a는6915원본/6868구간PASS지만원래3e FAIL/SHA를변경하지않았다.

root88a08400-c1ac-4f88-9706-c2a06110860b/session83267 CLOSED/restoredtrue/pendingfalse/foregroundclosed/residual[]. 수렴111표본/기존40quiet·교차60·원본150 measured_rate PASS(6902표본/6855구간/.999880352~1.000118200/최대이력50,legacy_nominal도true), N10.3초+8audit·시동19PASS33.05초. G1 701c2860-d0a4-4377-ab9a-f0b5a9ef5f5b 25PASS, source171 SHAfaf3c8fab9e0b93d62c42e871313565cd885b249ba52cb9ef784de4aad2279b3, ZIP2348623B SHA39f57937924d54f527844c22f175f652d801829190ea679635f0aceb64b2b8b3. 이단회통과로간헐10wall문제/고정3회를해결했다고하지않는다.

C1 7e642180-032d-4077-9ee4-1a2f11fde186은최초numeric native_qp_returned 경과10.4469ms/스레드CPU3.4507ms로FAIL,54제출53완료1실패. offCPU/계측되지않은경과6.9962ms. solver구간CPU62.4µs에비해경과2.3115ms로계산부하만의원인은아니다. 접촉결합227발행/차최대8ms/매칭대기0/종료pending0/error빈값, 관측245주기/최소간격20.001495ms/최대batch3/실제226고유접촉. FIFO적체수정은실제관측경계를통과했으나물리4발완료0은보존한다. 원래required_checks와임무FAIL불변. 파괴시정리system.log의실제숫자owner ACK/reap/exit0/두handle해제true를확인했다. 실패뒤측정STOP미확정/비활성화거절로앞선RPCclose평가FALSE인것과구분한다. status/잔여없음만으로종료성공을만들지않는다.

고정관측cost 88-acf7ea97-3402-4780-81c3-e80e16f89c60.json+방법: G1스텝UpdateCPU199.41/Post228.53µs, C1Update212.23/Post238.87µs(합CPU451.10µs/경과494.03µs/2ms), 오류0. 단계사이C1경과1233.47µs는DART CPU자체로단정하지않는다. 정확7e64회귀입력45758B SHAa6159d58ebbfdf899cc659f549813e7dc413f74982fb1c383cbb61528d27a0f8. G1원본은보존정책대로native canonical에서읽고추가복제하지않았다. 첫Windows분석은로컬raw생략으로실패했고native경로명시후한번분석했다.

호스트4초CIM기록자는timeout/exit1로실제연속기록을못했고, 별도15초단일조회는01:48:37.545~39.980UTC/CPUperformance87%,maximumfrequency88%,time97%를기록했다. 단일조회범위를C1실패구간과동일시하거나열/전원단독원인으로사용하지않는다. 다음읽기기록자는15초조회/오류도기록/최대18표본64KiB로수정해C1시작에묶는다. 설정·관리자·드라이버변경0.

관측자내부StringMsg dump→JSON parse 왕복/완료batchdeepcopy를직접owned JSON값/move로분리했다. 기존StringMsg wrapper/모든검증·수치·스키마·빈접촉·시각·2ms/50Hz·모터/10ms32회/40ms는유지한다. missingAPI RED(CMake63초) 보존→I/S/N2m21+8auditPASS→관측동등성/소유권7+고정cost3=10PASS. 동일ECM400회CPU기존15.071ms/직접7.6743ms(약49.1%감소)는소규모읽기비교이며실제전체성공아님. 나머지변경없는69/100/전체회귀를무변경반복하지않았다. 후속동결root2c9f0a33-2e94-4daa-876c-21e3b2a373df/session67454에서원래시각→G1/C1한번판별중이다. Task8/전체G2/양엔진고정3+reverse/Nav9–14/최종push미완료.

### 2026-11-01 CompleteXYZ single-boundary redesign (not physical acceptance)

Closed root2c9f0a33: G1 45a9b4f2=25PASS, C1 9c62136f=FAIL (23submitted/22completed/1failed; exact_ik_validated10.581101ms wall/3.6444ms CPU). FIFO188 captures, maxspan10ms, pending0, no association error; no completed foot transitions. Root restoredtrue/foreground_sessions_closedtrue, no new engine active. Do not count different-source G1s as consecutive. Original failures unchanged.

Expected RED task8-complete-xyz-red:1FAIL14.83s, missing integrated native kernel. Exact9c62 fixture47140B exported once, source preserved. Added same mass/contact ABI1 + same QPMAD XYZ ABI1 + same28-sample reference ABI1 + nonlinear servo proof in one new complete ABI1. General affine inverse retained. Fixed Python I/O pointers/buffers; original10ms starts before Python validation and passes only remaining budget to C++;40ms transport/32iterations/all original physical/geometry bounds retained. No fallback/cache/retry/rights change. Legacy calculator remains independent oracle.

Build task8-complete-xyz-build:I/S/N1m47s + eight-package source/install audit PASS. task8-complete-xyz-green:17PASS19.13s (four real fixtures/independent primal/no Python reentry/invalid inputs/borrowed lifetime/raw ABI dimensions/no output commit/original wall start). task8-complete-child-red:1FAIL22.25s, actual child still fragmented, expected backend missing. Wired only stance_xyz child to complete kernel and added explicit preparation/backend/ABI and closed binding ACK; height unchanged. N rebuild/audit task8-complete-child-build in progress. Physical C1/G2 success not asserted.

Complete child GREEN task8-complete-child-green:83PASS79.97s (actual backend+ABI, cancelled/outstanding failure retention, owner/lifecycle/close, reference integration, terminal-force objective). Nbuild16.2s+eight-package source/install audit PASS. Core17+affected83 PASS; no physical acceptance implied. Freeze runtime sources now for one approved measured-clock Gazebo G1→C1 diagnostic. No competing builds/tests/analysis during engine; host collector, if used, is bounded read-only and not causality evidence.

Latest closed root debf36c4-969c-45b8-8c3e-a43da0b8cc3a: measured150s PASS6896samples/6848windows; startup19PASS28.93s, Nbuild10.1s+8auditPASS. Gazebo G1 b06558d5=25PASS. Complete kernel actual C1 9b6038a5=FAIL, dispatch40ms at ROS33.004; submitted13/completed12/discarded1/failed0/pendingtrue. Child backend native_complete_1 verified; ACKtrue/reapedtrue/exit0/reference+optimizer+complete bindingclosedtrue, yet pending remains => numeric normal close and runtime acceptance FAIL, not promoted. Engine exittrue/parentreaped/residual[]/forcedfalse; root servicesrestoredtrue/restoration_pendingfalse/foregroundclosedtrue. No host CPU monitor ran in this root. Do not equate dispatch deadline with a proven numeric10ms failure. Next: inspect consumed late result and pending/ACK lifetime, reproduce targeted regression; no new trials during user-requested status/model-cost review. Idle shell16062 exited normally. No commit/push, no fullG2 success.

### Resume: approved task-specific model policy; native single worker

Tool inventory has no main worker model/effort switch; do not claim Astra/Sol switch occurred, no subagent spawned. Scope stays native singleworker. C1 9b6038a5's actual post-receive40ms fault consumed result before pending release; last_attempt was lost. Controlled actual numerical child reproduced this exact boundary (task8-late-reply-lifetime-red1FAIL18.71s). Identity-validated consumed reply now retires pending, retains attempt and bounded issued/poll/compute/receipt metadata, accounts discarded and numeric failures before latching deadline; no late model/result returned, no retry. N14.9s+8auditPASS; affected37PASS37.98s. This fixes lifecycle evidence only, not physical/dispatch success.

Same actual parent model_mass→model_safety19.0483ms/CPU1.3405ms; original result collection happens after model safety. New bounded pre-model collection design in LOAD_TRANSFER_REDESIGN_KO: same40ms atactualcollection; single completion slot, no command; current measurement/reference/age/generation checks atapplication, actualmonotonic200ms receipt check, no retag; stop/reset/faultdiscard. RED1FAIL19.51s showed ready reply still behind measure. N12.5s+8auditPASS. New5 tests + affected owner/gait/fault tests running. No engine started, no new system settings, no unchanged full matrix repeated.

Pre-model collection first GREEN retained17PASS/1FAIL56.85s: zero-velocity path discarded twice. No criterion/test was weakened; skip early collection on zero command, retain original stop path's single discard. N12.7s+8auditPASS. task8-early-numeric-collection-green-2:85PASS94.24s (5new + async owner/XYZ/current state/gait/lifecycle/fault/unload). All modified runtime installed. Freeze for one actual measured-clock Gazebo G1→C1; no concurrent host monitor/test/build/analysis during engine. Same original10ms/40ms/200ms and physical gates. Model-selection UI limitation recorded, no model switch or subagent claimed.

Actual root4e7e532d closed/restoredtrue/restoration_pendingfalse/foregroundclosedtrue. Clock convergence129samples then150s6896samples6848windowsPASS; N14.9+8auditPASS;startup19PASS38.15s. G1 1e7eda2bFAIL original10swall calibration: preload/STANDcandidate8.574s leaves1.426s; source172files manifest4ba7c6de0dd1969d652ed1690e97dde2f5dc44d6407ee335bfab98b2bc3de3d3; ZIP2412628B SHAc490daebe3dd1c69ff0fc16219c5de51386b7d8ff7ab1f7ca56411aedb6f0bec. Engineparentreaped/residual[]/forcedfalse, runtimeacceptanceFAIL/engineacceptanceFAIL retained. C1 notstarted; no physical claim for pre-model collection fix.

Independent last1.426s probe-window analysis53samples: jointspeed9/bodyspeed24 violations; longestobservedhealthy0.60764458s. Actual ownercache/dwell differs, so proxy not acceptance replacement. SourceframeSHA e6e04a6b25f195637529e4ee965161fb5432fb95fb06000ec6b8ec57e52506f8; compact analysis+method g1-settle-window-005b4cdf... preserved. First helper execution rejected command_publications object schema before writing output; corrected rows/joint_names binding and removed repeated raw parse. Originalfailure unchanged.

G1-only hypothesis: terminal constant acceleration discontinuity excites body residual motion; reuse existing own quintic velocity sampler at original20mmps/.2mps2 (not loaded .01mps restriction). Failedseedreturn1.092ROSs becomes1.179ROSs, so actual reducedsettling must repay extra curve time within same10swall/1ssettle. No physics/gain/force/reference-source changes; ordinary/default/MJ/G2 policies retained. RED task8-g1-smooth-preload-red1FAIL23.24s unknownpolicy; nativeG1 selects explicit bounded_preload_smooth. N9.85s+8auditPASS; target+legacyG1 regression inprogress. No unchanged engine retry.

G1 smooth preload GREEN task8-g1-smooth-preload-green:27PASS53.96s (new2 + existing inplace/fullpreload/ownerwalllease/nativegeometry/crawl lifecycle). N9.85s+8auditPASS. Explicit nativeG1 selection only, legacy/default/MJ/G2 policies retained. Freeze for one actual G1→C1 comparison; no repeated unchanged full matrix, no CPU competing work/hostcollector during engine. This is a physical hypothesis test, not acceptance completion.

Root4ba87d36 restoredtrue/pendingfalse/foregroundclosedtrue; G1 03f1ca75 FAIL10swall, native_g1 smooth selected asintended. STANDcandidate9.473s leaves0.5267s; C1NOTSTARTED. Parentreaped/residual[]/forcedfalse/engineexittrue; runtime/engine acceptanceFAIL preserved. Source172manifest2c9f17a6721ec285c09cd940b1ae3a00932f21ad16c8e64d8408becb9e515d54, ZIP2400776B SHA5a369723d80c68b9b7bb37ebdb02c3f9ac73423043dfc07798ef6a0809dfd847.

Closed comparisons g1-process-cost-fa3a4810...+method: b065PASS candidate6.548ROS/7.035wall=RTF0.93076; 1eFAIL6.466/8.574=0.75415; 03fFAIL6.628/9.473=0.69965. ObserverCPU/step196.322us vs271.344us, noobservererror. Cannot infer hardware/frequency/llvmpipe singularcause. Old1e native_controls pruned by preexisting retention before comparison, explicit unavailable; do not regenerate or mark original preserved currently. Existing system-mono offset maxsteps700/2400/1200ns (<1ms), no runtimeRAW/schedwait evidence. IdleWSL8CPU/affinity8/noquota/currentpressurelow; idlehost Balanced CPUperf98% baseline only, notenginecausality. No otherwork stopped/settingschanged. LP_NUM_THREADS already2. threadpoolctl absent; noinstall. Existing NumPy freshprocess comparison b4d560a1... actual1thread both default/env1, medianinverse3.209/3.300us, no improvement=>NO OpenBLAS/profilechange adopted. OfficialOpenBLAS/runtime/extensions usedread-only, externalcopy0.

Smooth experiment failed; keepcurve/test/evidence but revert nativeG1 binding to original bounded_preload (ordinary/MJ/G2 unchanged). Need runtime causal measurement, not more curve trials. Added1Hz raw-before/mono/realtime/raw-after plus bounded ownedGazebo/crawl threadruntime/runqueuewait/timeslices, max96/128 with pid/pgid/start/uid guards and explicit missing/truncation/selfcost; no sensor/control inputs or priority/clock writes. RED1FAIL21.17s missingmodule; N14.1+8auditPASS. FirstGREEN1PASS1FAIL33.47 due newdiagnostic invalid cross-domain CPU<=wall assertion (CPU253800ns >mono235397ns); preserve failure, separateRAW/mono/CPU counters and require eachnonnegative instead, robotcriteriaUNCHANGED. N13.3+8auditPASS. Exitowner race RED1FAIL20.30s+6deselected (same exitingPID becomesroot-owned inprocfs); add sameidentity+terminalstate recheck, liveforeign/recycled stillfatal. Nrebuildinprogress, noengineactive. Next finish8new+existingprocess/runner/shutdown regressions, freeze once, actualG1-C1 to distinguish runtimeclockprogress/queue/compute. No unsupported model switch or subagent.

Runtime CPUprobe GREEN3:40PASS36.09s; Nexit-race rebuild9.34+8auditPASS. GREEN2 original4PASS1FAIL33.73s retained: test assumed whichTID appears in bounded directory subset; separated truncation check from fullscan missingthread check, no production/robotcriterionchange. Probe no writes/threads/priority; 1Hz sameexistingcollector. G1binding rollbacklegacy explicit; smoothclass/27tests/archive retained. Freeze one actual G1→C1 with RAW/schedstat evidence to distinguish clockrate/queue/computation, not more trajectory parameter trials. No concurrent analysis/CPUtests/hostqueries during engine. Original safety/acceptance sets unchanged.
2026-11-01 resumed: root5588b9e4 session verified restoredtrue/pendingfalse/foregroundclosedtrue; actual G1 835a4a4c PASS25, C1 76838bec FAIL contacts:wall_age209.302ms in STAND, numeric0submitted. Numeric ACK/reap/exit0/allhandlesclosed verified; not an exercise of early-collection40ms fix. Source173manifest79f5491f7a48d52f2f4b4e854ca57647f900898de7fe0f1096aabb2a6656b000; ZIP2409907B SHA176a33792d6a9a7455667b9b8c120db789de946585569c82696e965e093023a5. Runtime RAW boundary66817455: mono/raw stableabout3ppm; broadprobe max72.224mswall/20.387msCPU => not negligible. Independent receiver also missed normalized contact refresh while joints advanced. Original separate feet/contacts publication/transport member loss is NOT established. contact-delivery-gap5e0441a9 compact+method retains boundaries+hashes. First analysis helper failed on top-levelcontact_ingress key before anyoutput; corrected to first_fault ownership, original evidence untouched.

Bounded offline synthetic DDS ABBA ingress comparison fd9490c1: 4seconds each, same6sensor+clock/header/firstreceipt/parser/inbox,1840 sent/received each,strictincreasingall,alljoined/noerror. Waitset processCPU.20927/.20883core vsEvents.13495/.13157 (~36%lower; includes senderCPU). No engine/TimeSource/model/motion acceptance inference. Adopt existing owned serial Events backend only for explicit Gazebo G2, as already used in MuJoCo G2; model/cadence/default/G1 unchanged. Live dependency/process/thread attestation retained with corresponding expectedbackend. Broad thread scan now CLIoptin; original process/raw/requiredchecks retained. GZ selection RED task8-gz-event-ingress-red1FAIL19.99s; optionalthread RED task8-thread-probe-optin-red1FAIL14.77s. Nbuild9.83+8auditPASS; related regressions running. No same-source engine retry/model switch/subagents/host setting change.

Gazebo Events/optin related GREEN89PASS62.81s; N9.83+8auditPASS. Contact boundary RED1FAIL18.84s then minimal bounded counters/maxgap/lastpair/pending-firstreceipt snapshot+readonly report RPC, no per-frame IO or authority changes. Added actual report RPC to existing SIGINT/inflight-callback lifetime regression. N13.1+8auditPASS; contact/exit/runner/process72PASS39.09s. Freeze runtime for one new actual Gazebo G1-C1 first-failure-stop comparison. Model executor/G1/default/reference/physics/limits unchanged; threaddiagnosticsfalse, original cheap RAW/process witness retained. No source-unchanged engine retry; no actual physical success claim from syntheticCPU.

Actual rootad97fa29: NOENGINE/validation_exitnull. Convergence112samplesPASS; original150s recorder completed, cross-clock gate FAIL before continuous-assessment/engine. First original response rawbracket869.8855ms; ratioRAW[.985654478,1.000157171] crosses1.0 but uncertainty extends beyond original±1%, so not evidence of actual8.3%drift. Rootrestoredtrue/pendingfalse/foregroundclosedtrue/final_related[] verified. Original7rows/FAIL untouched; no physical success/consecutive count. Corrected CURRENT_TASK_STATE active fields toclosed.

QPC handshake root cause: READY emitted before first ConvertTo-Json response initialization. Read-only host ABBA qpc-ready-cca7aa1c: newfunction cold first89.2976/106.9004ms vs initializedREADY30.3781/7.4482ms; subsequent0.36–.85ms; all4serversnormalexit0. This comparison is NOT rate/engine acceptance. Minimal harness change initializes SAME serializer response path beforeREADY, frozen helper/provenance included. Original7fixed samples/10sspacing/60s crossclock±1% and original150s/40squiet/1ms/actual±.1% stay unchanged; no selection by RTT, no fallback/retry/clockwrites. ExistingactualFAIL is RED for readiness defect. Target real host RPC/normalexit and harness safety regressions next, then one new diagnostic (runtime unchanged, measurement protocol changed).

QPC READY protocol and existing engine-plan/lease/foreground/convergence safety GREEN:47PASS1.07s, task8-qpc-ready-safety-green.log (--noconftest, stdlib/host test only). Real ownedhost QPC originalfrequency/strictincreasing/normalexit and initialization-beforeREADY checked. Runtime sources unchanged since contactboundary72PASS; freeze for new onepair originalcriteria, no physics/safety changes. Previous ad97 failure counted as NOENGINE, not a robot failed/successful repetition.

Root86f2bc1c CLOSED verifiedrestoredtrue/pendingfalse/foregroundclosedtrue/final_related[]. WarmREADY crossclockRAW[.9999547659,1.0000728230]PASS; continuous150PASS; preflight1955samples/nojumpPASS; N8.16+8auditPASS;startup19PASS29.33s. G1ed0a4f30 PASS25/source173manifestc6bce035d4f6b6254e751183906203227dfc5f3dfa8282c29aaf307bc682ee58; ZIP2373783B SHA9a71b8201203121e3738f17a0016ce8957070ed119582e097afba1f0ff7d7d45. C1ac904b6c FAIL nativeQPstatus4=MAXIMAL_NUMBER_OF_ITERATIONS32, solver250.3uswall/250.2usCPU, NOT10ms deadline;61submitted60completed1failed; pendingfalse/ACK/reap/exit0/allhandlesclosed; normalruntime/engine true; sensorfreshness/stand10/controlclock true; zero completedfootcycles. OriginalFAIL retained, notfullG2 or3consecutive. Contactadapterboundedreport collected; maxgap536ms belongs veryearlybootstrap, not faultcausality. No furtherengine yet.

Important falsification: exported load_transfer_observation.numeric_input standalone replay task8-qp-presolve-red unexpectedlyPASS1/17deselected10.11s. Do NOT call this RED or solverfix. Traced early collector error copying previous successful numeric input/model while overwriting current failed attempt/worker. Thus recorded input is previousjob60, not failed61. Derivedfixture scope corrected; originalraw/report untouched. A strict-box-presolve proposal was drafted but immediately removed from runtime/CMake before anybuild; retained T/box_presolve.unselected.hpp and test_box_presolve.unselected.cpp only. NO numerical algorithm/tolerance/iteration/constraint change adopted. New diagnostic binding test task8-early-failed-input-red1FAIL14.43s proves stale60 vs61. Minimal errorreport rewrite + explicit input/reply jobID implemented; actualchild/earlyowner/complete regressions running. Need exact failed input before solver redesign, not parameter sweeps.

Failed-input binding build N10.3+8auditPASS. First GREEN1FAIL37PASS54.86s due NEW assertion comparing original NumPy arrays to JSON-owned lists with dict== (ambiguous array truth). Fixed only new test's representation comparison via independent JSON normalization; original robot criteria/runtime unchanged. Next repeat affected tests only, no rebuild required for test-only correction. Production QP unchanged and no presolve installed.

Failed-input binding GREEN2:70PASS42.66s; N10.3+8auditPASS; new stdlib export binding guard1unittestPASS0.000s. Retains actualfailedreplyID/lastinputID/input/context, refuses old mixed60/61 report export. Early error report replaces prior validatedmodel instead of inheriting it; no changes to math/32iter/10ms/40ms/200ms/132primal checks/reference/physics. Freeze new runtime for one actual G1-C1 to collect trustworthy failedjob before any numerical redesign. Previousac904 raw failure remains, derivedrecorded-input fixture explicitly notfailed61. No actualsuccess claim/model switch/subagents.

Root07bdad22 CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/final_related[]. Convergence174samplesPASS; crossclockRAW[.9999520226,1.0000698264]PASS;150witnessPASS;preflight1958samplesPASS;N9.71+8auditPASS;startup19PASS28.22s. G1954ebc67 FAIL original10s calibration, STANDcandidate8.953990313wall/6.544ROS (~.73085RTF),1.046009687s left for original1smeasuredsettle. Actual lift/contact/limits/freshnessPASS; runtime/engine acceptanceFAIL due measuredSTOPunconfirmed. Parentreaped/forcedfalse/residual[] do not replace normal exit acceptance. C1NOTSTARTED. Source173manifest401aa3d72c5b7d7fa0e773363ce0a59fc873975712b94e2c9ac4090630393539; ZIP2425547B SHAbbf8761a582b43ccd460c348ca19197462c5131b06ab04dfdea648e790c4482a. No same-source retry. Need reduce scheduling/dispatch overhead with evidence rather than shortening criteria or selecting successful runs. Inactive actual controller2ms synthetic callback ABBA model-dispatch comparison running, no engine/motors/systemchange; ingress heldconstantwaitset for both variants.

User resumed native task again. Closed-owned actual model synthetic2ms ABBA comparison85416b3b: Draining2worker.28246/.29433core vsdirectSingle.26084/.26036 (~9.6%lowerCPU); all4trials200callbacks/one modelTID/0commands/inactive/ingressjoined/errornull. Ingress heldsamewaitset; don't add this percentage to separate36%ingress comparison. OfficialROS callback-group source reviewed; Jazzy webaccessdenied, useofficialros2_documentation GitHub primary. Existing sole model group alreadyMutuallyExclusive, ingressseparate; redundant pool dispatch produces no parallel model work. Implement directSingle + Events receiver for explicitGZrelay G1/G2 only, retain native/MJ/cadence/reference/physical/safety/default behavior. GZ owner RED1FAIL15.35s, N10.6+8auditPASS; expandedDDSblockedmodel/owner/clock/lifecycle/normalshutdown regressioninprogress10624. WSL emitted externalunknown boot.appendWindowsPath configwarning; no externalconfig/systemchange bythisagent, commandcontinues. User13.4file40723B preserved.

GZ direct-owner GREEN1:89PASS/1FAIL56.95s, actual_owner_decision_cost[gazebo-True] rejected FIRSTactivation guard:ros_age. Trace rig publisher runs on SAME thread as newlydirect model; native worker configure blocks that synthetic producer, then CrawlRig publishes guard with previous capture before super.pump updates clock. Existing runtime age check correctly rejects. Original physical producer is separateprocess. Correct only this decision-cost test setup to pump fresh synthetic captures .1s AFTER configure BEFORE firstactivation (as existing lifecycle tests already do); no retry/reactivation/age bound change/runtime bypass. Repeat affected regression, preserve originalFAIL log.

GZdirect owner GREEN2:101PASS63.99s including bothengine/G1G2 blockedmodel independent clock/contacts/guard/commandDDS, singleton ownership, callbackthread/manifest, modelcadence/lifecycle/shutdown. N10.6+8auditPASS fromsame runtime. Testonly refresh afterconfigure fixed co-located synthetic producer; no runtime/criteria change after build. Native/default/MJ paths retained; source freeze for one new GZ G1→C1 diagnostic, no competing work. OriginalfailedG1/C1s preserved; no success selection/consecutive count or mathematical redesign claimed. Guide/REUSE updated with boundeddiagnostics/jobID Mermaid principle.

Root7fd8724b CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[]; boot159d3734. Convergence76PASS; crossclockRAW[.9999531325,1.0003294383]PASS;150witnessPASS; N10.1+8auditPASS;preflight1966PASS;startup19PASS35.94s. G19d8f83b8PASS25; source173manifest453af6c851307899678882964e994413b0d6614202f7e517577e8a8fb8762a2f; ZIP2384094B SHA25f1d3e1c11a627cfb904eb789d88983b95c420b147cd9cba99a65e047fbd22c. C14d26fb83 FAIL nativeQP32iters atjob72/71complete, solver279.4uswall/278.7usCPU, freshness/stand10/normalruntime/engine true; ACK/reap/handlesalltrue/exit0/pendingfalse/forcedfalse; zerofootcycles. Crucially numeric_input_job_id==worker.last_input_id==last_reply.id==72 andokfalse. Exportguardvalidated fixture50750B SHA06abd46dfae57fa4add4fffc51b1c92dbc3acaf97550c25d50a2a53f524b6f26. Standalone existingkernel RED task8-job72-qp-red1FAIL19.25s reproducessame4. Now reintroduce previouslyunselected strict-box implication proposal as ONE controlled hypothesis; keep12vars/objective/box/original132postchecks/32iters/10ms/tolerance, one solve/no fallback/retry. C++4functional proof tests+exactfixture+legacyproof regressions pending. BuildI/S/N16092 active, NO engine. Earlierunselectedstage preserved; no mathematicalsuccessclaimyet.

Strict-box hypothesis I/S/Nbuild1m50+8auditPASS; CPP4functionalPASS8ms. Initial direct command guard exited beforetest/no logfile; actualexistinghelper confirmedBUILD_TESTINGON/binary and ran4tests. Helper reconfiguredCMake53.1s although justbuilt; prefer alreadybuilttarget for futureunchanged tests. Exactjob72 test task8-job72-presolve-green FAIL1/18deselected19.09s sameMAX32. Hypothesis partialredundancy removal is NOT sufficient; no actualengine rerun/no solutionclaim. Separate uninstalled debuglibrary diagnostic77925 captures originalmatrix/objective/bounds/keptrows/failedprimal before independent OFFLINE SLSQP512 oracle (explicitlyNOT runtime iteration/time acceptance). Need classify exactconstraint residual/optimality/degeneracy, not sweep engines or silentlyraise32. Originalnative/vendor sourcesnotmodified by diagnostic; own candidate source unaccepted.

Offline diagnosticbc0ea286 (uninstalleddebug.so/source+method+compilercommand/hashes preserved): after102 box-implied rows pruned,30retained nativeMAX32/counter33, originalresidual2.0 dueRLnormalized(-1,-1,-1); NOT tinyroundingprimal. Nativeobjective-4.90573 islower onlybecauseinfeasible. Independent OFFLINE SLSQP512cap converged8iters, residual3.55e-15/objective-4.8998059087. This oracle isNOT runtime32/10ms acceptance. Root redundant coordinatecube bounds vsunitL1facet representation can consume pivots; remove ONLY exact+/-1 solverbounds already implied by ALL32 canonicalL1facets, validatedagainstactualmatrix. Keep fixed/nonunit/envelope bounds, restoreALL32facets mandatory beforestrict-rowprune toavoidcircularproof; postvalidateoriginal132+box/geometry/servo andoneQP/32/10ms/toleranceunchanged. Add2CPPproofcases incl exteriorgrid and missingfacetfailsclosed. I/S/Nbuild29703 pending; no engines; no acceptingpartialprimal or retry/maxlimitincrease.

EquivalentL1/box I/S/N1m59+8auditPASS. Direct alreadybuiltCPP6PASS0ms XML task8-l1-box-proof.xml (no53sreconfigure). Canonicalfacets proof/outsidegrid/strictbox/fixedbounds/missingfacet/nonfinite allPASS. Exactjob72 task8-job72-l1-presolve-green1PASS15.24s/18deselected: same32cap/10ms + independentoriginalprimal/force/torque/vector/28geometry proof. Still notphysicalacceptance. Full affectednativeXYZ/legacyoracles/complete/terminalobjective/asyncowner/actualchild/lifetime/fault/crawl regressions session pending. Preserve earlier strictrowFAIL andoriginalbaseline; no engineuntilrelatedGREEN/audit/freeze. Newsolver keepsALL32 L1facets andonlyomitscoordinateexact+/-1alreadyimpliedbyL, otherboundsremain; postchecksoriginal132+box unchanged. No externalvendor edits/retry/criteria change.

Affected mathematical/lifecycle regression task8-l1-presolve-regression-green99PASS107.48s: nativeXYZ legacyindependentoracles/jitter/complete/exactjob72/terminalobjective/actualnumericalchild/asyncsoleowner/lateresult/inputID/faultrecovery/coupledcontact/crawl lifecycle. Source unchanged afterI/S/N1m59+8audit; CPP6PASS, job72original32/10ms/primalproofPASS. Freeze actualGZ G1-C1, no competing work. No claimingphysical lift/fullG2/3consecutive/sectioncompletion; no force/timing/default/vendorchanges.

Rootc73353c6 CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[]; boot2f69e310. Convergence89PASS/crossclockRAW[.999957748,1.000076851]PASS/150witnessPASS/preflight1957PASS/startup19PASS29.57s/N9.02+8auditPASS. G1154db0acPASS25/source175manifest3896bf19d537cbdc62de9b09b786e0fbcb000a8ca037df6dc2a0ce36710afa1b; ZIP2378975B SHA15056a4886635d1677f6d0e2c8b8ea4673938fa65888a61c616e0a1f4f052756. C133573eb6 numeric64/64/fail0 =>numericjobcontractTRUE; FIRSTparent elapsedreference rate FAIL atROS32.546. Validjob64 horizon19.929004ms vsROS18/wall20.105904ms; originfalse(selectedFn1.23172,Fy1.05656>Fn/sqrt2) so shrinkingnotcertified. Normalengine/runtime/ACK/reap/exit0/pendingfalse/handles/restorationPASS, zerofootcycles. KeepFAIL/no nextengine.

Newmature_horizon (explicitGZ G2 asynccoupled only): one unchanged validreply may waituntilbothoriginalclockhorizons mature withinUNCHANGED200ms snapshots/currentmodel/owner/geometry/rate checks. No resubmit/retry/age renewal/reference commit whilewaiting; original6s unloadleasecontinues; stop/fault/phase/resetclear sameboundedslot. Defaultstrict+noinvalidorigin scaling test kept. RED1FAIL23.91s; N15.9+8auditPASS; related55PASS75.60s; exactrealjob64 condition+actualROSscopebinding14PASS38.98s. Parenthorizon fixture49369B SHA8f8d9a2b4dd6255f3b5c7fcd5e0a65262c34c3563767723212f9f570ef6be9e4; sourceIDs64allmatch/oktrue separate from failedQP fixture exportguard. No physicalsuccessclaimyet.



Rootf44eca07 CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[]. G1db9883ec FAIL original10wallsec calibration SWING; SHIFT4.570ROS/9.160509298wall=RTF.49888056; lift5mmnotyet. C1NOTSTARTED. Source175manifestf03259ae7bf1ab2b0cfc612fd6b266fe395b618435f07685af07a2661d14b326; ZIP2471605B SHAe2d6d46bf9622f6871fe549b9493a70153cbc6c2991cf9597e04b1815f41b1aa. Originalruntime/engine acceptanceFAIL due measuredSTOPunconfirmed, parentreaped/forcedfalse/residual[] separate. Closedphase comparison82c6d4f3 samephysical/modelhash vsG1154PASS:RTF.95373->.49888, observerCPU90/99us->167/197us; runtimeMONO/RAW~3ppm healthy. No assertingclock/llvmpipe/thermal/QoS causality. NativeCPUIntel1185G7 nonhybrid;ACconnected; current noquota/memorypressure. New read-only hostPDH2s witness after initial fullToolhelp8-13msexpense rejectedprecheck/noengine. QoSquerydenied5/noadminfallback; moveToolhelp BEFOREengineonly. PurePDH10samplesmax.980ms; CPUclock0quantized NOTzeroactualcost. Selfcheck634d8e53 PASS, previousFAILEDselfcheckpreserved. Runtimeunchanged; nextsingleactualdiagnostic addshostwitness to discriminate throughput, notunchangedblindacceptanceretry.


Rootac1edd56 CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[]. Host296a0bdd read-onlyPDH280samples2s/parentreaped/observerclosed; maxwall2.0048ms; processCPU15.625msquantizationnotzeroactualcost. G10196fc1dPASS25. Phasee03a SHIFT4.680ROS/4.939462146wall=RTF.94747; Windowsperf88.31/94.57/94.85%nominal,ACtrue. No comparablehistoricalfailedhostwitness, soNOthermal/QoScausality;QoSreadaccessdenied5/nofallback. Samefrozen175sourcef03259ae. C148d02b49FAILjob130;129complete1failed;normalruntime/engine/ACK/reap/restorationPASS. OneFLfootactualunload/lift19.713mm/returncomplete;remaining3incomplete =>C1FAIL/fullG2notrun. ExactID130fixture50755B SHA70d458bba3e25223af2d20644523fbf54e1d16acbbab48f85a1b067fc1ce0e4f. StandaloneRED1FAIL18.68s. Uninstalleddiag2c2471e8 MAX32counter33/residual.644370576; offlineSLSQP30iters residual4.57e-13/objective22.68447 (NOT runtime32/10ms acceptance). Retained33rows includes8selectedL1facets duplicateonceXYfixed0;nativeprimal selectedZ-1.64437 invalid. New single equivalent presolve hypothesis:exactfixedcoordinate substitution pluszero-rowfeasibility/singletonrowbounds;selectedXYremoved,8selectedL1 becomeZbounds;original12vector/132+box/primal/28geometry/32iter/10ms proofs unchanged. PrimaryPlaCo/MathWorksreferencesreviewed;no vendorcopy/regularizationchange/warmstart/retry. CPP3equivalence/failclosedtests +exact72/130regression neededbeforeactual.


Fixedcoordinate I/S/N2m24+8auditPASS/CPP9PASS1ms; exact72PASS but130stillFAILMAX32 =>1PASS1FAIL18.90s, noengine. Vendorresetreview ruledout suspectedfirstgeneralindexissue (resetsetsindex0); no vendorbugclaim/edit. FixedsourcechooseConstraint selectsall simpleboundsfirst thenrawunscaledgeneralviolation. Offline7565 controlledthreevariantsonexactoriginal72/130:fixed20/MAX32,allgeneral26/MAX32,allgeneral+Hmetric16/16; originalobjective-4.89980590868478/22.6844709071878 andfull132+boxresidual~3.49e-14/4.84e-13matchofflineoracle. LastvariantimplementedasoneQP(no runtimefallback/retry) inownhelper;H/g unchanged,positive row scaling only,oldpostproof/alllimitsunchanged. CPPmetricunit-grid/failclosed tests+independentfull12objectiveanchors added; build66171pending. NeedGREENbeforeactual;no numerical/physicalcompletionclaim.


Metric I/S/N2m8+8auditPASS;alreadybuiltCPP11PASS1ms XMLtask8-metric-proof.xml. Exactfailed72/130fullcompletekernel2PASS18.19s original32/10ms, independentoriginal132/box/force/torque/28geometry/nonlinearservo AND full12objectiveoracleanchors. This is math/lifetime prerequisite NOTactualC1success. Affected12file regression7618running;noengine/systemchange. User13.4file40723Bpreserved;oldchapter/sourcesgitdiffempty. Get-Volumeread-onlyaccessdenied;noelevationattempted.


Metricaffectedregression104PASS114.23s (12files:independentnativeoracle/complete/exact72+130/actualchild/terminalforce/asyncsingleowner/earlycollect/lateRPC/faultrecovery/coupledphysicalinterface/lifecycle/maturity/loadprocess). RuntimeunchangedafterI/S/N2m8+8audit/CPP11/exact2;freezeactualGZ G1-C1. Original10s/32/10ms/40ms/200ms/forces/geometry/physicsallunchanged. No finalmatrix/consecutive/sectioncompletionclaim.


Roota9c599e5 CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[];NOengine. Clockconvergence149PASS/crossclockPASS/150witnessPASS; N16.4s;8auditFAIL REUSE_MANIFEST.md: I edited sensorREUSEafterinstallation, so source vsinstalldescriptor differed. Failurepreserved/acknowledged;notrobotfailure. Sensor--cmake-force-configure/installrefresh1m11+8auditPASS. Pairaudit comparison confirmsALLsensorlibraryELFs+navigationPythonbytesidentical;ONLYREUSEmanifestentrychanged. Thus104runtime tests retained/no repeat. Host42cbf63e177boundedread-onlysamples/parentreaped. Wrapper nowruns SAME8auditor beforeanyservicelease/longclock,retainsoriginalinaudit too. No criteria removal or robotruntimechange. Nextactual afterearlyaudit; not countingblockedrun asenginepass/fail.


Rooted850884 CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[];prelease8auditPASS/inauditPASS/convergence110PASS/crossclockPASS/150PASS/startup19PASS31.77s. G13f2b2183FAIL10wallsec TOUCHDOWN,actual5mmliftPASS;runtime/engineacceptanceFAIL(measuredSTOPnotconfirmed),parentreaped/forcedfalse/residual[]separate;C1NOTSTARTED,newmetricactualstillunverified. Closedhostcomparison7d4ce1b9 samephysics/modelhash:PASS0196 SHIFT4.68ROS/4.93946wall(.94747),FAIL3f2SHIFT4.592ROS/7.37984wall(.62224);hostperf88-95vs84-89/utility65-74vs76-85. No inferenceactual%busy/thermal/QoS/competingprocess fromproxyalone. Newread-onlyPDHdirectbusy+publicprocessCPUobserver2s rejected06df costmean6.25ms/max7.86ms; separatequery10sfirst451 failedarbitrarymax10msat10.1969ms. Correctdiagnosticbudgetbasedmeanwall/10s<=.001core/maxquery50ms;robot10ms/anyrequiredcriteriaUNCHANGED. Sparsepublicprocessnames/CPUonly,noQoSdeniedfieldfallback/admin/processstops. NeedactualhostvsVMattribution,notpower/affinityspeculation.


2026-11-02 resume: rootfbfb6b7e CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[]. G15f4b235aPASS; C148f565a9FAILactualjob19DISPATCH40ms,notQP. Submit561028466027/computed561052928627(+24.4626ms)/poll561067600826(+39.134799ms)/fullreceived561068729226(+40.263199ms). pollsourceconfirmslast_attemptcopiedfromSAMEreplybeforedeadlinecheck =>.588mscompletekernel;18completed1discarded0numericfailed/pendingfalse,normalnumerical/runtime/engineclose. Nofootcycle. SourceManifestSHA7de6334fe6af08fe157910f0e82e9026cbdfeaa45becf63cf6d00b138bac4132; installSHA0ad24b1ae4ba21a87e196140e18611de1cc208f367e6f072ee1336cfe1e6f5ac. job19-transport-2ebde151capturesexacttimestamps+attempt+hosthashes. PublicPDHhostnearC1busy84-91%,VM4.13-4.29logicalcores/Chrome~1;doNOTclaimcausalityorstopforeignwork. Read-onlycostthrottlevalidated10sprocessquerymean7.6351mswall(.076351%onecore),max10.3645msvs50msobserverlatencybudget;robot10msUNCHANGED. Structuredfixnowseparatecomplete-receiptfrom50Hzmodelconsumption,explicitGZG2only;1slot/noROSorcommands/actualcompleteframetime;joinbeforeSTOPACK/streamownertransfer. Existingdocupdated(notnewrepeatedplan),desiredtestRED6776pending,no productioncodewrittenyet.


EventreceiptRED1FAIL20.32s(newselectedmodeabsent); N10.6+8auditPASS;11functionalGREEN14.55s:actualchildtimelycomplete40ms/decision45msfirststampretained;legacynegativecontrol;latecompleteearlycomputedreject;200msconsumptionreject;partialframe/noearlystamp/one-slot/nooverwrite/EOF/partialstopstreamtransfer;outstandingSTOP/join/ACK/threehandles/reap;asynccoupledscopeguard. No numericalQPchange;singlecoldmetriclibraryfrom104PASSkept. NewmodeexplicitGazeboG2only;readonlyRXthread neverROS/model/command. Current11fileRPC/late/fault/scopeROS/lifecycle/shutdownregressionrunning;noenginebeforeGREEN/freeze.


Eventreceipt11-filecohort firstFAIL1/1PASS62.44s inlegacyheight defaultmodelpoll test_one_outstanding...:childkerneloriginal10msbudget. EventmodewasNOTselected. Addedonlytesthelperfailureattemptdiagnostics(no runtimechange); isolatedsamecasePASS1/9.13s, earlierFAILremainsintermittentUNRESOLVEDnotfixed. Old5f4frozenZIPworker_mainAST==currenthash600153bff12a167796c001639042823cd9d64decc66ce1f94627e86507abc8a9; heightkernelunchanged. Remainingunexecutedcohortcontinuesoncewithalreadydiagnosedcaseexcluded;finalfullmatrixMUSTINCLUDEALLtestsandthisFAILnotcountedaspass. Neednewscope/lifetimecoveragebeforeactual;noeventphysicalsuccessclaim.


Eventreceiptremainingcohort84PASS94.16s includesactualGZG1/G2+MJG1/G2scope,workersingleowner,lateconsumedID/context,originalcurrentmodelhorizon,STOP/fault/lifecycle/normalshutdown. Togetherwithnewfunctional11PASS14.55s andisolatedheight1PASS9.13s thisvalidatesnewpath,butinitiallegacyheight10msFAILstillUNRESOLVED andMUSTremaininfinalalltests;NOTclaimallcohortGREEN. No runtimechangesafterN10.6+8audit; freezeoneactualG1-C1 diagnostics (notfinalmatrix/consecutivecount). Defaultcheap2sPDHonly; process-arrayattributionalreadydoneandnotneededagain.


Root81e7c44f CLOSED/restoredtrue/pendingfalse/foregroundclosedtrue/residual[]. Prelease+inauditPASS/convergence107PASS/crossclockPASS/150PASS/startup19PASS28.34s. G102c60438PASS. C159873b32numerical57/57/0discard/0failed, eventreceiver40mscontractTRUE; job57submit8101809083358/complete8101810154458/received8101814877857(+5.794499ms)/poll8101823293956/consumed8101823804756. Parent57referenceboundsFAIL. Normalnumeric/runtime/engineTRUE, RXjoined/slotempty/ACK/reap/3handles/exit0/pendingfalse/forcedfalse/errorEMPTYallverified; zerofootcycles. SourceSHAb79ce39add982d33c6206969cf69a27d7a37e3bb58f62034c1f0b561d85d0cf5 installSHAc403001fc0e959a67e88e1697c6f17a097c1d0c340cca092447ac64f1406be4d. Exactsuccessinput57+contextguardexport native_5987_parent_bounds SHA56a7fe61eb589a2da4671e11f4c8cd10b963fb40966a2700bc80a4ae66502053. Standalonecb727986 allparentpredicatespassEXCEPTselectedFLZ=-5.298264602323201e-22m<0. DesiredstrictparentRED1FAIL15.70s. FixcandidatecanonicalizesONLYoldbox1e-9normalizedroundofftoexactbounds thenrechecksALLoriginal132rowresidual1e-7 BEFOREforce/torque/servo/28geometry/reply. Parent>=0unchanged;significantboxviolations/coupledrowviolationsstillFAIL. CPP3proofcases+actual57strict0+parenttinynegativeguardtest; build6623pending. No directiontolerancerelaxation/physicalclippingatapplication/extraQP/retry/maxiteration/timechange.


Originalprimal I/S/N1m49+8auditPASS (sensorREUSEupdatedBEFOREbuild). CPP14PASS2ms;exact57hard>=0 +72/130originalobjective/32/10ms +parenttinynegativeREJECTION8PASS13.93s. Affected6fileXYZ/complete/actualchild/terminalforce/eventreceipts/parent59PASS44.50s. RXcodeunchangedfrom11+84GREEN, no duplicatewholeIPC/mathmatrix. Originalheightintermittent1FAILstillrecorded;isolated1PASSnotfixclaim/finalalltestsMUSTinclude. FreezeoneactualG1-C1 fornewroundoffphysicaleffect; no originalthresholdremoved/loosened, no runtimefallback/additionalQP/physicalmodelchange.

2026-11-02 resume: root e12b7875 restored/foreground closed/residual[]; G1 779b5286 PASS; C1 1a62bcc3 job121 nonlinear servo FAIL after FL lift-return. Actual source/input binding fixture121 ba8708696b5d5488c495f87aadfe0e2ce2e1544ec6b268381854a133e8ac70e0. RED1FAIL15.81s; offline1688e330 linear -30 vs exact -30.00001789593626Nm, FK mismatch~6.42e-17m. New inner servo remainder certificate retains original limits/checks. Build1m52+8audit PASS; CPP17 PASS2ms task8-inverse-remainder-cpp.xml; exact22 PASS16.69s task8-inverse-remainder-exact.log. Related cohort20414 pending; no actual engine success claimed.

Freeze inverse-remainder: task8-inverse-remainder-related38PASS36.76s. One fixed-source actualG1-C1 next, no acceptance criteria changed. Prior legacyheight budget failure remains open.

Actual rootae53a6b0: read-only convergence137samplesPASS after transient. Original150s/crossclock/preflight+19startupPASS. G11e1a438cPASS;C1dbdfa89aFAIL after FL/RR full lift-return, numeric325submitted323complete2discard0failed, original325oktrue. CurrentparentservoFAIL(-30.016829Nm) due10ms newer q vs original-29.997881Nm. Original fullnormalclose/RXjoin/ACK/handles/reap+engine/runtimePASS; rootrestoredtrue/pendingfalse/foregroundclosedtrue/residual[]. Fixturede23c7c6; diagnostic182de9b6 freshcurrent solvePASS. New same_cycle RED1FAIL1PASS11.81s, Nbuild8.53s+8auditPASS, tests pending. No engine active.

Same-cycle candidate: RED1FAIL1PASS11.81s; firstGREEN4PASS9.39s. Added bounded transaction outcome to shutdown snapshot; N8.02s/8auditPASS. Relatedfirstcohort1FAIL15PASS43.24s at unchangedlegacyPythonspatialresponse10ms; retainednotfixed. Remaining11files79PASS69.27s; wholeparentfile12PASS10.00s with standard1thread environment. No thresholds removed. Fixed actualG1-C1 next.

Same-cycle actual root235a5ec8: convergence115PASS/crossclock150/preflight/19startup27.75sPASS. G17264d7d5PASS. C1ab85a9a6FL/RRcompleted but job264 QPMAD infeasible, transaction1.1533ms,263complete/0discard/1failed. Originalfailure kept; no retry. Normalnumeric/RXjoin/empty/STOPACK/handles/reap+engine/runtimePASS; rootrestoredtrue/pendingfalse/foregroundclosedtrue/residual[]. Exactfailed264 fixture50751B SHA19cc4abd30210422c4aaba23c8f1d6fd2e97cdde7658f9ae35b2400d5f658b87. OfflineFarkas diagnostic next; no engine active.

Closed264 diagnostic e19a7f50: independentHiGHS infeasible; Farkas4rows FLcalfservo-/stepL1/upperZ, Aty5.55e-17/bty-1. No iterationincrease can solve originallocal conflict. Window50ec6795 proves40-60ms bodymotion-ineligible intervals; source gatesallloadfeedback onsettled. Counterfactualmaintenance075b380d first3selectedXYZ0+measuredforcegoal andnextnormalPASS originalconstraints; NOTphysicalsuccess. MaintenanceRED initiallyfixturemissing_offset_start1FAIL14.87s; correctedREDv21FAIL2PASS13.27s desiredmissingfeedback. Scope samecycle/unloadSHIFTonly, fullfuture+settle stillneededfor100msdwell. N9.37s+8auditPASS; newchecks pending.

Maintenance validation: firstGREEN1FAIL5PASS17.97s was fakefixtureclock vs realage mismatch, correctedonlytestclock; originalage retained. GREENv2 new10PASS15.50s. Related14files108PASS101.82s; addedfull-future-release-negative1PASS10.97s. N9.37s/8auditPASS, no runtimechange afterbuild. Fixturemaintenance68717B SHA46c7eb22cd90e5dccd68143b1fae69eeb38fa373c33a50e40dbbf34d0e408ec5. ActualG1-C1 next; no engine currently active.

Handoff2026-11-02: root5597f39f CLOSEDrestoredtrue/pendingfalse/foregroundclosedtrue/residual[]. G14a209b11PASS; C1d50469aaFAIL267infeasible afterFL/RR,266complete0discard1failed,2.318899ms; numeric/RX/ACK/handles/reap/engine/runtime normalPASS. Latestfixture799e3b0b. Plantconsistency62719+0d186 offline: Jgravity/contact-7.6115Nm vs ForceCmd-30, static500samples meanabs20.02994command/5.20617projected, qdmax.000142. Wrenchprojection is NOT actuatorforce; commandapplication/physicsmeaning remains unproven. OfficialgzTestFixtureAPI checked only, no minimalphysicsprobe built orrun. User requested newwindowhandoff: Ch13/docs/HANDOFF_SECTION_13_5_2026_11_02_KO.md. No engine/test/backgroundowned process active; no commit/push.


## 2026-11-02 후속: 최소 물리 시험과 암시적 감쇠·접촉 모델 불일치

최신 C1 실패267 이후 전체 로봇을 재실행하지 않았다. 독립 `force-semantics-0e189460`은1Nm/2ms/관성0.1의 매step/매5step에서 Δqd2.0/0.4rad/s로 PASS했다. 기존2ms이벤트60표본에서도write시각58개가2ms/2개4ms차이라 전주기미호출로 단정하지 않는다. `contact-force-3563b9ac`의 같은1Nm 매step/관성0.01/고정구면접촉에서 native damping0 대10.95445만 바꾸면 정지속도≈0인데 전달렌치1.0→0.31339281Nm, 접촉Fz12.9774→4.0672N이다. 세최소물리실행의각조건정상종료/잔여[]이며 서비스/시계/외부설치변경은없다.

원본실패267을DART공개API로오프라인비교한 `implicit-damping-comparison-bd4be4a1`은 `u=g−JᵀF+Dv−hD M⁻¹JᵀF`의정상순가속도가정에서FLcalf−30.0009629Nm를예측한다(실제명령−30Nm).12관절최대잔차는기존식22.61547→0.0041273Nm다.15.2101kg질량일치·M SPD·선형해residual4.29e−14를확인했다. 최초DartLoader기본관성17.2101kg결과와경로전달준비오류도성공으로세지않고보존한다.6ms관측차이·속도편향/가속도가정이남으므로실제폐루프성공은아니다.

원인은단순4배보정이나수신기한이아니라, 현재독립발spring응답에서빠진전체관성/암시적감쇠/접촉충격량관계로좁혀졌다. 런타임수정은아직없다. 다음은원래물리·native damper·게인·토크cap을유지한전체결합응답의독립검증이다. 상세·정확한UUID·공식근거·보존은 `SECTION_13_5_FORCE_APPLICATION_DIAGNOSIS_KO.md`를읽는다. 기존maintenance·same-cycle 실패와C1/G2미완료상태는그대로다.


2026-11-02: User-requested G1/C1 repetition analysis and primary-source research saved in Ch13/docs/SECTION_13_5_REPEAT_ANALYSIS_RESEARCH_KO.md. Repetition includes valid regression checks and symptom-driven integration loops; pointwise torque mapping is not force-response derivative validation. No new robot execution or runtime changes during this research. C1/G2 acceptance remains incomplete.


2026-11-02 user-directed remote sync: original17929paths in9normalpushcommits, remoteSHA4ac5e623 verified. Protected13.4doc unchanged/excluded. Bookpolicy now20wallsec fixed calibration lease, eachengine1cycle+1reverse finaldemonstration; safety retained. RED1FAIL24.80s/new11PASS18.45s/related82PASS107.96s/N21.8s+8auditPASS. Independent mass/contact oracle f6c11c32 matchesDART1.421e-14Nm,15.2101kg; currentposeFR/RRnecessarytripodsfeasible but actualforce-response/pathnotvalidated. Runtimeforce-responsemodelunchanged.
