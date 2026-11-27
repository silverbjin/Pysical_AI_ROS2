# G08 개발 프리뷰 — T18/T19 안전 정지 및 복구

G07 scoped T16/T17 PASS 후 착수. G03/04/05/06/07의 기존 성공 SHA 및 원본 실패 증거 유지. G05 V7의 F01/F06 MCAP는 기록/분석 검수 증거이며, G08 복구 검수로 자동 승격하지 않는다.

| 단위 | 구현 및 실제 검수 경계 |
|---|---|
| G08-1 | FMEA 및 오류 계약 F01~F10, deterministic tests. 정지/latched guard 우회 없음. |
| G08-2 | mock F01: scan/heartbeat 실제 loss, receipt/source freshness 별도 측정, block→zero, exact UUID terminal, 복구 후 자동 재개 금지. 기존 임계 유지. |
| G08-3 | F03 탐색 실패 후 fresh 재검증(일시 실패 복구 및 영구 실패 max3), F04 stale/wrong epoch 접근 타깃 reject 및 pick0. |
| G08-4 | F06 PickObject ABORTED(success=false), 각 재시도 이전 UUID terminal, fresh target, stand/정지 확인, 최대 3시도, latch 중 재시도0. |
| G08-5 | MCAP, 이벤트/UUID, timing, exit/residual, installed Nav2 behavior plugin 확인. 실제 spin/backup은 별도 승인 없이는 실행 금지. |
| G08-6 | 물리 F01은 native 안전한 fault hook 및 승인 증거 없으므로 BLOCKED_PHYSICAL_FAULT 유지. 별도 근거 없이 물리 성공 주장 금지. |

실행 계획: 기존 G05 scheduling 및 Cyclone DDS isolation 구조를 재사용하되 새 G08 전용 fixture/entrypoint로 기능과 증거 분리. 물리/GUI/기존 성공 케이스 반복 금지. 실제 실패 시 최초 경계 증거와 교육 보고서 commit 후 단일 변화. G09는 G08 인수 범위 확정 후 진행. 현재 G08 preview only, NOT_RUN.
