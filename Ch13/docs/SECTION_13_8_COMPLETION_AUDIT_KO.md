# 13.8 전체 마무리 작업 및 현재 상태 점검

점검: 2026-11-05 23:59 KST. 단일 작업자. 원고·설계·실행 계획·실제 판정·커밋·원격 ref를 대조했다. 이번 점검에서는 새 구현이나 engine 재실행을 하지 않았다.

**결론: 구현·조사·기존 10회 평가는 상당 부분 진행됐지만, Level 2·3 수정본의 연속 임무 인수와 성능 목표 충족은 미완료다. 현재는 후진 경로/목표 회전 구성의 실제 부품 검증 후, 운영 설정을 적용하기 전 회귀 RED 단계다.**

## 전체 마무리 범위와 도달 지점

| 작업 | 현재 증거 | 상태 / 완료 조건 |
|---|---|---|
| 원고·범위·공식 패턴 조사 | 13.8.1~8 확보. 설치 버전 MoveIt/Nav2/ROS/MuJoCo 근거와 설계 기록 | 기본 완료. 새 제어기 조합 근거도 조사함 |
| 13.7 기반 격리·환경 | 전용 branch/worktree/build, 기존 모델·정책·94 자산·공유 lock 재사용 | 완료. 실행 전 소유 상태는 매번 확인 |
| 연속 임무 구현 | 같은 engine에서 탐색→접근→파지→운반→귀환→지지 확인→개방/detach→팔 후퇴→Finish 코드와 물리/수명 경계 구현 | 코드 존재. 모든 원고 Level의 실제 인수 완료는 아님 |
| 개발 fixture | v15 실제 pick/transport PASS, 연속 기능 1회 완료 | 완료한 개발 증거. 원고 Level/성능 평가 대체 불가 |
| Level 1 | v22 연속 기능/BT SUCCESS·정상 회수. 높이 하강 20.094mm, 귀환 44.449mm, 199.538sim초 | 기능 완료 이력 있음. 엄격 최종 FAIL, 목표 충족 미완료 |
| Level 2 | v28에서 Pick PASS 3건, 그중 1건 연속 기능/BT SUCCESS. 높이 23.360mm·귀환 55.231mm·259.912sim초 | 기존 기능 완료 이력 있음. 수정본 실제 인수와 수치 목표 미완료 |
| Level 3 | 기존 4건 6D pre-grasp 계획 실패. 충돌 원인 분리·pre-distance 수정/부품 검증. v34 실제 survey 도달·정착 통과 후 접근 계획 거부 | **연속 파지·운반·놓기 미완료** |
| 기존 고정 10회 평가 | v28 L2/L3 교대 각 5회, 총 10회 실제 완료. 엄격 성공 0/10, world witness 9/10 | **평가 실행 완료, 목표 실패**. 기존 분모·실패 보존 |
| 반복 문제 수정·조사 | 아래 문제별 표 참조 | 조사/부품 수정과 실제 해결 여부를 구분해야 함 |
| 최신 build/부품/소스 감사 | v34: 433 PASS/62.72초, source 383개/asset 94개, tested/runtime hash 일치, 설치·실제 venv child 감사 PASS | 마지막 전체 GREEN은 v34. 현재 편집본은 새 RED 검사 단계 |
| 수정본 실제 기능 확인 | v30~v34 사례 실패를 모두 보존. v34까지 L3 survey는 개선됐으나 최종 접근 미통과 | 진행 중. 새 L2/L3 연속 임무와 정상 종료 증거 필요 |
| 수정 후 새 고정 10회 | 아직 시작하지 않음 | 필수 연속 기능 gate 통과 후 source/scenario/10UUID 사전 동결하여 실행 |
| 성능·최종 집계 | 기존 CPU/tilt/시간/위치/접촉/height 판정과 실패 수치 있음 | 새 동일 조건 집계, 관측/health 만료 재확인 필요 |
| 로그·보존·복원 | 기존 원본/판정/freeze 보존, 모델 제외 archive와 hash 검증 이력. v32~v34 raw/정확한 source archive 커밋 | 최신 최종본의 보존·설치/복원/가이드 정합성 마무리 필요 |
| 학생 가이드·최종 보고·자체 검토 | 파일 존재하지만 과거 버전/후속 보고가 여러 문서에 나뉨 | 최종 동결 기준으로 명령·결과·한계·목록 통합 필요 |
| 원격 게시 | 원격 feat/ch13-section-13-8 = 9a2a00bd를 이번에 재조회 | 그 이후 수정 커밋은 로컬에만 있음. 최신 게시 및 원격 동일성 확인 미완료. main 병합은 범위 아님 |

## 해결한 문제와 남아 있는 문제

| 문제 | 지금까지 조치·검증 | 남은 확인 |
|---|---|---|
| L3 위치 IK는 되지만 실제 6D 계획 실패 | 설치 MoveIt collision-aware IK/validity로 base↔link3 접촉 분리. pre-distance .06→.03의 저장 4개 표본 검증 | 수정한 자세로 실제 접근·파지 완료 미확인 |
| L2 원본 관측/health 만료 | 촬영→발행/수신 단계 지연과 실제 300ms 위반 분석. 계측 추가. early capture overlap은 실제 지연 후 기본에서 철회, 명시적 실험만 유지 | **실제 반복 만료 해결 미확인**. 수명 확대 없음 |
| L2 운반 안전 중단 | 실제 yaw .361169rad/s가 .35 상한을 넘은 첫 위반 확인. L2 명령 yaw cap .10 부품 검증 | 수정본 적재 이동의 실제 안정성 미확인 |
| 세계 높이 하강 | 23.360mm를 TCP·상대 slip·몸체 자세 기여로 분리. 접촉 100%와 높이 성공을 구분 | **20mm 목표 미해결**. 정책/WBC/effort로 우회하지 않음 |
| 최종 방향 회전 중 XY 이탈 | goal checker와 RPP의 서로 다른 stateful latch를 확인·보완. heading-aware 계획 적용 | v34 survey 실제 도달·정착 개선 확인. 접근/귀환 전체는 미인수 |
| 파지 뒤 원래 대상 자리가 지도에 남음 | native GID/session/goal·fresh 실제 접촉/force-hold에서만 지도 제거. 실제 costmap 갱신/ACK 부품 검증. 장애물 캐시 비활성 | 실제 파지→지도 갱신→귀환 연계 미확인 |
| 계획 성공인데 footprint 충돌 | 반환 pose 전체의 filled-footprint 검사 추가. 충돌 경로 거부. 보간/padding/해상도 비교 중 실패도 보존 | live costmap까지 포함한 유효한 접근/탈출 경로 실제 확인 필요 |
| v33 지도 콜백 KeyError | rclpy 콜백과 기존 wire 메타데이터 혼동 수정. 실제 C++ DDS 중계 통합 시험 추가 | v34 실제 실행에서 지도 노드 정상 종료, 자식 12개 회수 확인 |
| 전진 전용 경로의 접근/탈출 거부 | REEDS_SHEPP 비교에서 서쪽 L3 접근 4조합+귀환, L2 귀환 모두 filled-footprint 충돌 0 | **아직 운영 코드에 적용하지 않음**. 적재 후진의 실제 물리 검증 필요 |
| 공식 shim 내부 XY latch 재발 가능성 | 설치 1.3.13의 내부 prefix 문제 확인. 실제 library 12mm 도달→20mm 이탈 RED→GREEN. 실제 controller configure/cleanup도 잘못된 설정 FAIL→수정 PASS | 운영 YAML·launch·회귀에 반영하고 새 동결로 확인해야 함 |

반복 문제는 있었다. 관측/health 만료, 목표 회전과 XY 정착의 불일치, 좁은 접근/탈출 경로의 계획 거부가 반복됐다. 단순 설정 보완 뒤에도 실패하여 owner/수명·제어기 latch·지도 수명·SE2 경로 구조로 조사 범위를 옮겼다. 모든 원인을 해결했다고 볼 수 없다.

## 지금 중단된 정확한 위치

- 로컬 branch: `feat/ch13-section-13-8`, 점검 시작 HEAD `46c5c69e4f10b912ff44a48b2fa000ee522cd35b`.
- 마지막 전체 GREEN 동결 v34 manifest SHA256: `0faa40478e47270fb2c3f298b1c16511902612dbf7c682668bc72fd55b0dce4c`.
- v34 실제 L3 UUID `9e160887-cc8a-4f1d-a4e7-83aae4f77818`: survey 통과 뒤 접근 계획 error 208, 파지 전 FAIL. engine 정상 종료·12 child 정상 회수·잔여 0.
- 후속 명세는 [후진·목표 회전 계획](SECTION_13_8_REPAIR_REVERSE_PLAN_KO.md)에 커밋돼 있다. 실제 설치 shim/RPP 구성과 내부 판정기의 부품 검증을 마쳤다.
- 수정 예정 동작을 검사하는 두 테스트 파일만 로컬 수정 상태다. 마지막 선택 검사는 **7 FAIL / 5 PASS / 425 deselected**(26.69초). 이는 구현 전 의도된 RED이며 현재 작업트리가 전체 PASS라는 뜻이 아니다.
- 후진 하한 -0.10, REEDS_SHEPP, shim/RPP 조합, 서쪽 접근 제한은 **운영 설정에 아직 적용하지 않았다**. 새 v35 freeze, 실제 수정본 사례, 새 10회는 모두 미실행이다.
- 이번 실제 잔여 검사: owned stack 없음 / 공유 engine lock free / PASS. 이전의 실행 세션은 종료됐으며 engine을 새로 시작하지 않았다.

## 앞으로 끝내야 할 순서

1. 후진·목표 회전 설정을 운영 YAML/launch에 최소 반영하고, 현재 RED 7건 및 관련 회귀를 GREEN으로 만든다. legacy/L1·기존 안전/수명 경계 보존을 확인한다.
2. 별도 build·설치·실제 venv child·전체 회귀를 확인한다. 새 source freeze와 테스트/실행 소스 전체 hash를 대조하고, 실제 사례 UUID를 실행 전에 고정해 커밋한다.
3. 단일 engine으로 L3/L2 실제 연속 기능을 순차 검증한다. 음수 명령 전달, actual 속도·접촉·관측·정착·내려놓기·terminal·회수·잔여를 확인한다. 실패하면 원인을 보존하고 부품 조사로 돌아간다.
4. 그 과정에서 원래 관측/health 만료와 운반 안전·height 문제를 다시 판정한다. 부품 PASS를 실제 해결로 올려 쓰지 않는다.
5. 필수 기능 gate가 통과하면 새 동일 조건의 고정 10회를 수행한다. 실패·기동 실패도 분모에 포함하고, 성능 목표 미달도 그대로 보고한다. 기존 v28 결과는 별도로 남긴다.
6. 최종 source/evidence archive·hash·필요한 복원·설치/다운로드 경로를 확인한다. 학생 가이드와 개발자 고장 주입/회귀를 구분하고 보고서·문제 이력·자체 검토를 최종 버전으로 연결한다.
7. 단계별 커밋을 정리한 뒤 승인된 13.8 브랜치에 최신 내용을 게시하고, 원격 HEAD와 실제 게시 파일을 재확인한다. main 병합은 하지 않는다.

**마무리 판정은 “433개 부품 PASS”나 “기존 10회 실행 완료”만으로 내리지 않는다. 수정본의 연속 기능·물리 판정·목표 수치·종료/회수·최종 문서/게시 범위를 각각 명시해야 한다.** 목표 수치에 못 미친 결과를 받아들여 보고하는 것과 목표를 통과했다고 주장하는 것은 별개다.

## 증거와 주요 문서

- [원고 기준 설계](SECTION_13_8_DESIGN_KO.md), [고정 10회 결과](SECTION_13_8_LEVEL23_EVALUATION_REPORT_KO.md).
- [순차 수정 계획](SECTION_13_8_REPAIR_SEQUENCE_PLAN_KO.md), 단계별 [1](SECTION_13_8_REPAIR_STEP1_LEVEL3_KO.md) / [2](SECTION_13_8_REPAIR_STEP2_OBSERVATION_KO.md) / [3](SECTION_13_8_REPAIR_STEP3_TRANSPORT_KO.md) / [4](SECTION_13_8_REPAIR_STEP4_VALIDATION_KO.md).
- [경로·지도 구조 조사](SECTION_13_8_REPAIR_NAVIGATION_STRUCTURE_KO.md), [후진·목표 회전 후속 명세](SECTION_13_8_REPAIR_REVERSE_PLAN_KO.md).
- 이번 점검 snapshot: `../evidence/section_13_8_repair/completion_audit_20261105/`. 실제 제어기 구성 RED/GREEN, native checker RED/GREEN, 선택 회귀 RED, 현재 잔여 점검을 함께 보존했다.
