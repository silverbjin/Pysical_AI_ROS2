# Ch14 개발 재개점 — 2026-11-26

승인 저장소 silverbjin/Pysical_AI_ROS2, main base 9431fb535ce7a51416c19c4395fb2ba3fabdad40, 개발 feat/ch14-ai-deployment. 이 문서 직전 head 237688eae533b7cfbd57e39a5206e39d8ed4760b. 기준 대비 44개 변경 모두 Ch14 또는 .github/workflows/ch14-g00.yml, main 동일 확인. G00 전체 BLOCKED, G01 foundation SCOPED_PASS / 전체 BLOCKED, G02~09 NOT_STARTED.

## 완료 단위 및 증거
- f01dfa3c2973c94a85e04c096223bd7721f4ce39: 사용자 승인 반영, S2 19개 원고 추적, G00 감사. S1/S3 전량 직접 대조 미완료.
- 2a41906353027454bf32357615b53deef3b6cf3c: CPU preflight 구현. [최초 FAIL 45739048641](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739048641). artifact 15080153039.
- a2eedeb3532aec8a35490de3d55795776d6aaeb1: G01 independent foundation source + 12/12 local pytest PASS, source blob 대조. 미학습 Torch forward 및 합성 전후처리/계측 테스트. ONNX 실제 export/YOLO/ROS 미실행. 환경 Debian13/Python3.13이므로 target acceptance 아님.
- 3b3b636efeaceeb54166e663a4cf0f742230166f: nested wheel metadata 경계 수정. local 3/3; [두번째 FAIL 45739405822](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739405822) artifact 15080307846. 실제 nested 12개 확인, 다른 JSON Header 오류 확인.
- a937bd43efe0bca4f4d4eeee7f2d0796ef2d951a: 공식 HF YOLOv8n/s revision 및 publisher expected SHA, 다운로드/검사 스크립트 및 5/5 local regression. 실제 checkpoint 다운로드/로드 미실행. AGPL 배포 결정 필요.
- 237688eae533b7cfbd57e39a5206e39d8ed4760b: Header 수정 및 4/4 local regression, 이전 artifact SHA/내부 7개 검증, 46개 wheel의 exact candidate lock 보존, ROS base digest 고정. [retry 45739828134](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45739828134)는 이 기록 작성 시 in_progress. 기존 두 실패와 다른 원인을 수정한 1회 실행이다.

## 바로 다음 작업 (순서 유지)
1. retry 45739828134의 실제 결론과 artifact 확인. PASS 시 exact lock 및 cv_bridge/ONNX smoke/라이선스 메타데이터/apt 목록 검토 후 CPU lock으로 승격. FAIL 시 최초 미통과 단계만 확인하며 동일 원인 반복 금지. 성공한 wheel 해시/ABI 증거는 재사용.
2. G01 T03 actual export/parity 100 input과 결과 저장을 target CPU CI에서 검증. 현재 source 작성됨. G01 T01/02/04 YOLO backend/CLI/export/real fixture 20개는 아직 필요. 공개 배포 권리 확정 없이 모델이나 이미지 vendor 금지. 사용자 소유 원고 자체는 공개 Git에 넣지 않는다.
3. PPO 원본 ZIP 또는 명세 허용 smoke 1회, Ch07/11/12 권리와 Ch11 minimal closure, Ch13 TF 계약 등은 해당 Gate 이전에 확정. B의 모델 부재 때문에 독립 A 검수를 차단하지 않는다.
4. G02~G09는 명세의 의존성과 완료 조건대로. 새로운 증거 없는 반복, 범용 로봇 HW/파지/장기 학습 확대 금지. L3 최종 인수는 owner WSL2만.

이 checkpoint는 완료 선언이 아니다. Gate별 실제 결과 보고서와 commit으로 갱신할 것. main 병합 금지.

## 2026-11-26 갱신 — CPU profile 실제 PASS
이전 checkpoint를 역사로 유지. 현재 우선 근거 https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45742206902, source 1228072c5679b608756bfbd578b2c56cbcfe32e8, artifact 15081503468; 원본 ZIP/internal 25/25 SHA 확인. CPU profile PASS, T03 actual 100 input PASS, 12 foundation PASS. 45-wheel cpu.lock.txt 승격(artifact exact SHA), setuptools 68.1.2 inherited; graph 197/182 zero. 실패 45739828134 원본 9/9 확인. 다음: T01/02/04 actual YOLO가 남음; publisher weight expected SHA는 확인했으나 다운로드/권리/평가 fixture 미확정. 기존 CPU/T03 재실행 불필요(관련 변경 시에만). G00 overall BLOCKED, G01 scoped; G02~09 NOT_STARTED. Main 및 기존 챕터 변경 금지.

## G01 actual YOLO update
PR #206 Draft, commit fcab9108a748cdc6e77ae0918655b89336295b96, run 45744146299: actual T01/T02 scoped PASS, T04 blocked TLS; artifact 15081689764 internal 13/13. Targeted fixture transport correction and source-identity reuse implemented. Legacy book PR doc preflight failure 45744271653 independently caused by missing Ch07 sparse checkout; no runtime pilots. No main merge before full G01 acceptance, release rights and PR checks resolved. G02 preview docs/G02_NEXT_WORK_PREVIEW_KO.md.

## G01 second failure boundary
Run 45744752315: transport resolved; 20 image hashes and fixed manifest, T01 reused (10/10 blob), fresh T02 exports both seed parity PASS but differ in bytes from prior export. Guard rejected; T04 NOT_RUN. Artifact 15082926406 verified 10/10. Freeze fixture and classify actual fresh T02 without claiming old binary reuse. New targeted run only. Do not merge until full actual T04, rights and legacy PR check resolved.

## G01 actual T04 result and bounded stop
Run 45745101023 source ce2ee7a3cada354d6c2625201f2fdcb7258decf5 FAIL stage T04_acceptance, artifact 15082717992 ZIP/internal 18/18 verified. T01 reused source 10/10, T02 fresh actual export/seed parity n/s PASS, T03 historical actual PASS. 20 fixed image pairs per model raw allclose and matched boxes (30/41, unmatched zero) PASS. Required target misses: n 2 (463199 bus, 392818 dog→cat), s 1 (463199 bus). G01 overall BLOCKED; no threshold relax, no fixture change, no repeat of whole suite. Next targeted diagnostic two IDs only; owner acceptance decision if no code/label error. Legacy PR #206 document preflight fails due baseline sparse checkout, separate fix authorization. External release rights pending. G02 preview only; main unchanged. Actual raw T01 CSV retained with source-identical Git blobs.

## G01 bounded diagnostic completed
Run 45746373267, source 5cd0eb2e4941b90d023977e3344c9008a846e2f2, artifact 15082449287 verified 6/6. Original PT raw target score below .5 for bus both and dog n; independent NMS reproduces. No new GT miss across all 64 labels reanalysis. Final educational CPU deployment scope SCOPED_PASS; original absolute semantic FAIL and full G01 BLOCKED retained. G02 independent CPU comparison allowed, actual full integration/main merge held, release rights/legacy PR/owner outstanding. Read G01_ACCEPTANCE_SCOPE_KO.md and evidence/g01_two_image_run_45746373267.json. No redundant rerun.

## G02 CPU comparison checkpoint
Run 45748461194 source a9d7e7d3514a2a9ab2698ef66dc8f91b5fd81bbd SUCCESS, artifact 15084542683 internal 27/27. CPU T06 scoped PASS, actual 800 timings independently recomputed, 40 raw/71 pairs/no new GT misses, historical G01 semantic failure retained. Separate OV lock graph 199/185 PASS; base CPU lock unchanged. First failure 45748144504 optional validator mismatch fixed without touching G00. See docs/reports/G02_CPU_EXECUTION_REPORT_KO.md, evidence/g02_run_45748461194.json and raw CSVs. T05 NOT_RUN, L1-L3 NOT_RUN, full G02 BLOCKED by G01 full/release. Main unchanged, PR #206 draft. Next G03 independent CPU perception implementation, strict actual Gazebo target semantics/TF/time/guards, no acceptance waiver. No redundant G01/G02 runs.

## G03 L0/L1 checkpoint
T07 actual ROS DDS burst 45750110277, T08 actual best-effort 49/50 and invalid boundaries 45750520212, reliable remaining 51/stale/order 45750895879, TF and clock actual final SUCCESS 45751287261 (16/16 hash), source 6a078a536cc4d3e9af6093a35ad7a5e770a58799. L0/L1 SCOPED_PASS evidence from different exact sources. No G01/G02 repeats. T07 subscriber age tail >300ms and publication heartbeat age distinct, no per-publish source trace for old T07. Ch13 exact geometry/contracts license preserved. G03 L2 candidate separate world person_standing, actual CI 45751598173 source 24305b1c4daa0e68522e8bc20317b33a672c2c71; pending at checkpoint; no L2 claim. Main/legacy PR and prior G01 absolute semantic blocker unchanged. Next exact failure boundary only, G04 after review.

## G03 L2 completed checkpoint
45751598173 SUCCESS, source 24305b1c4daa0e68522e8bc20317b33a672c2c71, artifact15086325815, ZIP/internal 21/21 verified. Actual Gazebo CPU L2 scoped PASS: 13/13 evaluated semantic/3D, source27 max86ms, pause/resume/exit0. L0/L1 historical scoped retained; G03 full release HOLD, G01 original absolute semantics unchanged, no main merge. Read G03_L2_EXECUTION_REPORT_KO.md and G04_NEXT_WORK_PREVIEW_KO.md. No redundant rerun; current DDS push phase final_faults only, select affected phase explicitly for future changes. WSL2 L3 NOT_RUN.

## G04 actual scoped completed checkpoint
Run 45755020128 source 0a94aebe5438df0b6de462b0f961299bb90f5b3e SUCCESS, artifact15086703629 ZIP/internal23/23. Actual 15/15 core, installed 4 packages, T09/10 atomic 17 (7 success/10 expected rejections), old snapshot proven in-flight heartbeat, n→s request61a66e9f1b0b40278ec501b5ed7ff10e gen0→1 in704.046ms, failures missing/corrupt preserved n/gen0, busy1; observed output gap719.808ms (includes probe), max source age286.909ms. T12 actual installed replay and Gazebo launch from /tmp, sim GT3/3, 4 source emits max123ms and clean all. No repeat G03 full suite; G03 narrow push triggers plus manual selector. G04 CPU L0/L1 and T12 L2 SCOPED_PASS, full release HOLD. Read G04_EXECUTION_REPORT_KO.md, LAB_14_5_GUIDE_KO.md, G05_NEXT_WORK_PREVIEW_KO.md. Main unchanged, G05 NOT_STARTED. Owner WSL2/GUI/GPU/ROS OV NOT_RUN. No model binaries published.
