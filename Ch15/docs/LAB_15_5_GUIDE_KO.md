# 15.5 미션 기록·분석·격리 재생 실습 — G05 인수판
목표: 실제 ROS 2 DDS mock mission을 MCAP에 기록하고 사건/상태를 분석한 다음, 제어 명령 없는 격리 재생을 검증한다. 실제 로봇/Ch13/Ch14 물리 환경과 동시에 실행하지 않는다.

## 1. 준비
Ubuntu 24.04 / ROS 2 Jazzy / WSL2. 최소 4개 사용 가능한 CPU, 새 workspace 및 빈 localhost ROS domain. G05 실제 최종 실행 PIN: c69fb2585546b89702d21d5e4e86f610d569f330. 다음은 G05 WSL2 실습 명령이며 CI 성공과 owner L3는 구분한다.
```bash
sudo apt update
sudo apt install -y python3-rosdep python3-colcon-common-extensions python3-matplotlib ros-jazzy-rosbag2 ros-jazzy-rosbag2-storage-mcap ros-jazzy-rmw-cyclonedds-cpp
source /opt/ros/jazzy/setup.bash
ROOT="$(git rev-parse --show-toplevel)"
rosdep install --from-paths "$ROOT/Ch15/ros2_ws/src" --ignore-src --rosdistro jazzy -y
mkdir -p "$HOME/ch15_g05_ws"
cd "$HOME/ch15_g05_ws"
colcon build --base-paths "$ROOT/Ch15/ros2_ws/src"
source install/setup.bash
export G03_INSTALL="$PWD/install"
```
ROOT는 PIN checkout 경로. Mock은 외부 물리 모델 불필요. G05 script에서만 Cyclone DDS/local domain 설정. 기존 안전 정책 및 command QoS 유지.

## 2. 정상 기록
```bash
bash "$ROOT/Ch15/scripts/record_mission.sh" normal "$HOME/g05-normal" 76
python3 "$ROOT/Ch15/python/bag_to_csv.py" "$HOME/g05-normal/bag" "$HOME/g05-normal/analysis"
python3 "$ROOT/Ch15/python/plot_mission.py" "$HOME/g05-normal/analysis"
```
새 출력 경로. Recorder 먼저, Scan 단일 발행자 10Hz, Watchdog false heartbeat, Arbiter 및 Ready/Safety 600ms 연속 검증, discovery 10개 후 명시 start. 64MiB budget, 8MiB split. 정상 COMPLETED, 4 accepted/terminal UUID. 7 owned process exit0. F01만 실제 양의 command 관측 후 scan 중단. Record QoS event + tf_static Reliable, 연속 telemetry Best Effort. /clock, odom, joints 등 없는 mock 물리 토픽 N/A, energy null.

## 3. 장애 기록
```bash
for row in F01:77 F06:78; do
  mode="${row%:*}"; domain="${row#*:}"
  bash "$ROOT/Ch15/scripts/record_mission.sh" "$mode" "$HOME/g05-$mode" "$domain"
  python3 "$ROOT/Ch15/python/bag_to_csv.py" "$HOME/g05-$mode/bag" "$HOME/g05-$mode/analysis"
  python3 "$ROOT/Ch15/python/plot_mission.py" "$HOME/g05-$mode/analysis"
done
```
ABORTED 기대 상태. F01 scan receipt loss, F06 실제 mock pick result6. G08 안전 반응/복구 acceptance 아님.

## 4. 실제 재생
```bash
bash "$ROOT/Ch15/scripts/replay_mission.sh" "$HOME/g05-normal/bag" "$HOME/g05-normal/replay.json" 79 76
```
Consumer 먼저, 다른 빈 domain, 정확한 Event/Status 두 토픽만 play. 새 /clock 1개, 기록 clock 제외. /events/read_split은 rosbag2 내부 타입으로 playback allowlist에 추가하지 않는다. 실제 player GID 고정 후 완전 데이터 수신 뒤 동일 GID unknown-name metadata loss만 허용. 새 GID/소유자/타입/복수 writer 거절. 상태·이벤트 전체 데이터, 시계 단조 증가, endpoint cleanup, player exit0, 제어 발행0 확인.

## 5. 증거 분석
metadata.yaml/topic counts → executor/mission-events.jsonl → analysis/events.csv, states.csv, metrics.json, mission.png → replay.json. record/ROS/steady clock 분리, UUID 수락-종료, source/epoch/producer sequence 확인. String demo read_states와 typed decoder 구분. Scan 및 watchdog/arbiter/executor native traces로 최초 실패 경계 분석. Raw bag은 로컬 보존; 공개 Git에는 해시/요약만.

## 6. 실제 CI 및 보고서
V7 record3/3 run45949623564, V9 replay run45950671176. [최종 인수 보고서](reports/G05_FINAL_ACCEPTANCE_KO.md), [독립 진단 보고서](reports/G05_SCAN_DIAGNOSTIC_RESULT_KO.md). CI 재현 full opt-in [RUN G05], replay-only [RUN G05 REPLAY]는 V7 timing/fault receipts 재사용을 전제로 하는 검수 유지보수용.

## G09 공통 실행 경로
Ch15 루트, `CH15_SOURCE_SHA`를 실제 고정 HEAD로 설정하고 `bash scripts/run_lab.sh 15.5 --bag /absolute/mission_bag` 실행. 상세 선행 환경과 evidence archive는 [15.9](LAB_15_9_GUIDE_KO.md) 참조. 문서 조회와 실제 실행을 구분한다.
