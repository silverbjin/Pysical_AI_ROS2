# SECTION 2.4 코드 리뷰·수정 보고서

- **원고** 2.4.1~2.4.4 / **기준 main** `94264bee4b53ce4c9676011b98e72368b1e40690`
- **대상** `turtle_spawn_client.py`, `add_two_ints_server.py`, `setup.py`, `package.xml`.
- **판정**: 요청/응답 및 서비스 엔트리포인트는 코드상 일치. 서버 대기·응답 타임아웃에 실행 취약점 존재해 클라이언트 개선. ROS 실행·빌드 미검증.

## 이슈와 처리

| ID | 심각도 | 재현 조건과 영향 | 조치 |
|---|---|---|---|
| 2.4-01 | High | `TurtleSpawnClient.__init__`에서 `wait_for_service()` 반복이 끝나지 않아 turtlesim 미기동 시 실습 무한 대기 | 유한한 대기/타임아웃·명시적 오류 |
| 2.4-02 | High | `spin_until_future_complete()` 타임아웃 없음; 서버 중지 후 영구 대기 가능 | 응답 timeout 후 예외 발생, finally로 노드 해제 |
| 2.4-03 | Medium | `robot_turtle` 이름 고정, 재실행 시 중복 spawn 실패 | `/kill` 정리 명령 및 예외 안내 |
| 2.4-04 | Medium | “비동기 호출”과 “클라이언트가 기다리는 방식” 혼동 소지 | `call_async`는 비동기 요청이지만 본 일회성 노드는 결과까지 대기함을 명시 |
| 2.4-05 | Low | 원고의 “서비스 콜백 안에서 또 서비스 호출하면 안 됨”은 과도한 일반화 | blocking 동기 대기를 callback-group/Executor 없이 하는 것이 핵심 위험으로 정정 |

## 변경
`turtle_spawn_client.py`: 서비스 발견 시간 제한, Future 응답 시간 제한, 실패 시 로그, `finally` 자원 정리. `add_two_ints_server.py`는 수동 검사상 `request.a + request.b` / `response.sum` 구조와 ROS 인터페이스가 일치하여 변경 없음.

## 검증 매트릭스

| 항목 | 결과 |
|---|---|
| 구현·원고·타입 교차검토 | PASS (정적) |
| 종료/타임아웃 경로 소스 검사 | PASS (정적) |
| ROS 2 통합 빌드 | NOT RUN |
| turtlesim 정상/서비스 미기동/중복 spawn | NOT RUN |
| `/add_two_ints` 서비스 결과 15 | NOT RUN |

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
# 터미널 A: ros2 run my_robot_system add_two_ints_server
# 터미널 B:
ros2 service call /add_two_ints example_interfaces/srv/AddTwoInts "{a: 5, b: 10}"
```

검증의 실제 stdout/stderr와 exit code 없이 PASS를 선언하지 않는다. 서비스 타임아웃은 예외 처리지만 하드웨어 안전 검증을 대체하지 않는다.