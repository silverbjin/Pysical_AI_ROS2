# LAB 2.7 — ROS 2 Launch·파라미터·리매핑 실험

## 목표
하나의 `ros2 launch`로 여러 노드를 올리고, **의도적 연결 실패 → 양 끝 리매핑 복구**를 눈으로 검증한다. 2.7.5절의 이벤트 핸들러는 개념 실습으로 구분한다.

## 환경 준비
Ubuntu 24.04 ROS 2 Jazzy + turtlesim GUI. **2.3절(런타임 의존성), 2.5절(action_msgs)의 변경이 병합된 코드**로 빌드하는 것을 권장한다.

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_robot_system
ls install/my_robot_system/share/my_robot_system/launch/ 2>/dev/null || true
```
마지막 설치 디렉터리는 merge/symlink 설정에 따라 다를 수 있다. 해당 `ls` 출력이 비어도 `ros2 launch`에서 파일 검색 결과로 실제 설치 여부를 검사한다.

## 실습 A — 정상 통합 실행
```bash
ros2 launch my_robot_system my_turtle.launch.py
```
GUI에 거북이 등장, 곡선 이동, 구독자 로그. 다른 터미널에서 `ros2 node list`로 `/sim`, `/my_publisher`, `/my_subscriber` 확인. `rqt_graph`로 토픽 연결선이 보이는지 점검. Ctrl+C로 모두 중지.

## 실습 B — 고장 재현 (의도적인 실패)
```bash
ros2 launch my_robot_system remap_test.launch.py
```
배경은 빨갛지만 거북이 정지. 제어 명령이 **`/cmd_vel_custom`**으로만 송신되고 turtlesim은 **`/turtle1/cmd_vel`** 구독을 유지하기 때문이다.

새 터미널(동일 ROS source):
```bash
ros2 topic list -t
ros2 topic info -v /cmd_vel_custom
ros2 topic info -v /turtle1/cmd_vel
ros2 topic echo /cmd_vel_custom --once
```
부록 질문: 퍼블리셔 토픽과 구독 토픽의 이름·타입·QoS 중 어떤 것이 어긋났는가? 데이터 발행이 존재해도 로봇이 반응하지 않는 이유를 한 문장으로 기록.

## 실습 C — 소스 수정 없는 복구
B 종료 후:
```bash
ros2 launch my_robot_system remap_fixed.launch.py
```
새 파일은 **양쪽 모두** `/turtle1/cmd_vel → /cmd_vel_custom`을 적용. 붉은 배경에서 다시 거북이가 움직여야 한다. `topic info -v /cmd_vel_custom`에 publisher와 subscriber가 모두 잡히는지 확인한다.

## 실습 D — 준비 완료 이벤트
원고의 `OnProcessStart(target_action=turtlesim_node, on_start=[spawn_client_node])`는 프로세스 시작 통지만 보장한다. `/spawn` 서비스는 아직 준비되지 않았을 수 있다. 따라서 `turtle_spawn_client`의 `wait_for_service(timeout_sec=...)`가 함께 필요하다. 런치 이벤트 핸들러를 readiness 확인으로 대체하지 않는다.

## 보조 코드 확인
`turtle_patrol.py`는 원고 본문의 직접 실습이 아닌 저장소 보조 예제다. `ros2 run my_robot_system turtle_patrol`은 `/turtle1/pose` 첫 메시지 후 출발해야 한다. `my_turtle.launch.py`와 동시에 켜면 서로 `cmd_vel`을 명령하므로 **별도 세션**에서 실행한다.

## PASS 조건
정상 실행 3노드, 실패 상태의 두 분리된 토픽, 복구 상태의 pub/sub 연결, 서비스 readiness와 프로세스 실행 이벤트 차이를 입증한다. [코드 리뷰 보고서](SECTION_2_7_REPORT_KO.md).