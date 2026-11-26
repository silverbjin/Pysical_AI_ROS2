# Ch14 인수 원장

| Gate | 절 | 상태 | L0 | L1 | L2 | L3 | 범위/증거 |
|---|---|---|---|---|---|---|---|
| G00 | 공통 | BLOCKED | SCOPED_PASS | SCOPED_PASS | NOT_RUN | NOT_RUN | CPU profile PASS 45742206902 / 197 graph / 45 lock / build ABI smoke; rights/model/fixture/profile closure pending |
| G01 | 14.1–2 | BLOCKED (full); SCOPED_PASS (CPU conversion/inference) | SCOPED_PASS | NOT_RUN | NOT_RUN | NOT_RUN | T01/02/03 PASS; T04 40 raw/71 boxes, new GT miss 0; absolute n14/16 s15/16 FAIL unchanged; raw diagnostic 45746373267 PASS execution only; scope G01_ACCEPTANCE_SCOPE_KO.md |
| G02 | 14.3 | SCOPED_PASS (CPU T06); full BLOCKED | SCOPED_PASS | NOT_RUN | NOT_RUN | NOT_RUN | 45748461194 SUCCESS, 800 samples, 40/40 raw, 71/71 matched, new GT miss 0; T05 NOT_RUN; G01 full/release HOLD |
| G03 | 14.4 | SCOPED_PASS (L0/L1); L2 pending | SCOPED_PASS | SCOPED_PASS | NOT_RUN | NOT_RUN | T07 240x2 actual DDS, 123 overwrite, hb miss 39→0; T08 exact50/51/fault/TF/clock verified over 4 runs, final 45751287261 success; actual Gazebo next |
| G04 | 14.5 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G05 | 14.6 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G06 | 14.7 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G07 | 14.8 전반 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G08 | 14.8 후반 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G09 | 14.9 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |

GPU_OPTIONAL: NOT_RUN. Ch12 역사적 PASS는 Ch14에 전이하지 않음. CI ≠ Owner L3. 승인 전 main 병합 금지.
