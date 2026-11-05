# 13.7 공식 구현 패턴 조사와 적용

2026-11-04 KST. 사용자 요청에 따라 공식 문서·GitHub 원본 및 설치본을 대조했다. 외부 패턴 확인 자체를 이 로봇의 물리 인수로 해석하지 않는다.

| 공식 근거 | 확인한 패턴 | 이 구현의 적용 |
|---|---|---|
| [py_trees_ros2.6.0 action_clients.py](https://github.com/splintered-reality/py_trees_ros/blob/2.6.0/py_trees_ros/action_clients.py), blob cc355f6b776df7f5e19a868b1cb82a48cdc3a779 | goal 전송·수락·result를 분리하고 update는 진행 상태를 반환한다. RUNNING→INVALID에서 비동기 취소한다. | Task/GoalTracker의 nonblocking 처리와 중단. 기존 동일 엔진 실행 경계를 사용해야 하므로 endpoint 하나만 감싸는 FromBlackboard를 그대로 대체 사용하지 않는다. |
| [ROS2 Actions 설계](https://design.ros2.org/articles/actions.html) | cancel 응답은 CANCELING 진입 대상이며 최종 CANCELED 결과와 다르다. | cancel_requests·cancel_acks·terminals·pending을 구분한다. 실제 물리 정착과 프로세스 회수는 추가로 검사한다. |
| [Jazzy rclpy ClientGoalHandle](https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/action/client.py), 조회 blob8fdbe37c18e4cdd6bd7d10969bc03c43652c3caa | cancel_goal_async/get_result_async는 별도 future다. 동기 호출을 callback에서 사용하면 deadlock 위험이 있다. | ROS 소유 worker만 action future를 poll하고 BT callback에서는 작업 요청/snapshot만 처리한다. |
| [Jazzy 공식 callback group 가이드 원본](https://github.com/ros2/ros2_documentation/blob/jazzy/source/How-To-Guides/Using-callback-groups.rst), 조회 blob829b66d96d7e0de22d5ee29bcdd24196fdcea54f | 기본 callback group은 mutually exclusive이며 executor 스레드 수만 늘려도 동기 대기가 해결되지 않는다. | BT 전용 node/context/executor와 기존 robot worker를 분리한다. 동일 node를 여러 스레드가 spin하지 않는다. |
| [py_trees_ros2.6.0 trees.py](https://github.com/splintered-reality/py_trees_ros/blob/2.6.0/py_trees_ros/trees.py), blob43891006e7234d598ac047044740466589213a6b | setup(node=...)를 지원하고 tick의 방문자/후처리를 통해 상태를 내보낸다. default_snapshot_stream 기본값은 false다. | 실제 설치 signature 확인. 직접 root.tick_once 후 임의 후처리 대신 tree.tick()를 호출하고 snapshot stream을 명시 활성화한다. terminal latch는 다음 root 실행을 막는다. |

docs.ros.org의 두 Jazzy 문서 URL은 접근 차단 페이지를 반환해 본문 근거로 사용하지 않았다. 대신 공식 ros2/ros2_documentation의 Jazzy 원본을 읽었다. 비공식 미러·커뮤니티 글을 구현 근거로 채택하지 않았다.

기존 run_pick은 blocking until 기반이며 live lease/단일 엔진을 보존해야 하므로 전체를 새로운 ROS 액션 클라이언트 예제로 바꾸지 않았다. 공식 패턴의 비동기 상태 전이와 소유권을 작은 어댑터에 적용했다. upstream terminate는 아직 goal handle이 없는 시점의 취소를 직접 처리하지 않으므로, 이 구현은 취소 의도를 유지하여 늦은 수락 후에도 취소한다. 이는 자체 보완이며 test_late_acceptance_is_canceled_and_ack_is_not_terminal로 따로 검증한다.

로컬 공식 deb는 py_trees2.6.0/py_trees_ros2.6.0/interfaces2.1.2이며 버전·hash를 prepare_bt_deps.sh에 고정했다. 시스템 전역 설치와 기존13.6 환경은 변경하지 않았다. 초기 기존·신규 전체 suite는232 PASS/64.02초였고 공식 패턴 대조 뒤 추가한 취소 ACK 기록 시험은 구현 부재로 RED를 확인한 뒤 보완했다.
