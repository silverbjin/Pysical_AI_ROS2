# G01 실제 YOLO 개발·검증 결과 — 전체 BLOCKED

## 범위와 실제 실행 증거
Run [45745101023](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45745101023), source ce2ee7a3cada354d6c2625201f2fdcb7258decf5, artifact [15082717992](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45745101023/artifacts/15082717992). ZIP SHA256 0537cf7ba76db50b918fe8d27a12c3304b810a8aa98781861591441d98ed32e9; 18/18 internal hashes verified. Actual T04 executed both models on all 20 frozen images. CI FAIL stage T04_acceptance, not infrastructure FAIL. T01 2x100 actual forward original run 45744146299 reused via 10/10 blob match, two raw CSV copied to Git with original blob hashes. T02 fresh verified exact ONNX SHA reused only within this run; T03 independent actual PASS 45742206902. G00/Ch01–13 not repeated. Static fresh-contract 3 tests and 4 target regression tests passed. Both actual negative contract groups 5/5 passed. Fixture 20/20 frozen SHA, 16 required positive, 4 unlabeled negative, 64 labels.

## Actual results
| Item | n | s |
|---|---:|---:|
| raw allclose (atol=1e-3/rtol=1e-3) |20/20|20/20|
| paired detections |30|41|
| unmatched reference/candidate |0/0|0/0|
| min bbox IoU |0.9999987535783985|0.9999986261405609|
| max score difference |1.2516975402832031e-6|7.152557373046875e-7|
| max raw abs |0.002593994140625|0.003570556640625|
| mean raw abs |1.4012150188591477e-6|1.3369375608363044e-6|
| positive required target |14/16|15/16|
| overall fixture images PASS |18/20|19/20|
| P/R (same for PT and ORT) |0.8667/0.40625|0.8780/0.5625|
| actual invalid-contract rejection |5/5|5/5|
| synthetic empty and nonsquare |PASS|PASS|

Precision/recall computed on 64 annotated objects with IoU .5, conf .5; incomplete COCO labels possible; not population accuracy or mAP. Four real unlabeled images are negative candidates, not absolute no-object proof. v8s emitted one matched detection on 127135. Synthetic empty test separately PASS.

## First semantic failure and decision
Image 463199 GT bus (class5, bbox [0,0,640,355.56]), both actual reference PT and ORT emit matched person/cell-phone detections but no bus at threshold .5. Image 392818 GT dog (class16, bbox [0,10.55,500,447]), n reference and ORT both label cat (class15, scores .528897225856781/.5288981795310974); s target passes. Evidence establishes shared semantic miss, not ONNX conversion mismatch. It does not establish precise visual/annotation validity or underlying low-confidence cause. No model/threshold/fixture modification. G01 required miss=0 unsatisfied; T04 numerical/bbox parity SCOPED_PASS, T04 semantic FAIL, G01 BLOCKED. No full rerun for same failure. Next bounded diagnostic: the two frozen images only, inspect original GT/source and top raw class scores/IoU at same threshold, compare both baseline/ORT. If no code/label error confirmed, request owner decision on pedagogical acceptance scope or separately approved model change; no cherry-pick, no training, no threshold weakening. Retain all three failures.

## Release and branch
Draft PR #206. Legacy Book Lab Acceptance document preflight failed independently due to Ch07 source missing in sparse checkout (runs 45744271653 and 45745105028). Main unchanged. User authorized merge only if G01 succeeds; condition not met. External Ultralytics AGPL and fixture publication rights not approved. No third-party weights, ONNX binaries or source images redistributed. Technical ONNX parity may be reused by exact binary/source contract but full G01 not passed. G02 preview only, see docs/G02_NEXT_WORK_PREVIEW_KO.md. Owner WSL2 NOT_RUN.
