# G08 최종 범위 인수 — PASS_SCOPED_G08_T18_T19_MOCK
2026-11-27 / Draft PR #208 / main merge HOLD. G01–07 owner tags exact7/7 verified; G07 baseline d05c67b1e88e06e5323722403e459afa6eaa2027.
## 1. 실제 개발·디버깅
- 독립 boundary RED1 import omission, V2 PASS run45955737237, unit8/8, actual DDS3/3. Existing report preserved.
- Search V1 RED run45967669908: stale allowed self node name, no children/injection, ZIP+13 verified. V2 fixed self/namespace; actual function3/3 PASS run45967908191, source4d6f207d62051c6d3b17a44d43731a46f1873a8e, artifact15184086938. Postprocessing failed root-owned MCAP unlink; original CI FAIL retained. ZIP verified, raw MCAP3 hashes verified, CSV64/64 exact, original internal hash manifest absent. Local derived sanitized ZIP SHA256 7ce89d88966abfe58aeb947920ebd73e6add8b8a6f038420d63c0f044c387d8b, 86 members hashed, raw omitted3; not original CI manifest.
- Pick/stop V3 actual CI PASS [45968356728](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45968356728) job140402408362 artifact15183652813 source 3a35404ce7cb7965adad5a4bc54c9efdce1f8153. ZIP 498781e564f6ffa1fc5d280e9315ff3e5a61e204ed2a0c92a7b3dbd767782a4d, internal60/60 independently verified, raw MCAP omitted2, 45/45 exact event CSV independently checked. New staging copies approved receipts only, does not delete root-owned directories. V2 runtime recovery_executor and original control sources unchanged; V3 observer/analyzer/staging/plugin audit changes only.
## 2. T18/T19 actual mock
| Scenario | outcome | attempts/Goal | events | MCAP messages | clean children |
|---|---|---|---:|---:|---:|
| F03 transient | COMPLETED | search2; pick1; terminal4x4 | 31 | 857 | 7 |
| F03 persistent | ABORTED | search3; pick0; nav terminal4 | 17 | 822 | 7 |
| F04 | ABORTED | 82 invalid observations; pick0 | 16 | 1369 | 7 |
| F06 | ABORTED | pick3; distinct terminal6x3; nav4 | 35 | 584 | 7 |
| F01 | ABORTED | nav exact terminal6; pick0 | 10 | 416 | 7 |
Total 5 cases,109 events,4048 typed MCAP messages,11 exact terminal UUIDs,35 child exit0/forced0. F06 prepared3/3 (new stamp>settle, fresh, settled, previous terminal), decision RETRY→RETRY→ABORT. No fourth pick. F03 transient original seven leaves+ready verified, not merely recovery success.
## 3. timing and boundaries
F01 actual source stamp path: native scan receipt→guard337.987493ms (≤1150ms), internal arbiter blocked observation→actual zero publish completion .067793ms (≤100ms); previous positive output, all later outputs zero, exact terminal6 UUID and STOP_OBSERVED. Independent paused ROS clock receipt→guard observed publish interval1008.634106ms, source jump→guard29.397563ms, heartbeat loss→latch168.776794ms and zero168.405634ms (≤250ms), resumed clear/nonzero0. Distinguish native receipt vs fixture publication/observer. Original G05 V7 F01 343.100ms and exact goal terminal preserved, source closure original safety/action/default executor unchanged; new run only to establish missing direct native zero witness in G08 opt-in runtime.
F02/F05/F07/F08/F09/F10 L0 deterministic contract covered, F07 also actual DDS. G03 late/cancel-unconfirmed source supervisor unchanged. Nav2 Jazzy installed XML class and shared library3/3 Spin/BackUp/Wait, YAML schema checked, behavior server not launched. No physical motion recovery. Physical F01 BLOCKED_PHYSICAL_FAULT, no native approved injection hook. Mock label and no full physical claim.
## 4. limitations and publication
Original search V2 accidentally includes 3 synthetic mock MCAPs due cleanup failure, no external asset/real physical data. GitHub connector lacks artifact-delete method; owner may remove that artifact after preserving sanitized copy. Raw never committed, new CI upload strictly sanitized. Original failure and hashes remain. C24 actual implementation explicit RetryBudget, not stock py_trees Retry decorator (counts preparation failures and exact terminal). G09 manuscript-to-runtime API mapping QA pending. All owned child exits verified, global graph residual check not independently asserted. WSL2 L3 NOT_RUN. G08 scoped MOCK acceptance only, not global/physical recovery. Main remains Draft. G09 next.
## 5. 교육
실패 경계를 코드/런타임/배포로 나누고 이미 GREEN인 실제 기능을 반복하지 않는다. 정지 요청, latch, zero publication, UUID terminal, physical stop은 서로 다른 관측이다. [가이드](../LAB_15_8_GUIDE_KO.md), [receipt](../../evidence/g08/final_receipt.json).
