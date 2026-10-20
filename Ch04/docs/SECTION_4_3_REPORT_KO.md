# 4.3절 코드 리뷰: Dynamic TF Broadcaster

- 검토 기준: `main@7b7c10f`, 2026-10-20 KST
- 작업 브랜치: `feat/ch04-section-4-3`
- 실제 파일: `Ch04/ros2_ws/src/my_robot_tf/my_robot_tf/dynamic_tf_broadcaster.py`
- 최종 판정: **핵심 예제 구조 타당; 시간·속도 의미를 명확히 해야 함. 실제 ROS 런타임 검증 미수행.**

## 1. 코드 경로 및 검토 내용

`DynamicFramePublisher`는 `TransformBroadcaster(self)`와 `create_timer(0.033, ...)`를 사용한다. 매 콜백마다 `header.stamp`를 갱신하고 `world→turtle_frame`으로 TF를 보낸다. 위치는 `x=2cosθ, y=2sinθ, z=0`, 자세는 `yaw=θ+1.57`이며, `setup.py`의 `dynamic_tf_broadcaster` 실행 항목은 존재한다. 쿼터니언 함수에서 0 roll/pitch 조건의 수식 자체는 정상적인 yaw 쿼터니언과 부합한다.

## 2. 이슈 목록

| ID | 등급 | 소스 근거 | 영향·개선안 |
|---|---|---|---|
| 4.3-R1 | Medium | `self.theta += 0.05` + `timer_period=0.033` | **실제 경과 시간과 독립적인 고정 증분**. 노드가 지연되면 각속도도 달라진다. 강의에서는 약 `0.05/0.033≈1.515 rad/s`의 이상적인 콜백 속도임을 명시. 실무에서는 ROS 시계로 계산한 `dt`를 사용. |
| 4.3-R2 | Low | `yaw=theta+1.57` | 원운동의 **접선 방향**을 바라보기 때문에 +π/2를 더한다. `1.57` 대신 `math.pi/2` 권장. |
| 4.3-R3 | Medium | `world`와 `turtle_frame`만 방송 | RViz에 TF 축만 표시되며 터틀봇의 3D 메시나 궤적 Path가 자동으로 그려지는 것은 아니다. 원고의 '궤적'은 시간에 따른 움직임 관찰과 구별. |
| 4.3-R4 | Medium | 자동 테스트가 없는 패키지 | 반지름 불변, 정규화 quaternion, 증가하는 타임스탬프·프레임 방향·발행 Hz 검증 필요. |
| 4.3-R5 | Medium | `use_sim_time` 파라미터 미설정 | 단독 데모는 시스템 시간 기준이다. Gazebo 연동 시 /clock과 시간원 통일 요구. |
| 4.3-R6 | Low | 정적·동적 TF 함께 사용할 때 | `world`의 정적 parent를 다르게 발행하지 말고 `turtle_frame` 중복 발행을 피해야 함. |

## 3. Acceptance Contract

- `ros2 pkg executables my_robot_tf`에 `dynamic_tf_broadcaster` 등록됨.
- `ros2 run tf2_ros tf2_echo world turtle_frame`이 갱신되며 값은 `x²+y²≈4` 만족.
- 이상적인 각속도는 약 1.515 rad/s (정확한 실측 Hz, 콜백 지터 보장 안 함).
- 방향은 위치각 `atan2(y,x)`에 비해 약 90도 접선 선행.
- TF 시간은 증가하고 quaternion norm은 1 근처.

## 4. 테스트 및 수정 상태

| 항목 | 판정 |
|---|---|
| Python 소스 및 entry point 정적 대조 | 수행 |
| 시간 의존 로직·궤도 수학 리뷰 | 수행 |
| ROS 2 Jazzy import / `colcon build` / 30Hz 실측 | **NOT RUN** |
| RViz 시각 검증 | **NOT RUN** |
| 소스 변경 | 없음(문서화만 요청 범위) |

실기동과 런타임에서 발생할 수 있는 QoS/타임스탬프 오류의 부재는 보증할 수 없다. 재현 명령과 관찰 지표는 [LAB_4_3_GUIDE_KO.md](LAB_4_3_GUIDE_KO.md)에 기술한다.

참고: [ROS tf2 dynamic broadcaster](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Broadcaster-Py.html)
