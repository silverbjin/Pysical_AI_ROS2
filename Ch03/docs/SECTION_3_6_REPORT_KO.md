# SECTION 3.6 — Gazebo ↔ ROS 2 브리지 코드·토픽 리뷰

- 원고: 3.6.1~3.6.5 (방향 지정, CLI, YAML, `/clock`)
- 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef`, 2026-10-20
- 대상: `config/ros_gz_bridge.yaml`, `launch/bridge.launch.py`
- 판정: **정적 설정 수정 완료 / 브리지 실연동 미검증**

## 수정 전 문제
| ID | 심각도 | 사실·증거 | 수정 |
|---|---|---|---|
| 3.6-01 | High | `/clock`이 `BIDIRECTIONAL`: ROS→Gazebo 반송 가능성 및 시간 소스 혼선 | `GZ_TO_ROS` 단방향 |
| 3.6-02 | Medium | `/tf`가 `BIDIRECTIONAL`: Gazebo 포즈→ROS TF와 RSP TF를 중복 전송할 소지 | 브리지에서 TF 제거. **RSP**가 joint_states에서 TF 발행 |
| 3.6-03 | Low | `bridge.launch.py`가 실제 매핑하지 않는 `/tf_static` QoS override 사용 | 무효 설정·미사용 import 정리 |
| 3.6-04 | Medium | 본 로봇에는 `cmd_vel`을 소비하는 구동 플러그인이 없음 | YAML에 학습용 통신 예제로만 표기, **토픽 발행이 움직임을 뜻하지 않음** |
| 3.6-05 | Medium | joint_state 토픽이 `/world/my_first_world/model/my_robot/joint_state` 고정 | 월드·모델명 변경 시 반드시 YAML 재점검하도록 명시 |

## 메시지 대응
`/joint_states` ↔ Gazebo `gz.msgs.Model`은 지원되는 형식 조합이다. 제어 `/joint1/cmd_pos`, `/joint2/cmd_pos`는 ROS `std_msgs/msg/Float64`를 Gazebo `gz.msgs.Double`로 전달한다. `ros_topic_name`과 `gz_topic_name`은 서로 달라질 수 있다. **문서 원고의 단일 `topic_name` 필드는 코드의 현행 YAML 별칭 구조와 구분**하라.

공식 참고:
- Gazebo Harmonic ROS 2 통합: https://gazebosim.org/docs/harmonic/ros2_integration/
- ros_gz_bridge README: https://github.com/gazebosim/ros_gz/tree/ros2/ros_gz_bridge

## 검증
- PASS(정적): 수정 후 Clock `GZ_TO_ROS`, TF 브리지 중복 제거, 2개 조인트 명령의 `ROS_TO_GZ` 방향 유지.
- NOT RUN: ros_gz_bridge startup, 실제 `gz topic -l`, `ros2 topic echo /clock`, publisher/subscriber QoS, `/joint_states` 실측.

## 재현
```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 launch my_robot_description spawn_robot.launch.py
# 별도 터미널
ros2 topic echo /clock --once
ros2 topic info /joint_states -v
ros2 topic list | grep -E '/clock|/joint_states|/joint[12]/cmd_pos'
gz topic -l | grep -E 'joint_state|cmd_pos'
```
`/joint_states`를 확인하려면 **3.8의 JointStatePublisher 플러그인도 실행돼야 한다**. 절별 독립 브랜치로 인한 선행 의존성을 숨기지 않는다.

## PR 승인 조건
`/clock` 단일 퍼블리셔, 시뮬레이션 시간 증가, `/joint_states` 매핑 정상, 조인트 명령 방향 확인, `/tf` 중복 없음. Acceptance: `PENDING_RUNTIME_VERIFICATION`.
