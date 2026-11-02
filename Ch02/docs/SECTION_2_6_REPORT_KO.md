# SECTION 2.6 액션 코드 리뷰 및 취소 경로 수정 보고서

- **원고** 2.6.1~2.6.6 / **기준** `main@94264bee4b53ce4c9676011b98e72368b1e40690` / 작성 2026-10-20.
- **대상** `CountUntil.action`, `count_until_server.py`, `count_until_client.py`, ROS 액션 CLI·QoS·Executor 계약.
- **판정**: 취소·실패 경로를 강화한 코드 수정 완료. **ROS 2 실제 실행·취소 통합 테스트는 미검증**.

## 위험과 수정

| ID | 등급 | 원래 구현 | 수정 |
|---|---|---|---|
| 2.6-01 | High | `MultiThreadedExecutor` 사용하지만 ActionServer에 별도 callback_group을 전달하지 않음. 기본 `MutuallyExclusiveCallbackGroup`에서는 실행 콜백 중 Cancel 콜백 진행이 지연/차단될 위험 | `ReentrantCallbackGroup`을 실제 `ActionServer(callback_group=...)`에 적용 |
| 2.6-02 | High | 유효성 검사 `target_number<=0`만: `period<0`이면 `time.sleep` 예외, NaN/무한대 및 비정상적으로 큰 goal 허용 | `1<=target<=1000`, `0.01<=period<=10`, finite 필터 |
| 2.6-03 | Medium | `time.sleep(period)` 전체에서 취소 확인 불가 | monotonic clock과 50ms 이하 구간으로 나눠 취소 플래그 확인 |
| 2.6-04 | Medium | 클라이언트 거절 시 done 표시 없어 `spin()` 무한 대기; 결과 콜백 내 `rclpy.shutdown()`으로 컨텍스트 종료 시점이 모호 | `finished` 상태로 정상/거절/서버 부재를 통합 관리하고 main의 finally에서 종료 |
| 2.6-05 | Medium | 서버·클라이언트 실행에 종료·리소스 해제 누락 | Executor shutdown, destroy_node 및 조건부 rclpy.shutdown 추가 |
| 2.6-06 | **선행 의존성** | `my_robot_interfaces/package.xml`의 `action_msgs` 누락 | **2.5절 브랜치에서 수정**. 이 브랜치만 독립 checkout 시 해당 패치가 없어 정상 빌드 보장 불가 |
| 2.6-07 | Info | 원고 '3가지 통신' 제목과 Goal/Result/Feedback/Cancel 4개 항목 불일치 | 액션은 **목표·결과·취소 서비스 및 피드백·상태 토픽**을 활용한다고 구분 |

## 변경 범위
- `count_until_server.py`: 콜백 그룹, 입력 검증, 취소 반응, 종료 자원관리.
- `count_until_client.py`: 서버 대기 timeout, goal 수락/거절/실패, result status 판정, node shutdown 수명.
- 기존 `CountUntil.action`의 Goal/Result/Feedback 필드 및 `setup.py` 콘솔 명령어는 그대로 유지.

## 검증 구분

| 항목 | 상태 |
|---|---|
| 기존 코드·인터페이스 정적 분석 | PASS (정적) |
| 취소 콜백 그룹·가드·종료 경로 코드 점검 | PASS (정적, 실행 아님) |
| colcon build / rosidl | **NOT RUN** |
| 정상 5카운트·피드백 5회·최종 status | **NOT RUN** |
| 목표 0, period 음수·NaN REJECT | **NOT RUN** |
| 실행 중 취소·중복 목표·SIGINT | **NOT RUN** |

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install
source install/setup.bash
# 터미널 A
ros2 run my_robot_system count_until_server
# 터미널 B
ros2 action send_goal /count_until my_robot_interfaces/action/CountUntil "{target_number: 5, period: 1.0}" --feedback
```

**중요**: 2.5절의 `action_msgs` 수정이 main에 병합되기 전이라면 2.6절 PR 리뷰 시 함께 적용된 브랜치에서 빌드 확인한다. 사용자가 취소 요청을 전송했을 때 **취소 수락·최종 상태 CANCELED**가 실제 관찰되어야 취소 기능 PASS다. `--feedback` 중 Ctrl+C는 CLI 자체 종료일 수 있어 **서버가 Goal을 취소했다는 증거가 아니다**. 취소 검증은 별도 ActionClient의 `cancel_goal_async()`와 status 검사가 필요하다.

참고: ROS 2 공식 Callback Groups 튜토리얼 및 Creating an action.
