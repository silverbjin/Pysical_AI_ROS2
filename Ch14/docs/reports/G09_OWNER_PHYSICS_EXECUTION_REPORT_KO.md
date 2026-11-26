# G09 실제 원샷 물리 옵션 최종 검수 보고서
2026-11-26 | OWNER_READY_HEADLESS_SCOPED | LINUX_REHEARSAL_ONLY | L3 NOT_RUN.

## 실제 근거
Workflow run [45816276822](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45816276822), workflow commit 4a4c55eb10f25e231785ef35fb66c75216f52824; actual bootstrap/source PIN 6c458e345236b124c9aa60f65788f35cfed74e62, same as successful build run45815645513. Three independent jobs all SUCCESS. Actual raw URL cmp, same SHA, no GHCR credentials for perception, exact G07 original ZIP from artifact15090667475 and 11 payload checks for both RL engines. All owner result stage complete, exit0, actual==requested SHA, owned container absent. No previous model/ROS controller/lock changes, no new RL training/export. Scope is new owner entrypoint input acquisition, isolation, actual runtime, exit and archive; no broad historical test reruns.

| option | artifact | outer hashes | owner tar hashes | tar SHA256 |
|---|---:|---:|---:|---|
| perception | 15116041923 | 31/31 | 25/25 | 79a0b26bf64fc24475aae60be5a57e44eb843bd0576c3fe079356221904d9435 |
| mujoco | 15116137030 | 28/28 | 21/21 | 389f9c5e137796294bf4ed2d6c80851d8681d4e0874118f4da572735e9542582 |
| gazebo | 15116306486 | 39/39 | 32/32 | d40b2f8f1352620047b492551ff335c8aa65802492a11b8e15de8a430875dda0 |
ZIP SHA256:
- perception: b8b462dd69c7fae4b069ea417776dd3e0dc440b8a7faa24396f49570a898b3cc
- mujoco: 8c700b3d7697eb836831e52a430cc1f7374f5a5a92b75d968797e08cdbe277c1
- gazebo: a4ce259ed181337301dcb651910e5462f3ffc06e924ce09f5e6f5f18fa98af7a
All three ZIP and nested tar SHA + coverage and byte equality to extracted contents independently verified. 98/98 outer manifest entries for physical matrix; nested 78/78. Build positive+negative run outer35/35, nested20/20+2/2 retained. Combined counts refer to archive manifest entries, not unique source files.

## actual result
| metric | perception | MuJoCo | Gazebo RL |
|---|---|---|---|
| semantic + geometry | 10 normal +3 resume PASS | N/A | N/A |
| active / matched / feedback | N/A | 400/400/400 | 399/399/399 |
| control rate | N/A | 50Hz | 50Hz |
| min body height m | N/A | .391139 | .392227 |
| max inference ms | N/A | .173242 | .105950 |
| command expiry | N/A | PASS | PASS |
| pause/resume | PASS | PASS | NOT_RUN |
| owned child exits | 4/4 zero | 2/2 zero | 3/3 zero |
| forced cleanup | 0 | 0 | 0 |
Perception first person confidence .831025, bbox IoU .921887, RGB-depth alignment .993447, independent point [2.2531597614,-.0858891316,.9409519571] m in odom; actual pause no new result, resume3. Not absolute G01 semantic acceptance. Gazebo RL headerless command receipt matching not source timestamp latency. RL smoke policy not stable locomotion quality. G08 negative contracts already preserved, not repeated. No claim that all four options were run sequentially in a single CI invocation. User WSL2 --check all can execute four independently checked routes once and review original results. Native WSL2 GUI is outside this headless candidate. No main merge/full release.

## User intake pin
6c458e345236b124c9aa60f65788f35cfed74e62. Bootstrap hash 0939ce653d896fb84a381e494600d77ce1cbbafd95e4aa86618cff33b7c2e30f. See G09_WSL2_OWNER_ACCEPTANCE_KO.md.
