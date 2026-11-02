# SECTION 2.2 코드·실습 검토 보고서

- **원고** 2.2.1~2.2.6 / **기준 main** `94264bee4b53ce4c9676011b98e72368b1e40690` / 2026-10-20.
- **검토 대상**: CLI 예제와 `my_robot_system`이 사용하는 turtlesim 토픽·서비스·메시지; 이 절의 독립 Python 소스는 없음.
- **판정**: CLI 문법·시나리오 정적 검토 완료. **실행 검증 미수행** (환경에 ROS 2/colcon/GUI 없음). 코드 수정 없음.

## 이슈

| ID | 등급 | 문제 | 권장사항 |
|---|---|---|---|
| 2.2-01 | High(실습) | 원고에 ROS 배포판 source, turtlesim 설치, GUI 표시 환경 검증이 없음 | 가이드에 사전 점검·apt 의존성·WSLg 추가 |
| 2.2-02 | Medium | `ros2 topic hz /turtle1/pose`의 원고 예시 62.456Hz는 고정된 보증값처럼 읽힘 | PC/시뮬레이터 부하에 따라 가변, 숫자 비교가 아닌 스트림 확인 |
| 2.2-03 | Medium | CLI `topic pub -r 1`을 teleop과 동시에 사용하면 서로 다른 `cmd_vel` 명령이 경쟁함 | teleop 종료 후 발행 테스트, Ctrl+C로 정리 |
| 2.2-04 | Medium | “토픽이 보이는데 모터가 안 돌면 하드웨어 문제”는 원인 단정 | 토픽 이름·타입·QoS·프레임·안전 인터록·컨트롤러 상태도 검사 |
| 2.2-05 | Low | 원고에서는 pub 페이로드를 'JSON 형식'으로 표현 | CLI는 **YAML 형태**의 메시지 값(인라인 매핑)을 받는다고 명시 |
| 2.2-06 | Low | `ros2 node info`의 Publishers/Subscribers 구분만으로 통신 성공을 증명하지 못함 | `topic info -v`, `echo`, `hz`를 순서대로 검증 |

## 정적 검토 체크
- `turtlesim_node`, `turtle_teleop_key`, `/turtle1/cmd_vel`, `/turtle1/pose`, `/spawn`은 ROS 2 turtlesim 표준 실습 API.
- `geometry_msgs/msg/Twist`, `turtlesim/srv/Spawn` 구조와 CLI 예제 일치.
- 인쇄된 로그·Hz는 **예시**; 재현 결과가 아님.

## 검증 상태 / 실행 계획

| 검사 | 상태 |
|---|---|
| 원고 명령 흐름 및 타입 대조 | PASS (정적) |
| GUI 실행/키보드 조작 | NOT RUN |
| CLI node/topic/service/hz/echo 확인 | NOT RUN |
| 서비스 spawn 실제 호출 및 화면 변화 | NOT RUN |

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
ros2 pkg executables turtlesim
# 터미널 A:
ros2 run turtlesim turtlesim_node
# 터미널 B:
ros2 node list
ros2 topic type /turtle1/cmd_vel
ros2 topic info -v /turtle1/cmd_vel
ros2 topic echo /turtle1/pose
ros2 service type /spawn
```

**수용 기준**: turtlesim GUI 표시, 노드 발견, 이동 명령에 Pose 변화, spawn에 추가 거북이 표시, CLI와 메시지 타입 일치. 스크린샷·터미널 로그 수집 후 실행 상태 재판정.