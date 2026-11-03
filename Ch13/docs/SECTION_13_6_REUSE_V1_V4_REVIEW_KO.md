# 13.6 v1~v4 변경·반복 오류 검토

2026-11-03 KST. 사용자 요청에 따른 **저장 증거·소스 비교**다. 새 엔진·빌드·물리 시험은 실행하지 않았다. 진행 중이던 v4 matrix는 이미 정상 종료된 상태였고, 이후 추가 실행·최종 게시 작업은 재개하지 않았다. 별도 잔여 검사도 소유 stack 없음·engine lock free로 PASS였다.

**판정: 반복 오류가 있다. 정상 pick과 실제 취소는 입증됐지만, “오류가 없어 작업을 재개해도 된다”는 상태는 아니다. 특히 시작 단계의 clock/state 동기화 오류가 v4에서도 재발했다.**

## 번호의 의미

여기서 v1~v4는 `section_13_6_reuse*.json`의 **인수 소스 revision**이다. v3는 진단 전용이다. 별도의 제어 profile v1/v2, 물체·카메라 계약 v1~v7과 혼동하지 않는다. 팔 bias 보상·gripper force hold·측면 카메라·한 번의 시각 lift 보정 등은 대부분 인수 v1 이전에 도입됐다. 네 revision 모두 물체20g·마찰0.8·원본 force cap·300ms 관측/100ms 과거TF·실제 상승90mm/유지2sim초 기준을 공유한다.

## 실제 변경 대조

동결 JSON의 파일 목록·hash를 직접 비교했다. 삭제된 실행 입력은 없고, 외부94자산은 그대로다. 전체 경로별 차이는 [기계 판독 목록](../evidence/section_13_6_reuse/VERSION_DELTA_V1_V4.json)에 있다.

| 인수 revision | 변경 목적·실제 변경 | 확인 결과와 한계 |
|---|---|---|
| v1, source229 | 동일 engine lease, 실제6축/gripper action, 모델 bias, MoveIt 장면/계획, 물리 원통·시각 보정, 부모 경유 카메라 경로를 최초 인수 기준으로 묶음 | `4732687c`: 실제 도달/충돌 거절까지 수행했지만 TOTG 끝 구간0.532510ms가2ms 물리 주기보다 짧아 취소 시험 직전에 거절. 전체 FAIL. |
| v2, source230 | `retime.py`: 최소 구간이2.000002ms 이상이 되도록 전체 경로를 먼저 시간 배율 조정. 원본 경로점/C2/속도·가속도/120sim초 한계 유지. 실제 실패 궤적 fixture·회귀 시험 추가. freeze/runner revision 처리 변경 | M3 실제 실행/취소와 정상 pick PASS. 정상 pick 최소100.346mm. 그러나 파지 중 취소 시도 `618613e2`, `f3064562`는 접촉 전에 OBSERVATION_EXPIRED로 중단. 취소 성공으로 세지 않음. |
| 진단 v3, source232 | `gc_timing.py`와 실제 GC callback 시험 추가, platform에 수집 시간 관측 연결. **GC 정책·제어·물리 수치는 변경하지 않음** | `b432a881`도 접근 중 관측 만료. GC65~87ms는 관찰됐지만 마지막 full GC334.33~334.41wall초와 fault342.254wall초가 불일치. GC를 이번 fault 원인으로 확정할 수 없음. |
| v4, source235 | `camera_publisher.py`로 wire 표현 재사용. 기존 renderer process가4개 카메라 토픽의 단일 DDS 발행자. 부모 큰 영상 큐는 보존만 담당. renderer의 전체 촬영/발행 journal을 정상 회수. 기본13.5 부모 발행은 유지. 부모를 막는 실제 Renderer/DDS 회귀 시험·계약v7 추가 | 전체165시험 PASS. 정상 pick 최소100.233mm·2.20sim초·양 finger100%, 파지 중 실제 CANCELED 후 낙하0·2.20sim초·양 finger100% PASS. 그러나 `f7919d47`이 팔 시험 전에 FUTURE_SOURCE:base로 시작 실패. |

v1→v2는 파일1개 추가/4개 변경, v2→v3는2개 추가/1개 변경, v3→v4는3개 추가/4개 변경이다. 현재 실행 소스 checkpoint는 `f86cb534`이며, v4 동결 SHA256은 `41be725d863fa7c4fc50c6f90f698a6d8822e25e8f5ef8ba51f881d5a0539f5a`다.

## 반복되는 오류 1: 관측 수명 초과

`OBSERVATION_EXPIRED`/`VISION_EXPIRED`는 개발 기록에서 반복됐다. 저장된 실패 사유에 이 문자열이 명시된 사례만 최소16건이다. 성공한 의도적 관측 손실 주입은 이 수에 포함하지 않았다. 서로 다른 소스/장면의 개발 시도 집계이므로 실패율·신뢰도 통계로 해석하면 안 된다.

초기에는 서로 다른 원인이 섞여 있었다. 동기 궤적 검증의 긴 계산, 혼합 큐 지연, 붉은 로봇 조각의 mask 병합, 실제 팔의 대상 가림, 렌더/전달 지연, 수신 lock 이전에 읽은 판정 시각의 경쟁 조건을 구분했다. 따라서 같은 에러 문구가 같은 단일 원인을 뜻하지 않는다.

다만 가림/fit 거절이 없는 상태에서도 v2 두 사례와 진단v3에서 만료가 재발했다. 마지막에는 source capture→native camera receipt가 약200ms에 이르고 추론·engine 전달을 더하는 동안300ms를 넘는 양상이 확인됐다. GC는 원인으로 확정하지 않았고, 약0.6ms의 개별 ray 계산도175ms spike를 설명하지 못해 batch 최적화를 채택하지 않았다.

v4는 부모 보존을 막으면 기존 경로의 DDS 발행도 막히는 구조를 실제 시험으로 재현한 뒤 그 결합을 제거했다. **완료된 v4 사례에서 예상 밖 관측 만료는 없었고** 긴 정상 pick·파지 중 취소도 통과했다. 그러나 대표 각1회 결과이므로 간헐 지연의 완전 해결·장시간 강건성은 아직 입증하지 않았다.

## 반복되는 오류 2: 시작 단계 clock/state 순서

이 오류는 현재 남아 있다. 이전 `7392cbb4`와 v4 `f7919d47-d466-4a1c-b441-92749a180b4e`에서 같은 계열을 확인했다.

v4 실패의 실제 상태:

- 최상위 오류: `startup/Nav2 readiness deadline`.
- Gateway: `FUTURE_SOURCE:base`.
- Navigation: `INVALID_NAV_INGRESS:future source did not catch up within50wallms`.
- Platform: DISARMED, native engine fault 없음. 단일 clock/base/joints/relay 소유자 count는 각각1.
- 따라서 실제 팔 취소 동작은 시작하지 않았다. **취소 제어기 고장으로 분류할 근거는 없지만 정상 시작을 방해하는 실제 결함/계약 문제가 남아 있다.**

소스의 우선 조사 지점은 `nav_contract.FutureInbox.ready`다. 이 함수는 pending stamp가 현재 clock과 같아져도 먼저 `now - original_receipt > 50ms`를 검사한다. 기존 함수를 이용한 읽기 전용 논리 확인에서도 clock이 pending stamp와 같고 처리 시각이 원본 수신 후51ms이면 예외가 났다.

이는 **처리 지연을 포함한 현재 판정 방식의 특성**을 확인한 것이며 실제 실패 원인 확정은 아니다. 현재 fault 기록에는 원인 pending stamp/receipt, 그것을 따라잡은 clock의 native 최초 receipt, Python 처리 시각을 함께 남기지 않아 다음을 구분할 수 없다.

1. 실제 clock이50ms 안에 따라잡지 못했는지.
2. clock은 기한 안에 native 수신됐지만 relay/실행기 처리가 늦었는지.
3. 별도 clock/state 토픽의 전달 순서나 샘플 유실이 있었는지.

단순히50ms를 늘리거나 재실행이 통과했다는 이유로 해결로 표시하면 안 된다. 먼저 위 경계의 원본 시각·순서를 같은 fault snapshot에 묶어야 한다. 이 부분은 v1~v4 변경 목록에 포함되지 않았으며 카메라 전달 구조 개선과 별개의 미해결 계열이다.

## 현재 시험 결과를 정확히 읽기

| 묶음 | 독립 검사까지 통과 | 실패 |
|---|---|---|
| v2의16개 시나리오 묶음 |15/16|파지 중 취소 주입 전에 관측 만료|
| v4의16개 시나리오 묶음 |15/16|일반 팔 취소 주입 전에 시작 동기화 실패|

v2의 추가 재실행과 진단v3는 위16개 묶음에 끼워 넣어 성공률을 바꾸지 않았다. v4의16개는15행 matrix와 별도 파지 중 취소1건을 합친 수다. 데이터는 [전체 대조 결과](../evidence/section_13_6_reuse/VERSION_AUDIT_V1_V4.json)에 있다.

v4의 정상 pick·파지 중 취소·MoveIt 취소·명령/관측 손실·중복·세션·13.5 기본4개 회귀는 통과했다. 의도적으로 입력을 끊거나 중복 소유자를 만든 시험에서 예상 fault와 실제 정지를 확인한 PASS는 반복 버그로 세지 않았다.

두 인수 묶음의 모든 실행은 RX/renderer/upstream join과 잔여 검사 PASS였고, 측정된 최대 force/cap 비율은1.0이었다. 해당 묶음에서 힘 제한 초과·잔여 엔진·넘어짐이 반복됐다는 증거는 없다. **정상 회수되는 실패와 시나리오 성공은 별개**다.

## 작업 재개 판단

정상 물리 파지와 실제 취소는 입증됐으나 전체 인수를 완료했다고 선언할 수 없다. **“문제가 없으면 재개” 조건을 충족하지 못했으므로 추가 실행·최종 게시를 보류한다.** 다음 개발의 우선순위는 카메라를 다시 무작정 튜닝하는 것이 아니라 시작 단계 clock/state 경계의 원본 수신·처리 순서를 진단해 반복 FUTURE_SOURCE의 원인을 확정하는 것이다. 현재165개 시험과 대표 실행은 강건성 보증으로 확대하지 않는다.
