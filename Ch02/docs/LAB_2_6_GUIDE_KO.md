# LAB 2.6 — Action 목표·피드백·취소 실습

## 실습 목표
`CountUntil.action`의 Goal(`target_number`, `period`), Result(`reached_number`), Feedback(`current_number`)를 클라이언트·서버·ROS CLI로 검증한다. 서비스와 달리 **진행 상태**와 **취소 요청**이 있음을 확인한다.

## 준비
이 절은 **2.5절의 `action_msgs` 의존성 수정 반영 후** 실시한다.

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 interface show my_robot_interfaces/action/CountUntil
```

## 실습 A — 서버 + CLI
터미널 A:
```bash
ros2 run my_robot_system count_until_server
```
터미널 B (동일 환경 source):
```bash
ros2 action list -t
ros2 action info /count_until
ros2 action send_goal /count_until my_robot_interfaces/action/CountUntil "{target_number: 5, period: 1.0}" --feedback
```
목표 ACCEPT 후 current_number 1~5와 최종 reached_number=5, status=SUCCEEDED에 해당하는 결과가 관측되는지 확인한다. 숫자의 정확한 출력 형식은 ROS 배포판에 따라 다르다.

## 실습 B — Python 클라이언트
터미널 C:
```bash
ros2 run my_robot_system count_until_client
```
기본값 5회 × 0.5초. 서버가 없으면 약 5초 이내에 오류 로그 후 클라이언트가 종료되어야 한다(실제 wall time과 구현 측정 분리).

## 실습 C — 목표 거절
```bash
ros2 action send_goal /count_until my_robot_interfaces/action/CountUntil "{target_number: 0, period: 1.0}"
ros2 action send_goal /count_until my_robot_interfaces/action/CountUntil "{target_number: 5, period: -1.0}"
```
둘 다 Goal 거절을 기대한다. 1001 이상의 target, `period: 0.0`도 거절됨을 확인할 수 있다.

## 실습 D — 취소의 올바른 검증
CLI `send_goal`에서 Ctrl+C만 누르면 **CLI 프로세스만 종료**될 수 있으므로 결과 CANCELED를 보장하지 않는다. 아래는 별도 검증 스크립트이며 서버는 계속 실행 상태로 둔다.

```python
import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from action_msgs.msg import GoalStatus
from my_robot_interfaces.action import CountUntil

rclpy.init()
node = Node('cancel_lab_client')
client = ActionClient(node, CountUntil, '/count_until')
assert client.wait_for_server(timeout_sec=5.0)
goal = CountUntil.Goal(target_number=20, period=0.5)
sent = client.send_goal_async(goal)
rclpy.spin_until_future_complete(node, sent, timeout_sec=5.0)
handle = sent.result()
assert handle.accepted
cancel_future = handle.cancel_goal_async()
rclpy.spin_until_future_complete(node, cancel_future, timeout_sec=5.0)
assert cancel_future.result().goals_canceling, '취소 수락되지 않음'
result_future = handle.get_result_async()
rclpy.spin_until_future_complete(node, result_future, timeout_sec=5.0)
assert result_future.result().status == GoalStatus.STATUS_CANCELED
print('CANCELLED', result_future.result().result.reached_number)
node.destroy_node()
rclpy.shutdown()
```

스크립트를 `/tmp/ch02_cancel.py` 등으로 저장하고 `python3 /tmp/ch02_cancel.py`로 실행한다. 실제 취소 판정은 **GoalStatus.STATUS_CANCELED** 및 부분 카운트 값으로 한다. `CancelResponse.ACCEPT`는 요청 수락이지 물리적 정지 완료 인증이 아니다.

## 검증 질문·PASS
- `call_async`와 `send_goal_async`의 목적 차이 설명.
- 정상 결과, 두 가지 거절, 서버 부재 타임아웃, 취소 최종 상태를 증거로 제시.
- `ReentrantCallbackGroup` 없이 MultiThreadedExecutor만 두었을 때 위험을 설명.
- 이 코드는 교육용 숫자 카운터이다. 물리 로봇의 정지/안전 인터록을 입증하지 않는다.

[코드 리뷰·수정 보고서](SECTION_2_6_REPORT_KO.md).
