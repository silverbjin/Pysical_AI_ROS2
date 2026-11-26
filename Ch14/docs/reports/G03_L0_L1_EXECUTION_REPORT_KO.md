# G03 T07/T08 실제 DDS 검수 종합 — L0/L1 범위 SCOPED_PASS
기준 spec 14-7/8 및 G03 preview. 기존 main 9431fb5 유지. 네 번의 CI는 동일 전체 반복이 아니라 실패 경계별로 분리: 45750110277 T07 actual pass + T08 49ms delivery unknown; 45750520212 actual 49/50ms pass and raw best-effort delivery missing; 45750895879 reliable 51/stale/order/recovery pass + missing TF source pass but independent DDS output not received; 45751287261 final TF/clock actual SUCCESS. All artifact ZIP SHA and 18/14/16/16 internal hashes verified. Actual installed 2 ROS packages; latest L0 4/4. All actual inference on original n ONNX exact SHA e8950e7e6edc29ee614a027ee7a07aa492afbda7f24faad049972be5b7c96546. No G01/G02 benchmark repeated. Source version for T07 0ad2b85; later changes only RGB-D, diagnostics/explicit reliability optional, source proof from earlier run retained. No blanket latest HEAD full-suite pass.

## T07 actual 30Hz burst, 240 frames, injected 150ms
| metric | sync | async |
|---|---:|---:|
| offered |240|240|
| callbacks |39|163|
| publish |39|39|
| overwrites |0 (not applicable)|123|
| heartbeat >200ms |39|0|
| max heartbeat ms |262.602167|101.036115|
| subscriber mean age ms |373.0758466|244.9371482|
| subscriber P95 age ms |1274.518327|284.432197|
| annotations received |35|33|
Actual async 163=40 started+123 overwritten, 40 completed=39 published+1 stale. Transport/callback loss before slot 240-163=77 not attributed to overwrite. Source latest heartbeat age <=300, actual per-publish source age trace not captured for original burst. Subscriber max age >300 due to end-to-end observation including observer backlog; do not certify entire subscriber age contract. Core deterministic 1→4 with exact 2 overwrites. Actual worker joined and exit0 both.

## T08 actual ROS DDS
Synthetic depth 2m, actual frozen RGB bus image 455085 and known static TF translation X=1. Observed point [0.95343994140625,-0.00314178466796875,2.0]. Actual BEST_EFFORT 49/50ms valid, bad depth/frame/K/RGB/future rejected, recovery; 51/stale not delivered and not accepted as protective pass. Explicit RELIABLE fault profile (not production default), 15/15 raw received, four pairs, 51ms all received no pair; stale matched but rejected, duplicate stamp rejected, recovery. Source emissions age 105.078074 / 92.427183ms. Final missing TF actual 3/3 pair and independent 2D bus receipts; zero target messages; TF_UNAVAILABLE3, source age 94.217242/94.658386/84.944187ms. Actual ROS /clock pause/rewind simulation of clock messages, 21 callbacks,20 accepts and publishes, CLOCK_PAUSED1,FUTURE1,CLOCK_RESET1; pause new output zero, new epoch resumed. Clean shutdown. This is L1 replay and synthetic depth; not Gazebo or physical range. 60s full end-to-end performance belongs G05; G03 burst 8s. No guarantee of hard RT. Read G03_DDS_DEBUG_01/02/03_KO.md and individual receipts. Final evidence Run 45751287261 artifact 15086175272 internal16/16; source 6a078a536cc4d3e9af6093a35ad7a5e770a58799. Fourth run source output discovery matched on both endpoints, shm1g, distinct 3 frames; avoids interpreting DDS loss as success.

## L2
T08-D actual semantic mesh scene candidate, independent depth silhouette GT, actual RGB/depth mask alignment, static optical TF and /clock, pause/resume and clean shutdown. Start only one bounded actual run from L1 completed source. New assets not published; no model/threshold changes. L2 actual success not yet recorded. Existing G01 absolute semantic and release rights/legacy PR blockers retained. Owner WSL2 NOT_RUN.
