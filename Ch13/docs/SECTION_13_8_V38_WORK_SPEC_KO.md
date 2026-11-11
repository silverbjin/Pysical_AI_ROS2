# v38 작업 명세와 순차 실행 계획

2026-11-11 KST. 기준 2ba1d991/v37. 단일 작업자로 실행하며 단계별 결과를 이 문서와 별도 보고서에 남기고 선택 경로만 커밋한다. 계획 실행은 executing-plans로 수행한다.

목표는 v37의 L3 PRE_GRASP 경로 거부와 L2 survey deadline을 각각 저장 증거로 재현하고 원인을 입증한 최소 변경으로 해결하는 것이다. 부품 PASS를 실제 임무 성공으로 표현하지 않는다. 설치 ROS2 Jazzy/Nav2 1.3.13/MoveIt 2.12.4/moveit_msgs 2.6.0/MuJoCo 3.13.0의 공식 소스·테스트를 우선 비교한다.

## 공통 계약

- v37 두 UUID와 판정·archive·source freeze를 수정하지 않는다. 새 증거와 manifest는 새 이름을 사용한다.
- link3 30mm 계획 여유·물리 접촉 guard·원본 정책·native PD·관측300ms·TF100ms·단일 ROS owner·소유 goal 회수 계약을 유지한다.
- 최종 goal XY15mm와 원고 최종3cm/120초/높이20mm 목표를 변경하지 않는다. survey의60mm/yaw.06rad는 중간 관측 조건이며 최종 점수가 아니다.
- 원인 분리 전 충돌 허용표 확대·계획 여유 축소·timeout 연장·속도 튜닝·전체 실험 재시도를 하지 않는다.
- engine 중 build/pytest/대용량 분석을 병행하지 않는다. 신규 raw는 모델 제외 archive와 내부 SHA를 검증하고, 결과·원인·회수·출처는 유지하며 불필요한 중복은 별도 원장으로 정리한다.

## 1. L3 계획 거부 원인 분리와 보완

입력: `6612d326-ae6c-4847-abe6-993e05150ec5`의 plans/pick_mission/launch와 source_v37. 실제 실패는 두 후보 error99999 및 ValidateSolution pick_target↔reuse/link7 충돌이다. 최종 로그 한 줄만으로 전체 경로의 유일 원인이라고 단정하지 않는다.

- [ ] 후보별 계획 요청·시작/끝 자세·경로/시간·scene revision과 충돌 로그 순서를 소형 JSON으로 추출한다.
- [ ] 기존 저장 장면 재생 도구로 실제 MoveIt의 GetStateValidity/동일 padding·ACM·target geometry를 사용해 경로의 처음/중간/끝 충돌을 분리한다. 같은 joint 경로의 padding0/.03 비교는 진단 전용이며 실행 설정은 .03을 유지한다.
- [ ] 공식 MoveIt ValidateSolution·FCL padding·Cartesian/pose constraint 구현과 결과를 대조한다. 요청 목표와 반환 경로의 실패를 구분한다.
- [ ] 확인된 원인만 겨냥한 회귀 시험을 RED로 재현하고 최소 구현으로 GREEN을 만든다. 예상 수정 경계는 `run_pick.py`, `scenarios.py` 또는 작은 planning helper다. 모르는 원인은 아직 수정하지 않는다.
- [ ] L3 별도 보고서에 원인·채택 ref·변경 경계·남은 한계와 시험 결과를 기록하고 커밋한다.

완료 조건: 저장된 v37 경로 거부의 원인이 authoritative scene으로 재현되고, 새 후보는 동일 물리/여유 조건에서 유효하며 기존 Level/legacy 회귀가 유지된다. 실제 팔 추종 성공은 단계3에서 별도 판정한다.

## 2. L2 survey deadline 원인 분리와 보완

입력: `7fdc7295-bcb1-44a2-85c2-7cd7902ea161`의 launch/BT 이벤트/Action·boundary/실측 base 기록. v37은42.846sim/126.365wall초이며 survey deadline이므로 허용 오차만 원인이라고 가정하지 않는다.

- [ ] survey 목표·실제 선택 XML/checker·최초 FAULT·종료 요청을 원래 clock/wall과 정렬한다. 최근접 XY/yaw 및 deadline 전 이동/정착 상태를 추출한다.
- [ ] 실제 설치 Nav2의 goal checker 선택, controller progress/failure, BT Action terminal 구현과 대조하여 최초 실패와 후행 timeout을 구분한다.
- [ ] 저장 fixture로 원인 재현 RED→최소 보완→관련 GREEN. 예상 경계는 `survey.py`, navigation config/BT 또는 기존 boundary의 작은 opt-in hook이며 새 소유 스레드를 추가하지 않는다.
- [ ] L2 별도 보고서와 회귀·기존 최종 goal 조건 보존 결과를 기록하고 커밋한다.

완료 조건: timeout의 최초 원인을 입증하고 그 조건을 막는 부품 검증을 통과한다. survey SUCCESS만으로 최종 도달/파지 성공을 인정하지 않는다.

## 3. 동결과 실제 기능 gate

- [ ] 변경 영향의 전체 부품 회귀, 새 소스 snapshot과 runtime 전수 hash 일치를 확인한다.
- [ ] 무실행/공유lockfree 확인→13.8 분리 build→실제 venv child/설치 모듈·새 config/XML·94자산 감사→새 manifest 및 runtime을 준비한다. 13.7/13.6 build를 보호한다.
- [ ] UUID/조건을 사전 고정하고 L3·L2를 단일 engine으로 순차 확인한다. 결과와 실제 정착·접촉·cancel/terminal·join·12child·최종 잔여를 판독한다.
- [ ] 실패 시 원인을 보존하고 저장 자료 조사로 돌아간다. 같은 계열의 두 최소 보완 뒤에도 실패하면 구조/경계 재검토를 기록한다.

## 4. 13.8 마무리 gate

- [ ] 두 실제 기능 gate 통과 후에만 새로운 동결10회(L2/L3 각5회, 실패 포함 분모10)를 수행한다. 기존 v28 0/10과 분리한다.
- [ ] 원고 목표 달성 여부와 실제/모의·물리 한계를 보고하고 학생 가이드·최종 인수 집계·다운로드/복원 절차를 정리한다.
- [ ] 단계별 커밋과 최종 검토를 남긴다. 게시/병합은 해당 사용자 지시 및 remote 상태와 구분한다.

검토 초점: stale/future 원본 관측, scene 변경 후 과거 plan 사용, 요청은 성공해도 실제 checker가 다른 경우, cancel ACK 뒤 미종료, 잔여 프로세스/열린 증거 파일. 각 조건은 기존 계약을 보존하거나 해당 단계의 회귀로 검증한다.
