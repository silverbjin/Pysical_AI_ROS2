# LAB 2.2 — turtlesim을 CLI로 관찰하고 진단하기

## 목적
2.2.1~2.2.6: 노드 → 토픽 → 메시지 형식 → 서비스 → 연결 불량 추적을 실제 실행 순서로 익힌다.

## 준비
Ubuntu 24.04 / ROS 2 Jazzy 및 GUI 환경. WSL2에서는 WSLg/X 서버의 GUI 실행 여부 확인. 배포판이 다르면 `jazzy`를 교체한다.

```bash
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install ros-jazzy-turtlesim ros-jazzy-rqt-graph
ros2 pkg executables turtlesim
```

## 단계별 실습

**터미널 A — 시뮬레이터**
```bash
source /opt/ros/jazzy/setup.bash
ros2 run turtlesim turtlesim_node
```
파란 화면이 표시된다. 닫지 않는다.

**터미널 B — 원격 명령**
```bash
source /opt/ros/jazzy/setup.bash
ros2 run turtlesim turtle_teleop_key
```
방향키를 입력할 때 터미널 B에 **포커스**를 둔다. 다음 단계의 `topic pub`을 실행하기 전에는 B를 Ctrl+C로 중지한다.

**터미널 C — 진단 루틴**
```bash
source /opt/ros/jazzy/setup.bash
ros2 node list
ros2 node info /turtlesim
ros2 topic list -t
ros2 topic type /turtle1/cmd_vel
ros2 interface show geometry_msgs/msg/Twist
ros2 topic echo /turtle1/pose
```
echo가 연속 출력될 때 Ctrl+C로 종료. 이어서 `ros2 topic hz /turtle1/pose`; 수 초 관찰한 후 Ctrl+C. Hz는 환경 따라 변한다.

**직접 publish (B 종료 후)**
```bash
ros2 topic pub -r 1 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 2.0}, angular: {z: 1.8}}"
```
원운동을 확인하고 Ctrl+C. Twist 필드는 YAML 표현이다. 실제 하드웨어가 아니라 turtlesim에서만 수행한다.

**서비스와 인터페이스**
```bash
ros2 service list -t
ros2 service type /spawn
ros2 interface show turtlesim/srv/Spawn
ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 2.0, theta: 0.0, name: my_turtle}"
```
`my_turtle` 추가 표시. 반복 호출 시 같은 이름 충돌 가능. `ros2 service call /kill turtlesim/srv/Kill "{name: my_turtle}"`로 정리.

## 장애 추적 실습
1. `ros2 node list`에서 `/turtlesim` 확인 (없으면 실행 로그 확인).
2. `ros2 node info /turtlesim`로 `/turtle1/cmd_vel` 구독 확인.
3. `ros2 topic info -v /turtle1/cmd_vel`로 pub/sub 수·QoS 확인.
4. `ros2 topic echo /turtle1/cmd_vel`로 실제 명령 값 확인.
5. `ros2 topic echo /turtle1/pose`로 결과 확인. 연결은 살아 있는데 이동하지 않으면 토픽명·타입·QoS·속도값·시뮬레이터 경계·컨트롤러 상태를 순차 검사한다.

## PASS 기준
노드 2개, pose 수신, hz 값, 새로운 거북이 소환, Twist 계층 구조를 각각 설명·화면 기록. 오류 시 `echo`만으로 하드웨어 불량이라고 결론내리지 않는다. [리뷰 보고서](SECTION_2_2_REPORT_KO.md).