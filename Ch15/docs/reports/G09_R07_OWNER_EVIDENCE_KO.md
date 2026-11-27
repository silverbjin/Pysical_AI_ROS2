# G09-R07 — 사용자 인수 증거 고정
- 기준 72db9392fa8e8c9fa3eb8e4033453bedeb299430, PR #208 draft, main 1931cac92585fc155357880b584c72c76d67257c. 독립 브랜치.
- 실제 첨부 4개 외부 SHA 4/4, 내부 manifest 163/163, 파일 목록 정확 일치. 각 source receipt 378개, requested/actual PIN 0b044f528ffd99b23d563f32eddf27833dea7566, bootstrap receipt verified true. 실행기 바이트 자체는 첨부에 없어 별도 재해시하지 못함. 원본 MCAP magic 및 해시 확인, 이번 회차 MCAP 메시지 전체 독립 재디코딩 미수행.
- [R07 receipt](../../evidence/g09/owner_l3_r07_receipt.json), [R01 receipt](../../evidence/g09/owner_l3_r01_receipt.json). R01 기존 4 PASS 재사용.
| 항목 | Owner | 미션 | 근거 |
|---|---|---|---|
| F03 transient | PASS | COMPLETED | 탐색 2회, 신규 목표 valid 12, 4 terminal |
| F03 persistent | PASS | ABORTED | 탐색 3회, withheld 39, pick 0 |
| F04 | PASS | ABORTED | mission_epoch invalid 82, pick 0 |
| F06 | FAIL | ABORTED | 최초 pick status6, RETRY 1, readiness_or_safety_lost, fault receipt NOT_RUN |
- 각 실행 child 7/7 exit0/forced0, container residual0. F06 별도 global graph residual 파일 없음; 전체 노드 잔여0 단정 금지. F06 record PASS는 owner PASS 아님.
- F06 first watchdog latch 477946834642ns, arbiter 477947361241ns (MONOTONIC); realtime step lower 2931180386ns container, host 2931178000ns 근방. 원인 Windows/Hyper-V/guest time discipline 미확정.
- Host 9101 samples, forward15/backward3; 후반 3 runs RAW/MONOTONIC 상대 속도 약 +9.096205%. F03 transient 전체 +2.824558%. 서로 다른 시간 계통의 절대값 비교 금지. F03/F04 PASS에도 환경 장애 존재.
- 조치: R08 장기 진행률 및 gap-aware 분석 추가; R09 외부 기준 계측. 안전 임계값/미션/실행기 변경 없음. F06/F01 재실행 금지, native 기본 NOT_RUN, physical full BLOCKED, publication HOLD. 원본 비공개 유지.
