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
