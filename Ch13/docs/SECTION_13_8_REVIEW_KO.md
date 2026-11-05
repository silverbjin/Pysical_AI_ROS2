# 13.8 자체 검토 기록

단일 작업자 자체 검토이며 독립 검토보다 결함 탐지력이 약하다. 아래는 개발 중 발견 목록으로 완료 판정이 아니다. 사용자의 단일 작업자 지시에 따라 subagent를 사용하지 않는다.

## 실행 전 확인

기존 lease의 fresh watchdog을 추출하고 원본 zero-base/goal/pose 로직을 유지했다. 기존 lease 회귀 PASS. 새 운반은 별도 phase이며 예약하지 않은 goal·contact 상실·원본 관측 만료·busy arm·REVOKED를 거부한다. 원본 정책/물리 파라미터·effort/속도·가속도는 바꾸지 않았다.

## v2 첫 실행 중 정적 재검토: 후속 보완 대상

현재 engine 소스 v2는 변경하지 않는다. 실행 종료 후 아래를 시험으로 확인하고 필요한 수정은 새 동결로 분리한다.

- PLACE의 yaw drift 한도와 LOWER→RELEASE→RETREAT 순서가 단순 allowed-name 검사보다 강하게 제한되는지 확인할 것. 정상 runner는 이 순서로 요청하지만 권한기는 잘못된 요청 순서도 거부해야 한다.
- 사후 운반 판정의 contact force와 support force도 비유한 값을 명시적으로 거부할 것. engine state/actuator cap 검사만으로 모든 사후 로그의 무결성을 대신하지 않는다.
- bag 기록 자식의 정상 close·metadata/message 수와 실제 별도 domain replay를 검증할 것. 코드만으로 bag 실습 완료를 주장하지 않는다.
- 원고의 Level1 floor2m, 공통(3,1)테이블과 개발 fixture를 혼용하지 말 것. 추가 월드의 높이·기하와 기존 정책/팔 도달 가능성부터 검증할 것.
- 고정 source/config·실제 evidence UUID와10회 분모를 연계할 것. 허위 JSON fixture나 모의 CLI를 실제 성공 집계에 섞지 말 것.

## 재개 후 확인 상태

- PLACE yaw drift·LOWER→RELEASE→RETREAT 순서·support 전 개방 금지와 비유한 contact/support 거부는v3 이후 부품 보완 완료. 실제 place는 아직 미인수다.
- owned 귀환 client의 늦은 send 수락/result/cancel ACK 회수는v4 부품 시험 완료. v4 bag12토픽131424메시지 검사와 domain136 실제 reception replay 완료. 전체 비전/Nav2 algorithm replay는 미검증이다.
- v5에서 귀환 goal의z만 설정하고w 기본값을 남긴 오류 발견. v6에서 unit quaternion·실제 pose mismatch 독립 거부 시험 통과. 정적 검토만으로 이 오류를 앞서 찾지 못한 한계를 남긴다.
- v5 가림에는 부분 원통 추정기를 채택하지 않고 v6 opt-in camera mount를 변경했다. 기존 엄격 fit·기본 mount 보존·저장8자세 렌더링 회귀 포함299 PASS. 실제 v6는 matched 관측0으로 이동 전 실패했으므로 카메라 변경의 실제 연속 인수는 아직 없다.
- raw DDS callback/first-receipt 매칭/TF 상태를 별도로 판독할 진단 자료가 부족했다. 읽기 전용 카운터 추가 후 관련46개 시험 PASS. watch­dog/timeout/원본 시각은 변경하지 않는다.
- Level1/2/3·고정 설정10회·최종 배포/복원은 계속 미완료다. 개발 실패를 누락하거나 성능 목표 달성으로 표현하지 않는다.

- v10은 실제 개방까지 도달했으나 전체 FAIL이다. 분리 parent 불일치를 정적 검토에서 놓쳤고 outer 서비스 성공을 과신했다. v11 후보는 실제 설치 API에서 오류 재현 및 사후 장면 검사로 보완한다. 팔 후퇴·후속 유지·전체 종료는 새 물리 실행으로 확인해야 한다.
- 원고 성능 목표는 유지한다. 실제 귀환5.2cm/190.64sim초는 목표 미달이며 fixture 성공과 성능 인수를 분리한다. 개발 버전별 실패를10회 고정 설정 평가로 섞지 않는다.

## v15 단일 연속 인수와 남은 검토

v15 개발 fixture에서 실제pick/transport·detach readback·full Cartesian retreat·post-release hold·worker/14goal/12child/상태writer 회수를확인했다. Windows reader-lock3.115초로발생한advisory 오류3회는제어취소로전파되지않았다. 기본제어/모델/관측수명을바꾸지않고구조상오류를해결했지만한번의선택사례이며반복강건성은미검증이다. 3cm/120초목표미달·원고Level1/2/3·10회미완료를보존한다.

검출의모집단을합의점으로바꾼점은명시적계약변경이다. raw/inlier수치와실제raw 영상은함께보존했다. 전체RMS조건을유지했다고잘못설명하지않도록검토했다. source346·외부94자산·325회귀·실제bag164399/12토픽·모델제외41파일복원PASS를구분한다. 다음floor는static6D IK해를얻었으나충돌/접촉/시야/경로인수전이며기존fixture 성공을옮겨쓰지않는다.

## v22~v24 재개 작업 자체 검토

원문 journal은 현재 상태 json.loads를 유지하고 과거 container 보관만 줄였다. pretty JSON 정규화/legacy/default/작업 예외 후 콜백 제거와 client 회수 시험을 포함해v22전체357 PASS다. 원문보관의 작은 GC 실험과 실제 owner전체GC를 구분했다. v22실제정상종료/9012 heartbeat에서300ms초과0회만으로과거364ms원인해결을주장하지않는다. v22전체trial은carry_height FAIL이며BT SUCCESS로대체하지않았다.

v23설정의실제미적용은소스/설치hash감사만으로탐지할수없었다. 실제GetParameters와엔진없는ROSparser를추가해검증경계를보완했다. v24공식RewrittenYaml재작성은관련13 PASS와실제11.82mm전진1회로확인했다. 첫cold-start FUTURE_SOURCE:base FAIL도별도보존했으므로반복강건성은미확인이다. default0.06/yaw/stateful/속도보존을시험했고원본설정파일은바꾸지않았다.

남은필수범위: 적재귀환π회전에서새정밀도확인,관측/발행cold-start지연의반복강건성,common table/Level2/3와고정10회평가,최종가이드·배포/복원검증. 이검토는13.8완료승인이나독립리뷰가아니다. 원격게시하지않는다.

## Level 2·3 총10회 자체 검토(2026-11-05)

단일 작업자의 자체 검토이며 독립 리뷰가 아니다. v28은 10건의 UUID/source/scenario 일치·worker 완료·실행 전후 잔여 검사를 대조했다. 전체0/10 FAIL과 world9/10·Pick3·BT1을 구분했다. 슬롯4의 lifecycle_manager 강제 종료를 정상 자식 종료로 세지 않았다. 귀환 오차 누락9건을0으로 채워 평균하지 않았다. 원본 판정과v28 고정 소스를 변경하지 않았다.

미해결은 L3의6D 목표 부적합4건, L2의관측수명2건, 운반 안전/health 중단 각1건, 연속완료예의 높이23.360mm·귀환55.231mm·259.912sim초, 시작deadline1건이다. v29는 증거가 확인된XY latch만 최소 변경하고 다른 원인 해결을 주장하지 않는다. 신구 조건을 섞은 성공률이나 새10회 평가로 보고하지 않는다. 실기·일반인식·SLAM 검증이 아니다.