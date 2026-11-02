# LAB 2.8 — QoS 호환성: '보내는데 왜 안 받지?'

## 목표
2.8.1~2.8.4에서 Reliable / Best Effort, History, Durability의 의미를 확인한다. **정상 발행과 전달 성공은 서로 다른 결과**라는 사실을 재현한다.

## 사전 점검
Ubuntu 24.04 / ROS 2 Jazzy, 동일 DDS 도메인. 2.3절에서 `std_msgs` 등 필수 의존성을, 2.5절에서 액션 의존성을 선언한 소스로 빌드하는 것이 권장된다.

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_system
```

## 실험 A — BEST_EFFORT 발행
터미널 A:
```bash
ros2 run my_robot_system qos_test_node
```
1초마다 `Published video frame (Best Effort)` 로그. 토픽명 `/video_stream`, 타입 `std_msgs/msg/String`, KEEP_LAST depth=1, VOLATILE.

터미널 C:
```bash
ros2 topic info -v /video_stream
ros2 topic hz /video_stream --qos-reliability best_effort
```
CLI가 정상적으로 연결된 상태에서 약 1Hz를 기대한다. 사용 ROS CLI 배포판에서 `--qos-reliability` 옵션 지원 여부는 `ros2 topic hz --help`로 먼저 확인한다.

## 실험 B — QoS 불일치 (의도적인 미수신)
터미널 B (A 유지):
```bash
ros2 run my_robot_system qos_compare_sub --ros-args -p reliability:=reliable
```
퍼블리셔는 BEST_EFFORT만 제공하지만 구독자는 RELIABLE을 요구하므로 호환되지 않는다. **B에 `Received frame`이 없는 것**이 예상되는 실험 결과다. B에서 경고가 보이는지는 ROS/RMW 설정에 따라 다를 수 있다. 반면 A는 계속 발행한다.

```bash
ros2 topic info -v /video_stream
```
endpoint reliability가 서로 다름을 기록. Ctrl+C로 B 종료.

## 실험 C — 호환 상태로 복구
터미널 B 다시 시작:
```bash
ros2 run my_robot_system qos_compare_sub --ros-args -p reliability:=best_effort
```
A의 발행과 B의 `Received frame: Frame Data` 로그가 함께 관찰되어야 한다. `ros2 topic info -v`에서 publisher/subscriber의 OFFERED/REQUESTED QoS 정책을 비교한다.

## 이론과 응용
| Publisher 제공 | Subscriber 요구 | 연결 |
|---|---|---|
| RELIABLE | RELIABLE | 가능 |
| RELIABLE | BEST_EFFORT | 가능 |
| BEST_EFFORT | BEST_EFFORT | 가능 |
| BEST_EFFORT | RELIABLE | **불가** |

`transient_local`은 publisher가 살아 있고 적절한 history를 유지할 때 늦게 가입한 구독자에게 데이터를 제공하는 설정이다. 본 코드는 VOLATILE만 사용하므로 **durability replay를 검증하지 않는다**. deadline/liveliness도 callback이 구현되지 않아 정의 학습만 수행한다. Reliable 정책도 물리적 안전 명령의 무조건적 전달 보증이 아니다.

## 고장 해결
- A는 발행하지만 B는 수신 없음 → `ros2 topic info -v`로 QoS/타입 확인.
- 양쪽 BEST_EFFORT인데도 수신 없음 → `ROS_DOMAIN_ID`, RMW, discovery, firewall, 토픽명, source 오버레이 확인.
- B에서 parameter 오류 → `reliable` 또는 `best_effort` 철자 확인.
- 동일 패키지 버전이 아닌 것 같으면 `ros2 pkg prefix my_robot_system`으로 설치 경로 점검.

## 제출·PASS
발행 로그 3줄, 불일치 상태에서 수신 로그 없음과 두 endpoint QoS, 복구 상태의 수신 로그 3줄, 네 칸의 QoS 호환성 표 설명을 제출한다. 종료 순서 B→A. [보고서](SECTION_2_8_REPORT_KO.md).
