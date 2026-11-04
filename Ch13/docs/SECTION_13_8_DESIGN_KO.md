# 13.8 복합 시뮬레이션 실습 설계

2026-11-04 KST. 단일 작업자. 사용자는 전체 원고를 목표로 단계적으로 개발하고 추가 질문 없이 진행하도록 지시했다. 이 문서는 구현 성공 증거가 아니다.

## 목적과 기준

로컬 13ecb58d/v7의 Go2+Piper BT를 확장한다. 교재의 통합 기동, 동일 engine의 파지→귀환→내려놓기, 건강 상태·성능 계측, rosbag 재생, 반복 평가를 재현 가능한 실습으로 제공한다. 원본 12축 정책, native arm PD, 0.5N force-hold, 속도·가속도 한도, 원본 관측 수명, 단일 ROS owner, 취소 terminal/회수 계약을 유지한다.

## 접근 방식

선택: Level 1에서 연속 임무의 물리 가능성과 수명 경계를 먼저 검증한 뒤 Level 2/3 및 10회 평가로 확장한다. 대안인 Level 1+계측 한정 개발은 전체 원고를 충족하지 않아 선택하지 않았다. 기존 파지 종료 뒤 새 engine을 시작하는 방식은 연속 운반 증거가 아니므로 제외했다. 사용자 선택은 '질문없이 권장 방식으로 진행'이다.

## 구조

- 새 ch13_system_validation 패키지와 scripts/reuse_13_8. 기존 실행기의 작은 opt-in hook을 사용하고 probe/보행 loop를 복제하지 않는다.
- 정지 조작 권한과 운반 권한을 명시적으로 구분한다. 파지 접촉·arm terminal·정착을 확인한 뒤 다음 Nav goal UUID를 사전 예약하고 engine 확인 후 발행한다. 운반 중 팔 계획/개방을 금지하고 기존 force-hold를 유지한다. 귀환 terminal과 실제 정착 후 새 정지 조작 권한으로 내려놓는다. REVOKED/FAULT를 재활성화하지 않는다.
- 운반 중 접촉·자세·관측·소유권 상실은 실패와 정지 요청이다. 단순히 기존 zero-base 조건을 삭제하지 않는다. physics weld/teleport/oracle 제어 입력을 사용하지 않는다.
- 실제 센서·TF·원본 receipt 기반 계측과 프로세스 CPU/주파수 수집. sim 시간과 wall 시간, 전송 지연과 관측 나이를 별도 기록한다. 없는 전압 센서는 unavailable로 표시한다.
- rosbag는 실제 존재 토픽과 QoS에 맞춰 선별 기록한다. 재생은 별도 ROS domain에서 분석하며 live lease/actuator를 구동하지 않는다.

## 단계 및 판정

M0 원고·소스·공식 패턴·환경 조사 → M1 계측/판정/격리 도구 → M2 명시적 운반 권한과 부품 시험 → M3 단일 engine의 가장 불확실한 운반·내려놓기 → M4 월드 난이도/10회 집계 → M5 설치·가이드·자체 검토.

10회 시도 중 성공 ≥9회, 평균 mission 시간 ≤120초, 목표 오차 <0.03m, 최대 roll/pitch <0.1rad, CPU 평균 <70%를 원고의 목표로 유지한다. 초기 기동 제외 Start~Finish의 sim/wall을 모두 보고하고 CPU는 사용 코어 총량 대비 정규화 정의를 명시한다. 기능 성공과 목표 성능 PASS를 분리한다. 누락·NaN·중복 UUID·불완전 로그·시도 중 실패를 성공 분모에서 빼지 않는다. 반복할 소스/설정은 먼저 동결한다.

## 원고와의 차이 및 미확정 위험

원고 Level 1의 2m 대상과 공통 시나리오 (3,1) 테이블은 서로 다른 fixture로 명명한다. 알려진 원통은 콜라 일반 인식으로 표현하지 않는다. Level 3는 기존 보행 정책의 물리 통과/팔 도달 가능성이 필요하며 불가능한 경우 blocked 결과를 기록한다. 몸통 5cm shift, damping +20%, nice -10, 무조건 Best Effort, effort/마찰 증가, 가상 부착은 기본 해결책으로 적용하지 않는다. 기존 정상 파지 한 번에 161.90sim초였으므로 120초는 달성 전제나 timeout이 아니다. 전체 mission 안전 예산은 별도로 정한다.

## 검증과 보존

저장 자료→부품 RED/GREEN→필수 실제 사례 순으로 검증한다. 같은 실패 계열 두 최소 수정 후에도 남으면 실행 경계/구조를 재검토한다. 장시간 과거 matrix를 반복하지 않는다. 새 build는 기존 13.6/13.7 및 상하위 경로를 보호하고 sibling 공유 lock을 유지한다. 모든 신규 실행은 새 UUID/evidence이며 기존 freeze/FAIL/verdict는 보존한다. 게시·main 병합은 범위에 없다.

## v2 실제 실패 후 운반 관측 계약 보완

v2에서 파지 후 회전14.60sim초 동안 양 finger 접촉100%·상대 slip4.27mm였다. gripper 부분 가림으로 원래 upright fit의75% 높이 가시성 조건을 만족하지 못해 원본3D 관측이 만료되어 중단했다. 원래3D 관측을 재발행하거나300ms를 늘리지 않는다.

운반 권한은 새 카메라 capture health의 원본 stamp/촬영 monotonic 시각/최초 native DDS receipt와 소유자를300ms 이내로 검사하고, 매 physics step의 지정 finger-target 양 접촉 및 force-hold ready, 팔 action 미실행, 허용 자세/속도, 예약된 Nav goal을 모두 요구한다. 과거3D point는 운반 명령·새 팔 계획의 권한이 아니며 만료 상태 그대로 보존한다. fresh camera health는 기존 vision 노드가 실제 RGB-D bytes/hash·과거TF를 검사한 별도 스트림이다. 독립 C++ latest-only relay로 engine에 전달한다.

귀환 terminal/실측 정착 뒤에는 fresh3D 재획득 전까지 PLACE_WAIT에 머무르며 팔 action을 허용하지 않는다. PLACE에 들어간 뒤에는 기존3D 관측300ms·TF100ms·zero-base·3cm/0.1rad drift 경계를 다시 적용한다. LOWER→RELEASE→RETREAT 순서를 강제하고 지정 receiving support의 실제 접촉 전에는 개방을 금지한다. health/접촉/소유권 상실은 latch fault다. 이는 고정 팔 운반을 위한 별도 권한이며 기존 정지 lease를 완화하지 않는다.
