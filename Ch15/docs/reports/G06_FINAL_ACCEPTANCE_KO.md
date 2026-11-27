# G06 최종 인수 — PASS_SCOPED_G06_T15
2026-11-27 KST / Draft PR #208 / main merge HOLD.
## 1. 실제 실행 및 증거
- V1 source 75c72106be3c447e296c424974159da7a310e333, [Run 45951984368](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45951984368), job140349724495, artifact15177381140, ZIP122be688f7cf37b1f87c96d499d2cb687c013c29db5557cbace500fe9f40c152, 7/7 internal hashes. Clean 2 package build, explicit 5/5 unittest, installed RViz config parse2/2, launch --show-args. Actual 65 captured messages.
- V2 coverage source 409d492ed327a8c518a364fa3c51a2106bb562cc, [Run 45952218641](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45952218641), job140350477722, artifact15176778952, ZIP ad7313e2d33d645eddffb8ffa6fcd2143d55ed4cfda36c29a64ea4b73c089f37, 4/4 internal hashes. Same runtime source; only extra probe and CI mode. Actual 6 captures.
## 2. T15 quantitative
| condition | actual |
|---|---|
| valid baseline sphere | 10/10 ADD, exact source stamp/frame/position, quaternion w1, lifetime1s |
| distinct target label | separate ID2; source/kind and MOCK label |
| invalid | NaN/wrong frame/stale/wrong epoch rejected; DELETE IDs0/2 |
| transition/expiry | epoch switch and receipt expiry DELETE0/2 |
| replay mode | REPLAY with original MOCK source/profile, target ghost0 |
| actual clock rewind physical-shaped | 10s ADD0/2→9s DELETE0/2, after clock11s no ADD |
| actual clock rewind replay | 20s ADD1→19s DELETE1, after21s no ADD |
| graph | only target/status marker publishers plus ROS infrastructure; no control topic or service, clean 4 node exits |
| install | both RViz configs and launch XML installed/parsed; only MoveCamera/Select tools |
## 3. Learning and scope
First accepted baseline reused rather than re-run; the only missing witness was actual time reversal, so two DDS no-motion sessions isolated the behavior. Fixed ID0/2 target and separate status ID1 avoid collisions; DELETE is explicit in addition to lifetime. Rewind fails closed until process restart. G06 actual fixture test does not constitute a real physical simulation or RViz GUI visual acceptance. PHYSICAL fixture uses existing T11 source RGBD_COLOR/position-only contract; no artificial manipulation pose. G05 replay data only includes mission state/event, so no fabricated target or safety. RViz GUI/optional Foxglove and WSL2 L3 NOT_RUN. G04 original native FAIL and G05 accepted PINs preserved; Ch01–14 tree lock check actual PASS. G07 next.
