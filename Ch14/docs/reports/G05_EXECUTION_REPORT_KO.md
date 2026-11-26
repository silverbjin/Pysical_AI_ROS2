# G05 실제 성능 계측 개발·검증 보고서 — 14.6 / T13

## 판정 및 기준
- G04 기준 0a28bd5bc0d7e96608e5bc82e208fe9599268529; 실제 검증 source 595e88a23856c9c791c227a189ea90388e0bb208. 원격 main 9431fb535ce7a51416c19c4395fb2ba3fabdad40 변경하지 않음.
- [Run 45758721447](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45758721447) SUCCESS, 05:00:14–05:05:57 UTC, job139703404979, artifact15089655249. ZIP SHA256 5ded84f952ff6a2bd1c9e64642bfa47a73c20a8deb9a2db0a90bbe864fac5e8a; 39/39 내부 파일 SHA/coverage 독립 검증. 23/23 unit/core regression (G05 8, G04 11, G03 4), 실제 설치 5 packages (9.59s). CPU lock 기존 사용, pip check 통과, 기존 고정 Jazzy/Harmonic 이미지/장면 재사용. CPU T13 L0/L1/L2 SCOPED_PASS; 전체 release HOLD. L3 NOT_RUN, optional GPU D N/A.
- 개정 원고 14.6.6 A Torch CPU FP32 sync, B ORT CPU FP32 sync, C ORT CPU FP32 async, D TRT FP16 async optional. 동일 YOLOv8n 원본/실제 export, 640×480 sensor, 640×640 network, confidence .5 / NMS .45, 2 threads, affinity 0–3, CPU quota max, Python3.12.3, nominal sensor10Hz sim, real 60 wall seconds each after 10 real DDS outputs warm-up. Same immutable world/mesh and identical input pixel hash across measured emitted results. Actual input delivery is variable, no claim of exact equal frame counts or fixed identical wall arrival rates.

## 구현 단위
T13-A ch14_ai_common/profiler.py: monotonic stage timing, finite/negative/reset rejection, bounded history, count reconciliation and RTF; python/profiler.py 교육 wrapper.
T13-B ch14_performance_monitor/monitor_node.py: independent DDS RGB/detection/heartbeat/debug subscriptions, observed clocks and RTF, source vs subscriber distinction. T13-C detector_node.py timestamps at synchronized callback receipt, queue, preprocessing, actual model forward, NMS, result wait incl geometry/annotation, publish; /debug/inference_latency, /debug/result_age, /debug/heartbeat_interval (Float32 ms), /diagnostics plus legacy /perception/diagnostics. /clock separate from monotonic wall. T13-D process CPU/RSS for detector/Gazebo/bridge/TF once per second; CPU% 100=one logical core, RSS MiB, no GPU claim. T13-E scripts/g05_actual_compare.py and g05_ci.sh, actual sequential independent launched Gazebo instances, fixed scene asset. Torch CPU only accepts pinned publisher PT digest, no Torch swap or arbitrary checkpoint. G03/G04 thresholds/guards/swap unchanged; no hardware. T13-F metrics/callbacks/resources CSV, observer/result JSON, 4 PNG plots, artifact hashes and summary CSV, manuscript-ready table.

## 실제 원고 표 (단일 CI runner, 2026-11-26)
| metric | A Torch sync | B ORT sync | C ORT async | D TRT FP16 async |
|---|---:|---:|---:|---|
| measured wall s | 60.025 | 60.003 | 60.019 | N/A |
| inference mean/P95 ms | 90.782 / 130.380 | 78.406 / 104.794 | 82.670 / 116.902 | N/A |
| pipeline mean/P95 ms | 95.686 / 135.808 | 85.337 / 112.150 | 95.667 / 132.099 | N/A |
| detector local ROS Age P95/max ms | 37 / 60 | 32 / 39 | 154.15 / 163 | N/A |
| source output count / Hz | 236 / 3.932 | 206 / 3.433 | 218 / 3.632 | N/A |
| observer RGB count / Hz | 317 / 5.281 | 303 / 5.050 | 303 / 5.048 | N/A |
| callback window / carry out | 237 / 1 | 206 / 0 | 219 / 1 | N/A |
| heartbeat miss >200ms (window) | 16 | 7 | 0 | N/A |
| heartbeat P95/max ms | 186.862 / 235.989 | 166.521 / 211.795 | 101.006 / 107.326 | N/A |
| output interval P95/max ms | 523.876 / 1027.707 | 614.099 / 1836.857 | 589.798 / 1060.004 | N/A |
| detector CPU% mean / RSS MiB mean | 111.60 / 432.39 | 107.35 / 269.40 | 128.29 / 283.00 | N/A |
| Gazebo CPU% mean / RSS MiB mean | 72.48 / 810.72 | 68.34 / 798.54 | 69.78 / 800.32 | N/A |
| RTF | .971219 | .971763 | .971675 | N/A |
| static person GT miss / source-observer matched | 0 / 236 | 0 / 206 | 0 / 218 | N/A |

All 660 emitted frames same pixel hash 09c3a902b0a49ca36469197faa94a7de369551fa6a8e3f23909c872f465c96d5; A/B and B/C exact class matched boxes (IoU>=.95, confidence diff<=.02), static scene target IoU>=.5, zero misses. Source 660 matched independent DDS outputs, no local-clock stale emit; no clock reset/invalid debug. A/B/C own four processes finished cleanly, launch exit0, worker joined. A→B inference speedup1.15785x (latency -13.63%), detector RSS -37.70%, but B output Hz lower than A (-12.68%); no blanket FPS improvement. B→C model inference +5.44%, source output Hz +5.80%, heartbeat misses7→0, max interval211.795→107.326ms, detector CPU +19.51%, RSS +5.05%. The async benefit here is executor responsiveness, not raw model acceleration. Queue mean A .009/B .008/C .823ms; C result wait 6.043ms vs B1.012ms. Actual wall pipeline contains overhead beyond forward. C max local ROS age163ms below300; output interval max1060ms >300, no uninterrupted output guarantee.

## Count reconciliation and clock caveat (important)
Window callbacks662, source emits660; A/C one source callback each emitted after window end. All window callback stamps eventually emitted, no unaccounted internal drops. Full process accepted/published 249/249,217/217,229/229, sum695/695; overwrite0, pending0/in-flight0, residual0. Observer RGB is separate BEST_EFFORT DDS observer, not sensor native publish count. Exact RGB stamps intersect callback stamps 222/196/201; observer-only95/107/102 and callback-only15/10/18. Thus pre-pair difference is not exact DDS loss and cannot assign a cause; synchronization, DDS receipt and observer sampling are distinct. This fixed scene did not saturate queue; G03 overload proof historical, no duplicate rerun.
A/B local ROS Age appears smaller than wall pipeline, despite RTF near.97. Sync callback can delay /clock updates, so node-local now may lag live sim clock. No independent per-output /clock snapshot retained (only observer first/last), no claim A/B result actually fresher or global Age<=300 certified. Measure independently synchronized clock at each emission for future freshness/age interpretation; do not loosen 300ms guard. G05 is scoped measurement/functional pass, not global safety timing acceptance. CPU percentage not normalized to total four cores. One static scene not general performance or accuracy, no multiple repetitions/statistical confidence claim.

## Additional regression failure (separate from G05)
Workflow trigger maintenance itself caused [G04 run45758721305](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45758721305), same source 595e88a23856c9c791c227a189ea90388e0bb208; artifact15089740118 ZIP a7c41360e0fa27057198b5dd6df630f3b5a9f121fb0e10fda82098c121f9233e, 23/23 verified. 15 core and 4 packages passed; actual replay PASS, actual sim 3/3 semantic+3D PASS, detector worker joined, bridge/TF/detector clean, launch parent exit0. Gazebo server stop replied true, but server did not exit after SIGINT5s then SIGTERM10s, SIGKILL exit -9. Workflow FAIL at sim shutdown. Previous G04 run45755020128 successful evidence is retained as historical only; latest G04 shutdown HOLD, not a G05 model failure. Exact root cause of Gazebo termination hang not established; targeted shutdown diagnosis before G06 deployment, no repeat all G04/G05. All three actual G05 launches independently clean. A code change or trigger correction does not erase failure; no main merge. Matplotlib Axes3D warning observed, 2D plots created; no 3D plotting claim.

## Evidence and reproduction
Original [ZIP artifact](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45758721447/artifacts/15089655249), retention30 days. Preserve downloadable raw archive externally; repository stores immutable hashes, summary CSV and report rather than third-party model/mesh binaries. All per-frame raw CSV, observer/callback/resource traces, plots in original ZIP. See evidence/g05_run_45758721447.json and evidence/g05_summary.csv. For exact source use 595e88a23856c9c791c227a189ea90388e0bb208, CPU lock, fixed image and assets. WSL2 final owner acceptance not run; G01 absolute semantics and release rights, G04 regression, legacy PR remain HOLD. Next G06 Docker CPU scope only after targeted termination boundary review. No redundant 60-second runs.
