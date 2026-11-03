# R2 단계 0 — 기준본 게시와 후속 실행 계획

작성일: 2026-11-02 KST. 사용자 지시: 새 브랜치에서 기존 작업을 먼저 commit/push하고 R2를 끝까지 수행하며 매 단계 보고서를 함께 게시한다.

## 기준본

기존 corrected A profile, edu_stop_v2, 최소 ROS2 연결을 보존한다. 실제 엔진 증거 ad20c823: 전진0.433457m, raw손실→zero결정0.314408wall초, 실측정착·latch·정상회수 PASS. 기존 실패는 변경하지 않는다. 당시 28개 검사 PASS이며 이번 게시 전 같은 검사를 재실행한다. 원본94개 자산은 lock으로 참조하며 모델/가중치는 저장소에 복제하지 않는다.

## 순차 단계와 게시

1. 단계0: 현재 변경과 이 보고서를 새 브랜치 feat/ch13-section-13-5-reuse-r2-20261102에 commit/push. 기존 브랜치/사용자 변경 보존.
2. 단계1: 실제 DDS publisher 교체·clock pause·state 손실/미래 입력·relay 손실과 latch/명시 재무장 검증. 보고서·검사·증거 commit/push.
3. 단계2: 속도 slew의 시간축을 sim초로 맞추고 wall watchdog을 유지. RED→GREEN, 설치 감사 및 전체 작은 검사. 보고서 commit/push.
4. 단계3: 설치 launch 경로에서 실제 짧은 이동·회전·정지·고장·정상종료/회수 확인. 최종 R2 경계 대조·보고서·lock/checkpoint 갱신 후 commit/push 및 원격SHA 확인.

R3/Nav2·지도·센서·비전·MoveIt는 범위 밖이다. 새 gait나 학습을 추가하지 않는다. 물리 실행 중 빌드/검사를 병행하지 않는다. 단계마다 PASS/FAIL과 미검증을 구분하고 실패를 보존한다.

## 판단 기록

- 기존 worktree를 유지하고 새 브랜치만 만든다. 미추적 파일을 임의 stash/clean하지 않는다.
- 단일 작업자 요구를 유지하며 최종 자체 검토한다. 전체 R0-R5 계획은 미완료이므로 기존 작업 ledger는 보존한다.
- 원격 조회 실패는 승인 서비스 사용량 및 실행 사용자 차이에 따른 저장소 소유권 인식 문제로 구분한다. 전역Git 설정을 변경하지 않고 요청한 저장소에 한정한 명령별 safe.directory를 사용한다.

## 이번 게시 전 재검사

2026-11-02 재검사: 28개 중27 PASS, `test_gateway_sigterm_has_normal_exit` FAIL(exit1 기대0). 과거 실제 연결 PASS는 당시 고정본 결과이며 이번 반복의 실패를 덮지 않는다. [전체 로그](../evidence/section_13_5_reuse/r2_stage0_20261102/baseline_tests.log). 현재 commit은 완료 선언이 아닌 검토 가능한 기준본 보존이다. 단계1에서 stderr를 보존해 종료 경합을 제한 조사하고 RED→GREEN으로 수정한다.

해시 대상 신규 경로에 한정해 `.gitattributes -text`를 적용한다. Git의 자동 개행 정규화가 다운로드 후 SHA를 바꾸지 않도록 원본 바이트를 보존하며 기존 장 경로에는 적용하지 않는다.
