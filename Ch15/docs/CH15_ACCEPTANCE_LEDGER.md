# Ch15 인수 원장
기준 main 1931cac92585fc155357880b584c72c76d67257c. Ch01~14 불변. 공개 소스 개발 승인, 출판/외부 모델 재배포/main merge HOLD.
| Gate | 상태 | L0 | L1 | L2 | L3 |
|---|---|---|---|---|---|
| G00 | SCOPED_MOCK_CPU_READY; physical asset/rights pending | SCOPED_PASS | SCOPED_PREFLIGHT | NOT_RUN | NOT_RUN |
| G01 | T01/T02 scoped | PASS | NOT_RUN | NOT_RUN | NOT_RUN |
| G02 | SCOPED_PASS | PASS 6 pure/IDL tests | SCOPED_PASS T03–05 | NOT_RUN | NOT_RUN |
| G03 | MOCK_MISSION_PASS; T06–09 scoped | PASS 16 pure tests | SCOPED_PASS | NOT_RUN | NOT_RUN |
| G04 | PARTIAL_PASS_T11; T10 BLOCKED | PASS 13 baseline +3 targeted | SCOPED_PASS 3 package cube build | T11 PASS; T10 BLOCKED | NOT_RUN |
| G05 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G06 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G07 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G08 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G09 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
- G00/G01 CI 45853673522: static 7/7, negative drift/assets, actual mock preflight, native SDF Valid. G00 physical assets/rights/closure HOLD. Previous automatic repeat 45855234520 recorded, workflow dispatch only.
- G02 runs 45855381985 and 45855811717, source d908f219... and e22c4fb5..., original receipts evidence/g02_ci_receipt.json. 4 package builds, eight IDLs, DDS 3/3 accepted + three reject, QoS 10/0/S10, independent missing predicates, short deadlines, latched reject. G03 start/cancel/reset scoped verified; true safety latch reset G08.
- G03 original run 45857297181 overall FAIL (D01 init collision), T06 8/8 actual PASS and 16 pure tests. Normal fix run 45857717821 PASS, ready+7/7, accepted/terminal 4/4, 35 ticks P95 1.042921ms max 1.17032ms, 5/5 children exit0, full physical false. Target/cancel/invalid run 45858159748 PASS, actual typed DDS 10/10 negatives, wrong epoch 81/0/0, operator cancel 79.961972ms exact UUID, 11/11 children exit0. Three original ZIP SHA256 and 56/56 inner files verified. [G03 report](reports/G03_FINAL_REPORT_KO.md), [receipt](../evidence/g03/receipt.json).
- G04 T11 run 45910585983 SUCCESS at 468e02849613ee3b26c389078c8989643380db3c. Actual Harmonic 10/10 normal unique stamps, max 2.045876541mm, min IoU .9216202813, skew 0ns, invalid depth 3/3 + actual occlusion 3/3 blocked, command publishers 0, detector/TF/bridge/Gazebo exit0 force0. Normal sensor is actual; invalid-depth copied real-frame NaN fixture; actual occlusion uses native set_pose. Position-only. 13 pure tests (8 native/compatibility,5 cube); 3 packages build 15.9s. Targeted native fixture run 45910956651 SUCCESS 3 tests, source ddeddf51e12524bb0323166a87c547742a8b578f. ZIP hashes and 25+3 inner files independently verified. T11 source closure unchanged by subsequent native adapter/report changes; normal simulation not repeated. [G04 report](reports/G04_PHYSICAL_INTEGRATION_REPORT_KO.md), [receipt](../evidence/g04/receipt.json).
- T10 source wrapper ready for authorized environment but runtime not verified. Upstream exact SHA exists, 94/94 paths, size match 23, mismatch 71; CRLF exact match proven for one sample, others not verified. No rights receipt and no actual 94 SHA/installed closure. T10 BLOCKED_ASSET_ACCESS_OR_RIGHTS; physical F01 BLOCKED_PHYSICAL_FAULT (no proven hook). Ch14 actual ORT BLOCKED_COMPATIBILITY/rights, fixture only. Historical Ch13 v53 10/10 basic PASS retained, not current T10. Profile C NOT_ACCEPTED. 
- G05 independent code/Mock+cube evidence reuse may proceed with T10 hold explicitly retained; full G04/G09 acceptance cannot be claimed until T10 is actually verified or owner formally revises scope. No MCAP yet, no WSL2 owner. CI ≠ Owner L3. main unmerged, publication HOLD.
