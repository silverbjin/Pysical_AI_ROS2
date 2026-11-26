# 15.2 실습 — ICD와 DDS
목표: Action, Service, Topic의 차이와 준비·차단 계약을 배운다. 실제 로봇 금지. 별도 ROS_DOMAIN_ID 사용.
```bash
source /opt/ros/jazzy/setup.bash
cd Ch15/ros2_ws
colcon build --packages-select ch15_interfaces ch15_adapters ch15_safety ch15_mission
source install/setup.bash
export ROS_DOMAIN_ID=71
ros2 launch ch15_mission mission.launch.py auto_start:=false
```
다른 터미널에서 같은 domain과 setup을 적용한다. ros2 interface show ch15_interfaces/action/PickObject, ros2 topic echo /ch15/ready, ros2 topic echo /ch15/safety_state, ros2 service call /switch_gait ch15_interfaces/srv/SwitchGait "{gait_type: stand}" 및 /ch15/gait_state 관찰. 요청 수락과 실제 상태 확인은 구분한다. 자동 전체 미션은 G03 이후. QoS demo 별도 실행: ros2 run ch15_adapters qos_demo; BE subscriber 준비 후 /ch15/qos_demo/start Trigger. RELIABLE subscriber는 BE publisher와 불일치, TL late joiner는 마지막 상태 수신. 숫자 10은 fixture 한정.
정상 종료는 소유한 launch에서 Ctrl+C 한 번. 실행 및 기대 결과는 CI 증거 확인 전 설계 예시. G02 reset은 의도적으로 거절. 실제 물리 또는 L3 인수 아님.
