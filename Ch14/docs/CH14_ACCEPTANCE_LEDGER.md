# Ch14 인수 원장

| Gate | 절 | 상태 | L0 | L1 | L2 | L3 | 범위/증거 |
|---|---|---|---|---|---|---|---|
| G00 | 공통 | BLOCKED | SCOPED_PASS | SCOPED_PASS | NOT_RUN | NOT_RUN | CPU profile PASS 45742206902 / 197 graph / 45 lock / build ABI smoke; rights/model/fixture/profile closure pending |
| G01 | 14.1–2 | BLOCKED (full); SCOPED_PASS (CPU conversion/inference) | SCOPED_PASS | NOT_RUN | NOT_RUN | NOT_RUN | T01/02/03 PASS; T04 40 raw/71 boxes, new GT miss 0; absolute n14/16 s15/16 FAIL unchanged; raw diagnostic 45746373267 PASS execution only; scope G01_ACCEPTANCE_SCOPE_KO.md |
| G02 | 14.3 | SCOPED_PASS (CPU T06); full BLOCKED | SCOPED_PASS | NOT_RUN | NOT_RUN | NOT_RUN | 45748461194 SUCCESS, 800 samples, 40/40 raw, 71/71 matched, new GT miss 0; T05 NOT_RUN; G01 full/release HOLD |
| G03 | 14.4 | SCOPED_PASS (CPU L0/L1/L2); full release HOLD | SCOPED_PASS | SCOPED_PASS | SCOPED_PASS | NOT_RUN | T07 240x2, 123 overwrite, hb miss39→0; T08 final DDS 45751287261; actual Gazebo 45751598173: 13/13 GT, 27 source emits max86ms, pause/resume and clean shutdown; G01/release/legacy/L3 pending |
| G04 | 14.5 | historical CPU SCOPED_PASS; ordered shutdown SCOPED_PASS | SCOPED_PASS | SCOPED_PASS | SCOPED_PASS (ordered runner); generic Ctrl+C HOLD | NOT_RUN | 45755020128 historical SUCCESS; 45758721305 failure preserved; 45760289636 targeted 3/3 GT and four clean exits in 601ms, no server escalation; native hang root cause unconfirmed |
| G05 | 14.6 | SCOPED_PASS (CPU T13 actual A/B/C); full release HOLD | SCOPED_PASS | SCOPED_PASS | SCOPED_PASS (actual fixed scene) | NOT_RUN | 45758721447 SUCCESS; 23 tests, 5 packages, 3x60 wall sec, 660 source/DDS match, GT miss0, heartbeat16/7/0; local Age caveat, G04 shutdown regression and release HOLD |
| G06 | 14.7 | SCOPED_PASS (CPU T14–T16); full release HOLD | SCOPED_PASS | SCOPED_PASS | NOT_RUN (replay, not Gazebo) | NOT_RUN | 45761633396 SUCCESS, artifact34/34; 4 installed packages, actual CPU inference, single/compose 39/39 DDS+3D each, six containers exit0 same image, domain mismatch rejected, cleanup PASS |
| G07 | 14.8 전반 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G08 | 14.8 후반 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |
| G09 | 14.9 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN | NOT_RUN | 없음 |

GPU_OPTIONAL: NOT_RUN. Ch12 역사적 PASS는 Ch14에 전이하지 않음. CI ≠ Owner L3. 승인 전 main 병합 금지.
