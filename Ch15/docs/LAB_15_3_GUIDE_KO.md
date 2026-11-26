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
