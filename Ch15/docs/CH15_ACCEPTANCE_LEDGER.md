# Ch15 인수 원장
기준 main 1931cac92585fc155357880b584c72c76d67257c. Ch01~14 불변. 공개 소스 개발 승인, 출판/외부 모델 재배포/main merge HOLD.
| Gate | 상태 | L0 | L1 | L2 | L3 |
|---|---|---|---|---|---|
| G00 | SCOPED_MOCK_CPU_READY; physical asset/rights pending | SCOPED_PASS | SCOPED_PREFLIGHT | NOT_RUN | NOT_RUN |
| G01 | T01/T02 scoped | PASS | NOT_RUN | NOT_RUN | NOT_RUN |
| G02 | SCOPED_PASS | PASS 6 pure/IDL tests | SCOPED_PASS T03–05 | NOT_RUN | NOT_RUN |
| G03 | MOCK_MISSION_PASS; T06–09 scoped | PASS 16 pure tests | SCOPED_PASS | NOT_RUN | NOT_RUN |
| G04 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G05 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G06 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G07 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G08 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G09 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
- G00/G01 CI 45853673522: static 7/7, negative drift/assets, actual mock preflight, native SDF Valid. G00 physical assets/rights/closure HOLD. Previous automatic repeat 45855234520 recorded, workflow dispatch only.
- G02 runs 45855381985 and 45855811717, source d908f219... and e22c4fb5..., original receipts evidence/g02_ci_receipt.json. 4 package builds, eight IDLs, DDS 3/3 accepted + three reject, QoS 10/0/S10, independent missing predicates, short deadlines, latched reject. G03 start/cancel/reset scoped now verified; true safety latch reset G08.
- G03 original run 45857297181 overall FAIL (D01 init collision), T06 8/8 actual PASS and 16 pure tests. Normal fix run 45857717821 PASS, ready+7/7, accepted/terminal 4/4, 35 ticks P95 1.042921ms max 1.17032ms, 5/5 children exit0, full physical false. Target/cancel/invalid run 45858159748 PASS, actual typed DDS 10/10 negatives, wrong epoch 81/0/0, operator cancel 79.961972ms exact UUID, 11/11 children exit0. Three original ZIP SHA256 and 56/56 inner files verified. Source pins distinct; normal full run not repeated after targeted refactor. [G03 report](reports/G03_FINAL_REPORT_KO.md), [receipt](../evidence/g03/receipt.json). 
- G04 next: source/rights closure required for native basic. No physical full success (Profile C NOT_ACCEPTED). CI ≠ Owner L3. main unmerged. No MCAP yet; G05 reuse raw normal JSONL. No external asset distribution.
