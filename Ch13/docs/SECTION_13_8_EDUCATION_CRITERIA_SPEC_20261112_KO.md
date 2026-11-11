# 완화된 교육용 평가 정책과 실행 계획

2026-11-12 사용자 지시로 원고보다 완화된 기준을 채택한다. 이전의 원고 수치 유지 결정은 새 교육용 평가에 한해 대체한다. 과거 freeze/verdict와 원고 기준은 수정하지 않는다. 단일 작업자로 RED→GREEN→REFACTOR→REVIEW→COMMIT→공개 CI 순서로 구현한다. 성공 인수는 별도다.

## 정책 명세

|항목|book_v1 비교 기준|education_v1 새 기준|
|---|---:|---:|
|10회 성공률|90% 이상|80% 이상|
|평균 정상 임무 시간|120 sim초 이하|600 sim초 이하|
|최종 위치 오차|3cm 미만|10cm 미만|
|측정 최대 roll/pitch|0.1rad 미만|0.15rad 미만|
|평균 CPU|70% 미만|85% 미만|

교육용600초는 기존 느린 native 팔 제한과 장시간 경로를 감안한 실습 예산이다. 공식 문서가 보증하는 로봇 성능 수치가 아니며 달성 여부는 별도 실측한다. 시도 수10회는 유지하고 실패/미실행/자료 누락을 분모에서 빼지 않는다. 교육용 시간·최종 오차는 정상 완료 사례 집합으로 평가해 조기 실패가 평균 시간을 좋게 만들지 않도록 한다. CPU/기울기는 실패 사례를 포함한 유효 측정 전체를 사용하고 성공 사례의 필수 측정은 누락을 허용하지 않는다. 실패 사례의 누락 값은 null로 공개하며 NaN/음수/중복/종료 미회수는 통과시키지 않는다.

물리적 파지·접촉 유지·지지 후 개방·실제 놓기·충돌 없음·원본 capture300ms/TF100ms·명령 소유권·cancel/회수는 그대로다. 이번 정책은 성능 집계 기준의 완화이며, 이미 알려진 충돌 경로를 실행할 권한이 아니다. 기존 높이20mm 등 추가 물리 witness도 이번 성능 정책만으로 제거하지 않는다. 내부 Nav2 허용치를 함께 바꾸는 반복 튜닝은 하지 않는다.

기존 assessor의 기본 호출은 book_v1로 남겨 과거 도구의 의미를 보존한다. 새 batch 준비 CLI의 기본 정책은 education_v1이며 새 v2 plan에 프로필/수치를 고정한다. 단일 mission은 평가 정책을 trial에 명시한다. v1 plan 실행은 명시적으로 book_v1을 전달한다. 과거 trial을 원본 수정 없이 새 정책으로 비교하는 경우 별도 출력과 retrospective 표기를 사용한다.

## 근거와 한계

공식 Nav2 1.3.13 [SimpleGoalChecker 구현](https://github.com/ros-navigation/navigation2/blob/1.3.13/nav2_controller/plugins/simple_goal_checker.cpp)은 내부 XY/yaw/상태 유지 옵션을 구분한다. 애플리케이션 성능 목표와 안전 동작 기준을 같은 숫자로 취급할 근거가 없다. 기존 저장소의 immutable make_plan/canonical 검증과 fail-closed assessor 패턴을 재사용하고 새 프레임워크는 추가하지 않는다. 정책 수치는 사용자가 위임한 교육용 설계 선택이며 공식 reference의 성능 보증으로 표현하지 않는다.

현재 Level3는 MoveIt ValidateSolution의 식탁 충돌 계획 거절이다. 성능 기준 완화만으로 이 사례가 성공이 되지 않는다. 변경이 없는 engine 재실행이나 새10회 평가로 이를 덮지 않는다.

## 실행 계획

1. criteria.py에 읽기 전용 named 정책과 조회/직렬화 함수를 추가한다. 먼저 test_metrics.py에 새 한계값·80%·성공 집합 평균·손상 자료 거절 RED를 작성한다. 기존 엄격 시험은 유지한다.
2. metrics.py는 기존 book 계산을 보존하고 education 계산에 명시적 population/threshold metadata를 반환한다. 관련 시험 GREEN 후 중복을 정리한다.
3. batch.py의 새 v2 plan에 정책을 실행 전에 고정하고 기존 v1 plan은 그대로 검증한다. 조작된 수치/혼합 정책 trial을 거절하는 RED→GREEN을 확인한다. evaluate_batch.py 준비·실행과 run_mission.py trial metadata에 정책을 연결한다.
4. 관련 시험과 필요한 전체 부품 회귀를 한 번 수행하고 자체 REVIEW/커밋/게시/공개 CI를 확인한다. 제어·물리·수명은 변경하지 않는다.
5. 저장 Level3 실패를 education_v1로 별도 오프라인 평가해 여전히 실패인 것을 명시한다. 부품 PASS나 완화된 정책을 정상 완주로 표현하지 않는다. 새 정책의 실제 반복 평가는 충돌 없는 연속 임무가 가능해진 뒤 사전 동결한다.
