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
