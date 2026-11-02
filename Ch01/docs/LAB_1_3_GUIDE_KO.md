# LAB 1.3 — 노드·메시지·인터페이스

**환경:** Ubuntu 24.04 / ROS 2 Jazzy / Python 3.12. **현재 상태:** 재현 실습 문서 작성; 실제 ROS 2 명령 실행은 NOT_RUN.

## STEP 1. 교육용 로봇 설치 및 시작
```bash
source /opt/ros/jazzy/setup.bash
sudo apt install -y ros-jazzy-turtlesim
ros2 run turtlesim turtlesim_node
```

터미널 B에서 Jazzy를 다시 source하고:
```bash
ros2 node list
ros2 node info /turtlesim
ros2 topic list -t
ros2 interface show turtlesim/msg/Pose
```

## STEP 2. Topic = 비동기 스트림
```bash
ros2 topic echo /turtle1/pose
ros2 topic info -v /turtle1/pose
ros2 topic hz /turtle1/pose
```
`/turtle1/pose` 메시지 최소 5개 관찰 후 Ctrl+C. Message 필드, QoS, 관찰 주기 구분.

## STEP 3. Service = 요청과 응답
```bash
ros2 service list -t
ros2 interface show turtlesim/srv/Spawn
ros2 service call /spawn turtlesim/srv/Spawn "{x: 5.0, y: 5.0, theta: 0.0, name: 'lab_turtle'}"
```
**기대:** 응답에 이름 `lab_turtle` 표시 및 GUI 거북이 추가. 중복 이름이면 고유 이름으로 다시 요청한다.

## STEP 4. Action = 목표·피드백·결과
```bash
ros2 action list -t
ros2 interface show turtlesim/action/RotateAbsolute
ros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 1.57}" --feedback
```
**기대:** goal 수락/회전 피드백/결과. 취소는 action server 구현에 따르며 자동 보장하지 않는다.

## STEP 5. 원고의 커스텀 인터페이스 대조
```bash
find ~/Pysical_AI_ROS2/Ch01 -type f \( -name '*.msg' -o -name '*.srv' -o -name '*.action' \)
```
원고의 SensorData, AddTwoInts, MoveRobot은 예시 스키마이고 **빌드 가능한 패키지 파일은 없음**. 실제 사용자 정의 인터페이스를 컴파일하려면 별도 rosidl 패키지/의존성/빌드가 필요하다.

**ACCEPT:** Node 1개 확인, Topic pose 5회, Spawn 응답, RotateAbsolute 피드백/결과, 통신 패턴의 차이 설명. **NOT_RUN:** 이 검토 환경에서 ROS GUI/DDS 실제 실행.

## Evidence 기록

| 항목 | 실제 출력·환경 | 판정 |
|---|---|---|
| `git rev-parse HEAD` / `ros2 doctor --report` | 기록 필요 | NOT_RUN |
| 각 STEP의 실제 종료 코드·노드/토픽 로그 | 기록 필요 | NOT_RUN |
| 실패 증상, 변경 사항 및 재실행 | 기록 필요 | NOT_RUN |

[절별 리뷰](SECTION_1_3_REPORT_KO.md) 참조.
