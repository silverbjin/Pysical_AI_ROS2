# G08-1/2 범위 인수 — L0 및 독립 DDS 경계 PASS

## 실제 증거
- V1 RED1 build3/3, L0 8/8, probe import failure before injection (original ZIP+5 verified).
- V2 [Run 45955737237](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45955737237), job140361663164, artifact15178861198, source 086fa15b636304fafbd080312ec751f380af1e73; ZIP SHA256 586b2345d5614a9c35e3196fe7f510226c46bb4286863f7a6b2080dc4f8ed2eb, 내부 7/7 검증. 3개의 독립 run ID 및 fixture hash; 3 clean exits. 안전 노드 원본 및 시간 기준 변경 없음. L0 8/8.

| 경계 | 실측 | 판정 |
|---|---:|---|
| F01 steady receipt timeout, ROS clock paused | 마지막 scan publish→guard 1.008634106s (≤1.15s) | PASS fixture |
| F01 source-stamp age | clock jump trigger→guard .029397563s | PASS fixture |
| F07 heartbeat loss | 마지막 heartbeat publish→latch .168776794s (≤.25s) | PASS fixture |
| F07 heartbeat loss | 마지막 heartbeat publish→zero .168405634s | PASS fixture |
| F07 latch/zero observation | 절대 관측 시차 .00037116s | PASS fixture |
| F01/F07 resumed input | clear/nonzero 0 | PASS fixture |

주의: isolated observer 측정은 publisher→observer이고 native callback receipt 직접 계측이 아니다. latch와 zero 수신의 절대 시차는 인과적 block→zero 내부 지연과 구분한다. F01 두 실험에는 실제 mission goal이 없다. F07 actual DDS는 Mock 명령 경계이며 실물 정지 증거 아님.

## G05 V7 F01 원본 재분석
[Run 45949623564](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45949623564), artifact15176233329, source47bba1cc2769621ca68a4fffd025df384f1a755a, ZIP SHA256 8a7005372df230d7e3bc2935870b190b9fd995619c9fde0fdcfa09eb9fdda4d2, 102/102 내부 해시 검증. 실제 positive command input 이후 scan 중단, native 마지막 Scan receipt→latch .343099964s, same UUID ca888257c72a4ef1bc05379ade5c2a8a terminal status6, STOP_OBSERVED 7 mock zero samples, END ABORTED/all_terminal true, seven clean exits. MCAP decode와 기록 증거는 재사용하되 raw payload 미배포. 직접적인 block→zero 타이밍은 해당 아카이브에서 독립 확인되지 않음. G08 최종에서는 source closure와 부족한 경계 증거를 확보해야 함.

## 남은 범위
G08-1 FMEA/단위 계약 및 G08-2 독립 DDS 경계 완료. G08 전체는 HOLD. 다음 G08-3: 기존 MissionExecutor를 별도 recovery profile로 연계, F03 transient/persistent와 F04 실제 DDS. 이후 F06 3회 이하 actual UUID, fresh/settle/terminal, F01 부족 witness 및 MCAP/KPI, Nav2 plugin 설치 검증. 물리 F01 BLOCKED, 원본 안전 기준과 G04~07 성공 PIN 유지. G09 및 owner L3 NOT_RUN, main merge HOLD.
