# LAB 2.4 — 요청/응답 서비스와 예외 경로

## 목표
`turtlesim/srv/Spawn` 클라이언트와 `example_interfaces/srv/AddTwoInts` 서버를 구현 관점에서 이해한다. 정상 응답과 서버 미기동·중복 요청을 비교한다.

## 환경
```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_system
```
터미널마다 동일한 ROS/워크스페이스 source가 필요하다. 2.3절의 누락 의존성이 설치된 환경에서 진행한다.

## 실습 A — 거북이 Spawn
터미널 A:
```bash
ros2 run turtlesim turtlesim_node
```
터미널 B:
```bash
ros2 service type /spawn
ros2 interface show turtlesim/srv/Spawn
ros2 run my_robot_system turtle_spawn_client
```
GUI 중앙 부근에 `robot_turtle`이 추가되고 B에 서비스 응답 이름이 기록되는지 확인.

중복 이름 처리:
```bash
ros2 service call /kill turtlesim/srv/Kill "{name: robot_turtle}"
ros2 run my_robot_system turtle_spawn_client
```
복원 후 다시 소환. 의도적으로 동일 명령을 중복 실행하면 실패할 수 있으며 이것은 ROS 메시지 연결 오류가 아니다.

## 실습 B — 계산기 서버
터미널 C:
```bash
ros2 run my_robot_system add_two_ints_server
```
터미널 D:
```bash
ros2 service list -t
ros2 service type /add_two_ints
ros2 interface show example_interfaces/srv/AddTwoInts
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 5, b: 10}"
```
**예상 합계 15**, C에 요청 로그. 다른 부호 조합(`-4`, `2`)에 대해서는 `-2`를 예상한다.

## 실습 C — 실패 검증
turtlesim을 종료한 후 client를 실행한다. 무한 대기 대신 **수 초 내 에러**를 보고 정상적으로 리소스를 해제하는지 확인한다. 실제 제한값은 코드 `wait_for_service`와 `spin_until_future_complete`에 명시된다. `ros2 service call`을 서버 없이 무한 대기 상태로 두지 않는다.

## 원리
`call_async()`가 Future를 반환한 후 `spin_until_future_complete`가 완료까지 이벤트를 처리하므로, **서비스 프로토콜의 응답 구조**와 **호출자 코드의 blocking 여부**는 구분해야 한다. 콜백 내부에서 동기 대기는 기본 mutually exclusive 그룹에서 교착 위험이 있다.

## PASS
정상 spawn, 중복 방지/정리, `5+10=15`, 서버 중단 시 명시적 실패, 각 서비스 타입 확인. 미완료 항목은 실행 로그와 함께 BLOCKED로 표기. [리뷰](SECTION_2_4_REPORT_KO.md).