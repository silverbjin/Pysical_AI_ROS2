# 4.4절 코드 리뷰: TF2 Listener

- 기준: `main@7b7c10f` / 2026-10-20 / `feat/ch04-section-4-4`
- 대상: `Ch04/ros2_ws/src/my_robot_tf/my_robot_tf/tf_listener.py` 및 선행 `dynamic_tf_broadcaster.py`
- 상태: **핵심 4.3→4.4 TF 조회 구조 타당; 원고 시나리오와 실제 조회 프레임 차이·시간 동기화 설명 보완 필요.**
- 검증: 원격 소스 정적 검토. 실제 ROS 2 실행 **NOT RUN**.

## 1. 실제 코드 계약

`FrameListener`는 `Buffer()`·`TransformListener(self.tf_buffer,self)`를 생성하고 1.0초 타이머를 사용한다. `lookup_transform('world','turtle_frame',rclpy.time.Time())`으로 가장 최신 공통시각의 변환을 요청하며 `TransformException`을 처리한다. 받은 x,y로 **2차원 평면 거리** `sqrt(x*x+y*y)`를 계산한다. `setup.py`에는 `tf_listener` entry point가 있다.

## 2. 발견 사항

| ID | 중요도 | 발견·근거 | 개선·검증 방안 |
|---|---|---|---|
| 4.4-R1 | High(원고/코드 불일치) | 4.4.2는 `police_bot` 관측자, 실제 코드 target은 `world`이며 `police_bot` 프레임은 **어디에도 발행되지 않음** | 가이드에서는 관측자를 world 원점과 동일하게 정의. 진짜 `police_bot` 조회가 필요하면 `world→police_bot` static TF를 추가하고 target을 변경. |
| 4.4-R2 | Medium | `Distance`는 x,y만 사용 | 원고의 평면 거리 계약임을 분명히 한다. 3D 거리 필요하면 z까지 제곱합 포함. |
| 4.4-R3 | Medium | 노드 시작 시 버퍼가 비어 있을 수 있음 | `TransformException` catch는 이미 존재. 시작 직후 일시적 조회 실패를 곧바로 실습 실패로 분류하지 말 것. |
| 4.4-R4 | Medium | 원고의 과거 메시지 조회 스니펫 `msg.header.stamp`를 직접 전달 | Jazzy Python API는 `rclpy.time.Time.from_msg(msg.header.stamp)`와 같은 시간 객체 변환 필요. 단일 스레드 콜백에서 동기 timeout 대기는 교착·지연 가능: callback group/executor 또는 async 조회 검토. |
| 4.4-R5 | Low | `from rclpy.duration import Duration`이 미사용 | lint 청결도 개선. 기능 오류는 아님. |
| 4.4-R6 | Medium | TF의 최신값 조회 vs 센서시각 조회 | 최신 공통시각 조회는 센서 캡처 시점과 다를 수 있어 인식·제어에서 `header.stamp`와 동기화해야 한다. |

## 3. 최소 재현 및 합격 기준

1. 4.3절 방송 노드 실행 후 4.4절 리스너 시작.
2. `Detected` 로그가 매초 갱신되고 x,y는 변경, `Distance≈2.00m`.
3. 방송 노드 종료 시 조회 불가 로그가 나올 수 있으며 리스너가 예외로 종료되지 않아야 함.
4. `tf2_echo world turtle_frame` 출력과 리스너 값의 방향·범위를 교차 확인한다.
5. 의도적으로 `police_bot`로 target을 바꿨을 때 미발행 프레임 예외가 발생함을 이해한다.

## 4. 검증 상태와 판정

| 확인 | 결과 |
|---|---|
| Buffer/Listener/try-except 구조, entry point | 정적 점검 |
| `world` 조회 vs 원고 `police_bot` 차이 | **문제 확인** |
| `colcon build`, 실제 listener 로그·거리 수치 | **NOT RUN** |
| 다중 executor/시간 스탬프 센서 통합 | 범위 밖, **NOT RUN** |

코드 변경 없이 사용자가 실제 확인할 절차와 수정 방향을 [LAB_4_4_GUIDE_KO.md](LAB_4_4_GUIDE_KO.md)에 명시한다.

출처: [ROS 2 tf2 listener](https://docs.ros.org/en/jazzy/Tutorials/Intermediate/Tf2/Writing-A-Tf2-Listener-Py.html).
