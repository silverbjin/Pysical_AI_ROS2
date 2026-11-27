# G05 최종 인수 보고서 — 협업 개발·MCAP 기록·분석·격리 재생
2026-11-27 KST | PASS_SCOPED_G05_T12_T14

## 1. 결론 및 실제 실행 PIN
- T12: 기존 G04 94/94 자산 closure 검증 재사용, approved exact URL/commit 및 drift rejection, rosdep 해석/의도적 미해석 key 거부, Git conflict/LFS 실제 실습(RED1), clean 6/6 packages 및 6/6 installed imports. V9 explicit tests 10/10 (lock2, analysis4, replay4). colcon test-result 자체는 등록된 테스트 0; package-local tests PASS라고 하지 않는다. 시각화는 G06 설치 골격만.
- T13 actual V7: [run45949623564](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45949623564), job140342206931, artifact15176233329, source 47bba1cc2769621ca68a4fffd025df384f1a755a. 정상+F01+F06 recording/typed decode/CSV/KPI/plots 3/3. V7 replay FAIL preserved.
- T14 actual V9: [run45950671176](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45950671176), job140345518769, artifact15175994043, source c69fb2585546b89702d21d5e4e86f610d569f330. One normal same-job recording then isolated original MCAP replay PASS. V7 F01/F06 and timing reused. G05 only Cyclone DDS, original Mock Action/Safety sources unchanged, standalone 10Hz scan source, seven processes.
- G04 physical L2 accepted PIN de16542fbb4d7aae1876fd39fd782cfcf77f655b preserved, original CH13_NATIVE failure preserved. G06–09 not started. G08 safety/recovery and WSL2 owner L3 NOT_RUN; no main merge/publication approval.

## 2. 실제 기록과 분석
| mode | terminal | event count | MCAP messages | exact accepted/terminal UUID | steady s |
|---|---|---:|---:|---:|---:|
| V7 normal | COMPLETED |23|730|4/4|3.622856700|
| V7 F01 | ABORTED |11|420|1/1|.701580911|
| V7 F06 | ABORTED |17|514|2/2|1.874561150|
| V9 replay-source normal | COMPLETED |23|712|4/4|3.516272169|
V7 1664 messages, 51 events, 7 accepted terminal UUIDs, 21/21 clean children. V9 7/7 clean. All 10 required topics >0 per actual record, metadata matches actual reader, distinct mission IDs, exact JSONL to CSV event count and compared fields, START/END and sequence, plots, joint energy null. F01 stopped scan after actual positive cmd_vel_in observed, no later scan. F06 actual pick terminal6. These are recording/analysis witnesses, not G08 recovery response gate. Actual source MOCK, full_mission_success=false.

## 3. 실제 독립 진단 및 근본 원인
- Scan original recorder OFF/ON qualified (source 100.498/100.410ms); isolated sync source100.214ms but watchdog receipt412.000ms and tick361.196ms, latch. No cgroup throttle. Source producer pause not reproduced in isolated original tests.
- V5 FastDDS ASYNCHRONOUS isolated qualified, integrated first nav/pick completed, then actual sample callback gap320.910ms caused watchdog latch and return rejection. V6 independent scan source actual 100.110ms max, no watchdog latch, but consumer start rejected; actual Arbiter safety_state publish268.997ms wall/.057ms CPU. Exact DDS internal implementation cause not proven; one cannot generalize RMW performance from these bounded runs.
- V7 Cyclone isolated source100.105ms, watchdog receipt100.164ms, tick50.258ms, no latch; all three actual records succeed. V9 integrated scan100.113ms max/no latch. Same original guard deadlines. This is scoped mitigation validated by actual evidence, not universal real-time behavior.
- V7 replay false rejection /events/read_split internal type; V8 allowed exact topic/type/owner and received23/23 full events,140/140 state,151 clock, but final /clock owner check failed. V9 binds exact DDS endpoint GID. Actual two owner-name metadata-loss observations /clock and /events/read_split retained exact GIDs, only after complete event/final status; endpoint removal confirmed. This verifies the teardown metadata pattern; V8 raw failed owner had not been recorded, so V8 exact GID cannot be retroactively proven.
- V9 replay source domain76 -> domain79, exact two playback topics, 23/23 full typed event data/order, 140/140 status payloads/final, 147 generated /clock messages monotonic, one publisher, control publishers0, no action/start/cancel service, clean player exit0 force false, graph cleanup true.

## 4. 독립 증거 감사
V7 ZIP SHA256 8a7005372df230d7e3bc2935870b190b9fd995619c9fde0fdcfa09eb9fdda4d2, 102/102 members. V9 ZIP SHA256 09a4f74cdff37516aa08335d9f29781e62fc85ecd1e43317d0e0dd3eb07504b3, 42/42. Independently verified all 144 member hashes, 48/48 per-case record/admission/exit/metadata/payload receipt/CSV/event/UUID/KPI/plot/fault checks, 18/18 combined scope and replay checks. Actual raw MCAP decoded and replayed in CI; public ZIP only metadata, hashes and analysis receipts, no independent re-reading of raw payload. C15 synthetic demo actual10/10, .9s, wrong type rejects from run45947575404 reused. User WSL2 raw bag remains local, no distribution.

## 5. 교육 포인트 및 반복 종료
각 RED에서 최초 실패 지점을 기준으로 수정 가설을 선택한다: RED1 readiness, RED2 latch, RED3 actual receipt, RED4 source gap, 독립 OFF/ON diagnostic, RED5 sample callback, RED6 consumer/DDS, V7 replay infra, V8 endpoint teardown. 원본 RED와 GREEN 모두 보존. 성공한 F01/F06을 재실행하지 않았으며, 공개 배포 금지 원본 bag을 다시 사용할 수 없어 replay마다 필요한 정상 1회만 수행했다. G05 scoped PASS. G06 개발 별도 요청 대기.
- [실습 15.4](../LAB_15_4_GUIDE_KO.md), [실습 15.5](../LAB_15_5_GUIDE_KO.md), [기록 및 재생 영수증](../../evidence/g05/g05_final_receipt.json), [인수 원장](../CH15_ACCEPTANCE_LEDGER.md)
