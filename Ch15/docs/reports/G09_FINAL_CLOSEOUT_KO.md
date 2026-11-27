# G09 최종 통합 QA — 제한 범위 Linux 인수 준비
판정 `PASS_SCOPED_LINUX_ENTRYPOINTS_OWNER_L3_PENDING`. T20 전체/L3 승인 아님. 실행 PIN `70ed8b509809b09db26f57e4f9a7aea9f83d095c`, bootstrap SHA256 `40c306ac8cf2ff7e652e9b36e3f880f771e2f9276ec17a5589a5e149d403c606`. 문서/영수증 closeout commit과 실행 PIN 구분.

## 실제 CI
| 경로 | CI | 판정 | 실제 근거 |
|---|---|---|---|
| Contract | 45969586572 | PASS | 5/5, C24/CLI7/Q12/guide9 mapping; source drift/asset 미승인 exit2; design 실제 |
| Build | 45969586572 | PASS | 6 packages, 11 explicit unittest files, rosdep/import/launch |
| Mock | 45969586572 | PASS | COMPLETED, exact terminal4 UUID, 23 events/134 statuses replay, clock160, control0 |
| Joint | 45969586572 | PASS | 4800 actual steps +800 synthetic LPF, scoped independent |
| Fault F06 | 45969586572 | PASS | 3 picks, 35 events, ABORTED; other 4 actual G08 cases reused |
| ICD | 45970210242 | PASS | 8 IDL and actual DDS |
| Markers | 45970210242 | PASS | actual marker and clock probes |
| Cube | 45970803433 | PASS | actual RGB-D normal10/invalid3/occluded3, max error2.045876541mm, min IoU .9216202813, stamp skew0; signal regression3/3; 4/4 exits0 force0, graph0/container0 |
| Physical basic | 45943468828 | underlying historical PASS | exact V6 downstream, assessor10/10, Ch13 tree same; new positive owner wrapper NOT_RUN |

V1/V2 cube function GREEN exit RED remains recorded. V2 traceback proves detector publish after context invalidation; RMW rollback alone did not resolve. V3 dedicated signal stop flag, no native handler, callback finishes before context shutdown, exception propagates. All detector thresholds/frames and physical safety contracts unchanged. [V1 RED](G09_V1_CUBE_SHUTDOWN_RED_KO.md), [V2 RED](G09_V2_CUBE_LIFECYCLE_RED_KO.md).

## 증거 및 브랜치
Public ZIP 10/10 SHA256, 163/163 manifest entries independently checked. Original evidence archives 12/12 and 258/258 file hashes verified by CI; raw tar not locally downloaded. Failure archives included. Graph/containers zero for passing applicable isolated paths, no global WSL2 residual claim. 14/14 protected chapter trees and existing 7 tags unchanged. [receipt](../../evidence/g09/final_receipt.json), [source audit](../../evidence/g09/source_closure_audit.json). No raw asset/MCAP redistribution; public summaries only (historical G08 incident remains recorded).

## 남은 인수
Actual WSL2 L3, native positive wrapper and complete all sequence NOT_RUN. Physical basic prerequisites validated environment/asset approval and original 94 asset bytes required; negative preflight verified. Faults wrapper actual F06 representative; other four G08 accepted probes unchanged, not claimed actual all-wrapper. External bag analysis and Git lab wrapper separately not run (normal record/replay decoder and earlier Git evidence reused). GUI manual WSLg NOT_RUN, excluded. Manuscript mapping C10/C21/C24 differences documented, manuscript edit not performed. Full pick/return/place and physical F01 BLOCKED; publication/license/redistribution HOLD. Owner evidence and separate approval before main merge. [WSL2 guide](G09_WSL2_OWNER_ACCEPTANCE_KO.md).
