# Ch15 인수 원장
기준 main 1931cac92585fc155357880b584c72c76d67257c. Ch01~14 불변. 공개 소스 개발 승인, 출판/외부 모델 재배포/main merge HOLD.
| Gate | 상태 | L0 | L1 | L2 | L3 |
|---|---|---|---|---|---|
| G00 | SCOPED_MOCK_CPU_READY; physical asset/rights pending | SCOPED_PASS | SCOPED_PREFLIGHT | NOT_RUN | NOT_RUN |
| G01 | T01/T02 scoped | PASS | NOT_RUN | NOT_RUN | NOT_RUN |
| G02 | SCOPED_PASS / G03 entry ready (mock only) | PASS 6 pure/IDL tests | SCOPED_PASS T03–05 | NOT_RUN | NOT_RUN |
| G03 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G04 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G05 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G06 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G07 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G08 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
| G09 | NOT_STARTED | NOT_RUN | NOT_RUN | NOT_RUN |
- G00/G01 CI 45853673522 static 7/7, source drift/missing assets exit2, actual mock preflight PASS, two native SDF Valid. CI checkout merge SHA 76bcd7be3194edf414fdb490905de7ac761b80f0; PR head 92f50d6c1dba7814c9952bce74da4e94bb510583. Legacy document CI 45853673245 success (pilots skipped). Unintended automatic repeat 45855234520 succeeded; old workflow changed to explicit dispatch, do not repeat.
- G02 baseline d908f219551ef2cfc24c75c4eb3c0d72b2969e93: run 45855381985 / artifact 15135003659. Four installed packages 12.2s; interfaces 8/8; three goal rejections/three SUCCEEDED, gait 3/1, QoS 10/0/S10, startup/ownership blocked, five owned processes clean via harness. 
- G02 targeted e22c4fb5f7a77fe9a97eaf25bd6e8bbac3d37e8c: run 45855811717 / artifact 15136141827. Four installed packages 20.8s; five independent readiness negatives; initial ready 1.019605452s; pick/place short 0.01s ABORTED, normal 2s SUCCEEDED, nav prerequisite SUCCEEDED, two post-latch goal rejections; three owned processes clean via harness. Source review and targeted fixes, not prior reproduced failure. Fixture lifecycle service and scan/heartbeat/TF are mock; native lifecycle and physics not claimed.
- T05 executor start/cancel service and real active-goal reset contract remain G03/G08; G02 reset intentionally refuses without verified terminal-idle witness. Action cancel/unconfirmed exact UUID supervisor T06, actual full BT mission T08, physical T10–11, complete six package build T12 not run. No new physical claims. See [G02 final report](reports/G02_ICD_DDS_FINAL_REPORT_KO.md).
- Profile C NOT_ACCEPTED. Mock SUCCESS ≠ physical success. G00 physical asset rights HOLD. CI ≠ Owner L3. GitHub artifact ZIP digest from service metadata, not independent ZIP byte rehash. Archive retention through 2026-12-26 UTC; public evidence contains only mock test data.
