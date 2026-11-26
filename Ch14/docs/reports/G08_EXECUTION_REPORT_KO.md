# G08 — 실제 ONNX 강화학습 제어 연결·검수 최종 보고서
2026-11-26 | §14.8 후반 / 코드14-19 / T19 | SCOPED_PASS (CPU SMOKE_ONLY)

## 1. 개발 목표 및 원칙
G07 원본 actor/contract의 무결성을 유지하여 실제 ROS 센서→48D 관측→ONNX 12D action→제한된 관절 목표→물리 feedback을 두 엔진에서 검증했다. 기존 Ch12 핵심 계약과 bridge 재사용; Ch11 Gazebo 형상 등 9 exact source blobs, 원본 장 변경 없음. G07 모델 신규 학습/export 없음. G07 artifact15090667475, original ZIP c8defc1a154c3d0ec92ddd3a7fbd70f8d3b012dc21d375acde9f5c5f9be9641d. G08 각 실제 CI에서 reuse payload11 검증, CPU/RL locked reinstall, pip check, colcon build 수행. 기존 MuJoCo 성공 이후 정상 경로 재실행하지 않았다.

## 2. 증거와 원본 무결성
| Run | exact source | artifact | ZIP SHA256 | 내부 |
|---|---|---|---|---|
| [MuJoCo 45787876247](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45787876247) | 2ebd6ea9ea3277b0d62a80d05e489470544d8bb2 | 15101700809 | 8beeea041532c56c2a5710afbdb91203b4f8b4a9761840610f32d421f5dd50c5 | 14/14 |
| [Gazebo 45799511462](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45799511462) | f4ac6713a9ac8f4555ee263760e9b05249b0c30d | 15106482820 | 994662a7576f54a11a20104958b9839545ad80b6cbbfaf1268bf65b5d352cd33 | 25/25 |
| [Protection 45799639451](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45799639451) | a5ddffa3912ef925e5d4787aac12a8ae5cab1b94 | 15106449298 | 15f46c63bac990f65622ac3383a7406b05eb2426de9fff5bbcdf51db90d948e3 | 16/16 |
| [Clock 45799888629](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45799888629) | 1402937dc7466b5cae183455c261d8ddab34b481 | 15106658250 | 3abb9f819d49fd384d379a2c61f608dc648a348e1ef0a46947e93a136fe951f6 | 12/12 |

이번 리뷰에서 신규 원본 ZIP3개와 내부 53개 SHA256 직접 검증; 이전 MuJoCo14/14 유지. 원본 run/log/trace ZIP은 Actions artifact 보존기간에 종속. source-sha, stage complete exit0, G07 reuse11 확인. 보존 receipt는 evidence/g08_*_run_<id>.json. 

## 3. 실제 두 엔진의 독립 물리 결과
| 지표 | MuJoCo | Gazebo |
|---|---:|---:|
| wall measurement s | 8.000048593 | 8.000518701 |
| ACTIVE samples | 400 | 399 |
| sim rate Hz | 50 | 50 |
| independent complete DDS target groups | 400 | 399 |
| feedback pairs | 400 | 399 |
| direction dot positive | 52 | 393 |
| min base height m | .392472774 | .390414695 |
| max inference ms | .169344 | .144613 |
| maximum consecutive target delta rad | .024928791 | .095488182 |
| command reflects/expires | PASS | PASS |
| MuJoCo pause/resume | PASS | NOT_RUN |
| clean exits | 2/2 | 3/3 |
| forced cleanup | 0 | 0 |

Gazebo raw independent recompute: active measurement sim .78–8.74; all 399×12=4788 command values match status target exactly; max receipt difference .002980167s; 399 independently recomputed feedback direction dot values match report, positive393. 8064 joint rows (all unique q vectors), 238 odom and 809 IMU rows total incl startup; each of 12 command topics 403 messages incl startup/tail. JointState frame empty, IMU base_link, odom/child odom/base_footprint accepted by adapter. Float64 headerless per-joint monotonic receipt matching is not source timestamp proof. Direction correlation is not controlled causal latency or tracking accuracy; no tracking RMS or locomotion claim. Both engines ROS_POLICY_CONNECTION_PASS, SIM_CONTROL_PASS limited to fixed normal scenario with short smoke policy. 

## 4. 보호 계약 실제 MuJoCo
| 시험 | 관측 및 판정 |
|---|---|
| invalid IMU frame | 19 measured fault statuses and 19 independent same-target hold commands; inference count18 unchanged; PASS |
| writer conflict | 18 measured statuses, published count40 unchanged; no new DDS target after observed conflict; rearm rejected; PASS |
| explicit rearm | arming→active; PASS |
| one-call overrun | actual ORT call + test-only 35ms delay; measured 35.147894ms >20ms, new command0, target unchanged, recovery; PASS |
| disabled | 20 measured statuses, graph command publishers0/commands0; PASS |
Raw totals include transitions: invalid20, conflict20, active53, arming2, dry_run19, wall timeout2, overrun1. Overrun simulation time1.9s and zero targets at that stamp verified from raw. Enabled/disabled/plant all exit0. Conflict witness creates an extra publisher but sends no foreign actuator data; graph guard is not atomic lease or hard real-time safety. Hold can re-publish last valid position, not a new policy action. cmd expiry sets observation velocity command zero, not motor disable. 

## 5. Clock reset — independent DDS, synthetic sensors
Time 5.8→2.02s; 43 measured reset statuses/43 hold targets, new policy commands0, recovered ACTIVE43, old command cleared, arming after reset, exit0. Independent raw CLOCK_RESET to next arming window44 status rows, all inference count38 (same as preceding status); includes one additional transition row relative to report measurement window. Physical engine NOT_RUN. Not physical clock-reset acceptance. 

## 6. Debugging and environment
First Gazebo 45798971449 and protection 45799070950 exit100 at Ubuntu signed apt index size/hash mismatch; original artifact15106606988 /15105963572 internal4/4 each retained. G07 reuse passed, actual simulation NOT_RUN. Hypothesis mirror/cache inconsistency, no proved server cause. Isolated HTTPS/no-cache/bounded APT retries corrected the observed boundary without relaxing signatures/hashes, locks or policy code. Both targeted retries passed first after correction; no further rerun. Gazebo ordered shutdown controller→bridge→server service ACK and actual exit0, general Ctrl+C/native hang not resolved universally. No escalation to snapshot needed.

## 7. Final acceptance boundary
T19 CPU SMOKE_ONLY SCOPED_PASS. L0/L1/L2 scoped; L3 NOT_RUN. Both engines normal physical control, MuJoCo negative/pause, synthetic DDS clock reset only. Gazebo negative fault injection NOT_RUN, hardware stop/atomic ownership NOT_ACCEPTED, stable locomotion quality NOT_ACCEPTED, GPU NOT_RUN. No general shutdown guarantee. G00 rights/profile, G01 absolute semantic failures, legacy PR checks, G04 generic shutdown, owner WSL2 and G09 keep full release HOLD. Do not merge main. G09 preview only; no implementation until explicit request. 
