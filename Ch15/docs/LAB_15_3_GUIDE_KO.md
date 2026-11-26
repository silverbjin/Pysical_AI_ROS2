# 15.3 실습 — 비동기 BT 전체 미션
Profile A mock 전용. 실제 하드웨어/Ch13와 같은 DDS domain에서 실행하지 않는다.
```bash
source /opt/ros/jazzy/setup.bash
cd Ch15/ros2_ws
colcon build --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission
source install/setup.bash
export ROS_DOMAIN_ID=74
ros2 launch ch15_mission mission.launch.py auto_start:=false evidence_dir:=$HOME/ch15_g03_$(date +%s)
```
같은 domain의 두 번째 terminal: ros2 topic echo /ch15/ready, ros2 service call /ch15/start_mission std_srvs/srv/Trigger '{}', ros2 topic echo /ch15/mission_state. 상태와 Goal UUID 이벤트를 관찰한다. 취소는 /ch15/cancel_mission Trigger; 미션 중 reset은 거절되어야 한다. 종료 후 재시작은 명시 reset 없이 거절. Ctrl+C는 terminal 확인 후. 실제 안전 fault latch reset은 G08 전까지 fail-closed. Profile B native runner G04, C 실행 금지.
교육 과제: Root SUCCESS와 END 상태의 차이, request_id와 UUID의 차이, stamp와 steady clock의 차이, tick과 supervisor 별도 timer의 역할. mission-events.jsonl 및 ticks.csv를 제출한다. G03 CI 확인 전 결과는 기대값이다.

## G04 독립 물리 실습: 두 경로를 동시에 실행하지 않는다
### B-1 Ch13 native basic (현재 BLOCKED)
원본 Ch13 시작 가이드 Ch13/docs/START_HERE_13_8_KO.md를 먼저 확인. 현재 외부 자산 권리/94 SHA256, 현재 설치 closure 미확보. 실행 전 승인된 local-use 검토 reference, 원본 upstream SHA, 실제 자산 바이트 필요. 사용 승인 receipt는 템플릿이며 사용자 승인 증거를 꾸미지 않는다. GitHub repository의 공개 여부는 외부 weight/mesh의 사용·재배포 허가가 아니다.
- 기존 Ch13 main 기준 1931cac92585fc155357880b584c72c76d67257c을 별도 checkout에 고정. 상류 경로는 해당 checkout의 부모/upstream-iit-locomanipulation-d010212, shared lock은 부모/ch13_reuse_engine.lock. 기존 engine이 소유 중인 lock 삭제 금지.
- 상류 94개 경로 존재, 71개 크기 차이. deploy/config.py 한 파일의 CRLF 변환이 원래 SHA와 일치하는 것으로 확인. 다른 자산의 EOL/바이트 변환은 미확인. 승인된 별도 checkout에서만 원래 SHA 전수 검사; 해시를 덮어쓰지 않는다.
- 원본 가이드와 동일한 검증된 native venv와 별도 build를 사용한다.
```bash
# 승인과 의존성 검수 완료 후에만 사용하는 명령 예시 (현재 실행 미검증)
export CH13_REUSE_BUILD="$HOME/ch15_native_13_build"
export CH13_REUSE_VENV="$HOME/ch13_reuse_iit_d010212_venv"
bash Ch15/scripts/run_physical_basic.sh /path/to/pinned_ch13 /path/to/approved_local_use.json "$HOME/ch15_native_$(date +%s)"
```
기본 exercise는 navigate/find/finish이며 pick/return/place 없음. 원본 basic_result, bag, source freeze, after lock receipt를 읽는다. 현재 T10 BLOCKED; historical v53 PASS를 신규 결과로 취급하지 않는다. native stop injection F01은 별도 검증된 hook 미확보로 BLOCKED.
### B-2 독립 RGB-D cube lab
Gazebo Harmonic, ROS Jazzy, cv_bridge, OpenCV, ros_gz_bridge, tf2_ros. 별도 ROS domain과 headless software renderer. 실제 로봇 또는 다른 시뮬레이터와 같은 domain에서 실행 금지.
```bash
source /opt/ros/jazzy/setup.bash
cd Ch15/ros2_ws
colcon build --packages-select ch15_interfaces ch15_adapters ch15_simulation
source install/setup.bash
export ROS_DOMAIN_ID=79
cd ../..
bash Ch15/scripts/run_cube_lab.sh "$HOME/ch15_cube_$(date +%s)"
```
실제 RGB/depth/info, map→camera_optical static TF, HSV color segment 및 median depth. Known 5cm cube half-edge correction; orientation identity is POSITION_ONLY marker only, not grasp. GT independent native pose and 8-corner projection. 10 fresh frames normal, invalid-depth copied fixture 3 frames, actual Gazebo occlusion 3 frames. No command topics published. 제출: positions.csv/json, model-pose.log, cube-result.json, shutdown.tsv, input-sha256.txt, rendered RGB samples. CI에서 실제 Harmonic T11 PASS (run 45910585983, 10/10 normal, max 2.046mm, min IoU .9216, 6/6 invalid blocked, 4/4 exit0). 동일한 WSL2 owner 실행은 아직 미검증. 원본 evidence/g04/positions.csv와 G04 보고서를 대조한다.
