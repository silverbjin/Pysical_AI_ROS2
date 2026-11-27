# Ch15 인수 원장
기준 main 1931cac92585fc155357880b584c72c76d67257c. Ch01~14 불변. 공개 소스 개발 승인, 출판/외부 모델 재배포/main merge HOLD.
| Gate | 상태 | L0 | L1 | L2 | L3 |
|---|---|---|---|---|---|
| G00 | SCOPED_MOCK_CPU_READY; T10 asset/source preflight PASS; runtime pending | SCOPED_PASS | SCOPED_PREFLIGHT | NOT_RUN | NOT_RUN |
| G01 | T01/T02 scoped | PASS | NOT_RUN | NOT_RUN | NOT_RUN |
| G02 | SCOPED_PASS | PASS 6 pure/IDL tests | SCOPED_PASS T03–05 | NOT_RUN | NOT_RUN |
| G03 | MOCK_MISSION_PASS; T06–09 scoped | PASS 16 pure tests | SCOPED_PASS | NOT_RUN | NOT_RUN |
| G04 | PARTIAL_PASS_T11; T10 ASSET_SOURCE_PREFLIGHT_PASS | PASS 13 baseline +3 targeted | SCOPED_PASS cube + native 8-package build/install | T11 PASS; T10 NATIVE_L2_FAIL (RED3) | NOT_RUN |
| G05 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G06 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G07 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G08 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G09 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
- G00/G01 CI 45853673522: static 7/7, negative drift/assets, actual mock preflight, native SDF Valid. G00 physical assets/rights/closure HOLD. Previous automatic repeat 45855234520 recorded, workflow dispatch only.
- G02 runs 45855381985 and 45855811717, source d908f219... and e22c4fb5..., original receipts evidence/g02_ci_receipt.json. 4 package builds, eight IDLs, DDS 3/3 accepted + three reject, QoS 10/0/S10, independent missing predicates, short deadlines, latched reject. G03 start/cancel/reset scoped verified; true safety latch reset G08.
- G03 original run 45857297181 overall FAIL (D01 init collision), T06 8/8 actual PASS and 16 pure tests. Normal fix run 45857717821 PASS, ready+7/7, accepted/terminal 4/4, 35 ticks P95 1.042921ms max 1.17032ms, 5/5 children exit0, full physical false. Target/cancel/invalid run 45858159748 PASS, actual typed DDS 10/10 negatives, wrong epoch 81/0/0, operator cancel 79.961972ms exact UUID, 11/11 children exit0. Three original ZIP SHA256 and 56/56 inner files verified. [G03 report](reports/G03_FINAL_REPORT_KO.md), [receipt](../evidence/g03/receipt.json).
- G04 T11 run 45910585983 SUCCESS at 468e02849613ee3b26c389078c8989643380db3c. Actual Harmonic 10/10 normal unique stamps, max 2.045876541mm, min IoU .9216202813, skew 0ns, invalid depth 3/3 + actual occlusion 3/3 blocked, command publishers 0, detector/TF/bridge/Gazebo exit0 force0. Normal sensor is actual; invalid-depth copied real-frame NaN fixture; actual occlusion uses native set_pose. Position-only. 13 pure tests (8 native/compatibility,5 cube); 3 packages build 15.9s. Targeted native fixture run 45910956651 SUCCESS 3 tests, source ddeddf51e12524bb0323166a87c547742a8b578f. ZIP hashes and 25+3 inner files independently verified. T11 source closure unchanged by subsequent native adapter/report changes; normal simulation not repeated. [G04 report](reports/G04_PHYSICAL_INTEGRATION_REPORT_KO.md), [receipt](../evidence/g04/receipt.json).
- T10 owner validation approval + actual asset/source preflight PASS: run 45911815970, artifact 15161115377, 94/94 final SHA256, 23 direct +71 exact CRLF, 97,439,027 bytes, current original freeze 407 sources +94 assets write/verify PASS, lock free, owned matches empty. Original ZIP and 9/9 inner hashes verified. Original lock unchanged. Current native build/install and level2 basic L2 NOT_RUN; physical F01 BLOCKED_PHYSICAL_FAULT, actual Ch14 ORT still BLOCKED. Historical v53 remains separate. [T10 recovery report](reports/G04_T10_ASSET_RECOVERY_REPORT_KO.md).
- G05 independent code/Mock+cube evidence reuse may proceed with T10 native execution pending explicitly retained; full G04/G09 acceptance cannot be claimed until T10 is actually verified or owner formally revises scope. No MCAP yet, no WSL2 owner. CI ≠ Owner L3. main unmerged, publication HOLD.

- T10 native CI RED1 45916811032 (pip boundary), RED2 45918686561 (exact BT Debian versions missing, exit100); Python pip/system/EGL actual PASS and 94/94 preflight PASS in RED2. Artifact 15163184267 original ZIP +22/22 inner hashes verified. Build and L2 NOT_RUN. Supplemental signed snapshot recovery prepared; no physical acceptance. [Debug report](reports/G04_T10_BT_APT_SNAPSHOT_DEBUG_KO.md).

- T10 RED3 run 45919308935, artifact 15163622279 ZIP/72 internal hashes verified: signed BT snapshot five exact pins, 8-package build, 75 module install audit, 407 source/94 asset freeze & stage PASS; actual basic L2 FAIL, 3/10 checks, forbidden RR_calf:world:WAITING engine exit1 before VISION_EXPIRED; bag closed, residual PASS. Historical Nav2 1.3.13 vs actual 1.3.14; one parity candidate prepared, not a proven cause. [Debug report](reports/G04_T10_NATIVE_CONTACT_DEBUG_KO.md).
