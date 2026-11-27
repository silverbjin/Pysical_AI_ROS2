# 15.5 미션 기록·분석 실습 (G05)
WSL2 Ubuntu24.04/Jazzy, source /opt/ros/jazzy/setup.bash 및 별도 Ch15 install/setup.bash. G03_INSTALL은 해당 install의 절대경로. 빈 로컬 ROS domain을 선택한다. 실제 로봇/기존 Ch13 프로세스와 혼용 금지.
```bash
bash Ch15/scripts/record_mission.sh normal "$HOME/g05-normal" 76
python3 Ch15/python/bag_to_csv.py "$HOME/g05-normal/bag" "$HOME/g05-normal/analysis"
python3 Ch15/python/plot_mission.py "$HOME/g05-normal/analysis"
bash Ch15/scripts/replay_mission.sh "$HOME/g05-normal/bag" "$HOME/g05-normal/replay.json" 79 76
```
F01/F06은 별도 새 출력 및 domain으로 반복한다. 실제 Mock 장애 주입의 기록만 검증하며 G08 안전 복구는 별도. MCAP recorder가 먼저 기동하고 10개 필수 토픽 discovery 후 start 서비스 호출. 64MiB 제한, 8MiB 분할, 60초 기록 budget. /clock, odom, joints 등 없는 데이터는 N/A. typed Event/Status와 String demo reader는 분리. START/END, producer seq, Goal UUID, record/ROS/steady 시간을 비교한다. Energy는 effort/velocity 없으면 null; 실제 전력 추정 금지. Replay는 별도 domain에서 Event/Status와 생성 /clock만 허용; command/action/기록 clock 재생 금지. 원본 bag은 로컬 보존, 공개 저장소에는 해시 영수증 및 분석 결과만.

기록 실행기는 최소 4개 사용 가능한 CPU가 필요합니다(안전 pair/recorder/worker 분리). 실제 scan과 false heartbeat가 충분히 진행된 뒤 Arbiter를 기동합니다. 이미 latch 상태이면 미션을 시작하지 않으며 자동 reset하지 않습니다. `startup_stages.json`, `arbiter_native_trace.json`, `watchdog_native_trace.json`을 분석하십시오.

V4의 기록기 구독은 continuous telemetry Best Effort, MissionEvent 및 /tf_static Reliable로 구분합니다. 원본 제어 QoS는 그대로입니다. Event 무결성은 반드시 100% 일치해야 하고 sampled telemetry는 모든 필수 토픽과 마지막 상태를 검증합니다. `mock_native_trace.json`의 actual goal gate와 `arbiter_native_trace.json`의 publisher 시간을 대조하십시오.

V6에서는 G05 전용 Scan 노드가 독립 SingleThreadedExecutor에서 원본과 동일한 10Hz LaserScan을 발행합니다. 기존 Mock Action 서버는 Scan publisher를 제거하고, 실제 `/scan` 발행자 1개를 확인합니다. Fast DDS 비동기 모드는 G05 스크립트 내에서만 적용됩니다. F01은 실제 양의 `/ch15/cmd_vel_in`을 관측한 뒤 Scan 발행을 중단하며 명령을 생성하지 않습니다. 7개 프로세스 정상 종료와 `scan_source_trace.json`을 확인하십시오.

V7 검증 후보: G05 스크립트에서만 Cyclone DDS 사용(`sudo apt install ros-jazzy-rmw-cyclonedds-cpp`). G03/G04 설정은 수정하지 않습니다. `executor_native_trace.json`에서 실제 미션 실행기의 ready_count, 수신 age, safety latch와 start 결과를 확인하십시오. V7 실제 인수 전까지 후보입니다.

V7 actual normal/F01/F06 recording and analysis PASS. Replay allows only two data topics as before. ROS bag player internal `/events/read_split` must be exact `rosbag2_interfaces/msg/ReadSplitEvent` from `rosbag2_player`; not a playable data topic. Generated `/clock` one, control topics/services zero, full event payload/order match, terminal state match. V8 replay-only CI creates one fresh original normal MCAP then plays it in another domain; V7 F01/F06 reused. Full CI opt-in remains available.
