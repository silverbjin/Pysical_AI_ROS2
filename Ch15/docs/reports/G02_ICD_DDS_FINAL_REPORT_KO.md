# G02 최종 개발·검수 보고서 — ICD, DDS, Readiness
2026-11-27 KST. Ch15 §15.2, C03–C06 / T03–05. 기준 main 1931cac92585fc155357880b584c72c76d67257c, Draft PR #208.
## 1. 문제와 목표
G01의 순수 상태 전이 oracle만으로는 실제 노드 연결, QoS, Action 결과, 안전 제어권을 보장할 수 없다. ROS 메시지 계약을 설치 가능한 인터페이스로 정의하고 독립 mock 프로세스에서 실증한다. 기존 Ch13 native owner 및 Ch14 모델/정책은 사용하지 않는다.
## 2. 개발 구조
ch15_interfaces: 2 actions, 1 service, 5 msgs. ch15_adapters: mock servers, QoS, pure contracts. ch15_safety: readiness, watchdog, arbiter. ch15_mission: launch default auto_start=false, executor는 G03. 자세는 map/frame/finite/unit quaternion; timeout 0<t<=10. Readiness endpoint/TF/sensor/heartbeat/owner/optional lifecycle, 3 samples. Watchdog steady 50ms, scan source 300ms, receipt 1s. Arbiter sole /cmd_vel 20Hz, heartbeat TTL 150ms, true latch. No full physical success. Native Ch13 interface separate.
## 3. RED / GREEN / REVIEW
RED local import error 1 (contracts absent). GREEN 4 pure tests, remote blob matches local: contracts 2860a9b758d9a8dfe3bf7145910b4ae961e401cd, tests 9fd3375e32cb3afe80c6aa2d3ee34d91020ce71a. CI additionally 2 IDL checks. Initial installed DDS run passed; review identified deadline-after-feedback-delay and readiness-recovery-versus-latch holes. They were code-review findings, not actual prior failed runs. Minimal correction: check deadline before state mutation; subscribe fresh nonlatched SafetyState, separate readiness from motion authorization. No threshold changes. Targeted boundary run, no repeat of accepted QoS/IDL. A prior G00/G01 workflow did auto-trigger one extra time, recorded; changed to dispatch-only, not deliberate regression. Shared legacy document CI unchanged.
## 4. Actual evidence
| Test | Result | Evidence |
|---|---|---|
| T03 | 8/8 interface show; four packages built | run 45855381985, 12.2s |
| Mock actions | invalid 3/3 rejected; normal nav/pick/place 3/3 status4; feedback 4/1/1 | original DDS log |
| Gait | crawl/trot/stand 3/3 observed; invalid 1/1 rejected | original DDS log |
| T04 | BE 10/10, incompatible REL 0/10, TL late S10 | original DDS log |
| T05 startup | six predicates missing; observed two zero Twist samples; duplicate graph owner blocked | original DDS log |
| T05 independent | TF/lifecycle/sensor/heartbeat/server 5/5 individually missing blocked | targeted run 45855811717 |
| T05 ready | 1.019605452 wall s (<15s); pure gate enforces 3 consecutive | targeted log |
| Deadline | pick/place 0.01s status6 ABORTED, next 2s status4 SUCCEEDED; nav prerequisite status4 | targeted log |
| Latch | false heartbeat recovers readiness only; nav/pick rejected, latch retained | targeted log |
| Cleanup | baseline five / targeted three children, exit0, force0 checked by harness | job exit0 and artifact result JSON |
The independent readiness probe uses controlled DDS scan/heartbeat/TF and lifecycle service fixture; this is not an actual Nav2 lifecycle/physical fault validation. T03/T04 unchanged source closure reused; mock server was corrected and affected action paths verified in targeted run. G02 reset service rejects every request without G03/G08 verified terminal-idle/stop/fresh contract. Actual start service and active-goal reset behavior remain downstream. This is G02 L0/L1 scoped acceptance, not full T06–T20, L2/L3.
## 5. Traceable source and artifacts
Baseline d908f219551ef2cfc24c75c4eb3c0d72b2969e93 / [run](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45855381985) / [artifact 15135003659](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45855381985/artifacts/15135003659), 21603 bytes, service ZIP digest f7a5ee383651652ee95d19ca878489751b3337b736b8a06ed5f0f60b2406a211.
Targeted e22c4fb5f7a77fe9a97eaf25bd6e8bbac3d37e8c / [run](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45855811717) / [artifact 15136141827](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45855811717/artifacts/15136141827), 17413 bytes, service ZIP digest 7169aa7c3f7dc1c45dba91a7937a47e5b787f54913c3c0d53a6ee573578b7aa0.
GitHub job conclusions and actual logs inspected. Artifact metadata inspected, not downloaded/rehashed independently. Internal checksums produced in workflow, not independently reopened. Both expiry 2026-12-26 UTC. Compact evidence receipt checked into Git. No secret, model or raw physical bag.
## 6. 교육 해설
Action 수락≠완료: UUID/feedback/terminal. Service 수락≠상태 전환: gait_state를 확인. QoS requested/offered: BE publisher cannot satisfy REL subscriber; TL late joiner retains last state. Readiness≠safety release: heartbeat false cannot clear a previously latched fault. Stop topics and real command owner separate. Tiny timeout tests show logical state cannot be updated after deadline; next normal goal verifies that failed pick/place did not consume state. Fixture counts are not reliability guarantees for arbitrary networks.
## 7. G03 handover
Reuse installed interfaces and mock DDS source at targeted pin; implement async supervisor (exact UUID, cancel-before-accept, terminal wait, late result rejection), mission/epoch target contract and BT 10Hz, start/cancel/reset with explicit terminal-idle witness, full mock mission source label. Reuse successful T03/T04/T05 where closure unchanged. G03 must test changed Action interfaces/runtime behavior; do not re-run all earlier Gate suites. No physical full mission, no Ch13/14 changes, no main merge. G00 physical asset/rights HOLD. G03 entry ready, owner WSL2 not ready.
