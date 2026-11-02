# 4.1절 코드 리뷰: 로봇 좌표계의 이해와 TF2

- 기준일: 2026-10-20 (KST)
- 기준 원격: `main@7b7c10f25194c770d0adc80b3f02b5493da94c8a`
- 브랜치: `feat/ch04-section-4-1`
- 대상 원고: 4.1.1~4.1.5
- 판정: **설명·CLI 실습 가능 / 별도 4.1 실행 프로그램 없음**
- 검증 수준: GitHub 소스·원고·공식 규약의 **정적 점검**. 이 환경에서 ROS 2 노드 및 RViz 실기동 미수행.

## 1. 실제 코드 자산 및 범위

`Ch04/ros2_ws/src/my_robot_tf/`는 `static_tf_broadcaster.py`, `dynamic_tf_broadcaster.py`, `tf_listener.py`, `multi_static_tf.launch.py`를 포함한다. 4.1절 전용 Python 예제나 테스트는 없다. 개념 학습용으로 4.2절의 표준 CLI `static_transform_publisher`를 재사용하는 것은 적절하다. 3장의 로봇 형상을 전제로 하더라도 4.1절의 좌표계 학습은 외부 모델 없이 독립적으로 진행할 수 있다.

## 2. 발견사항

| ID | 중요도 | 근거 | 문제 및 개선 조치 |
|---|---|---|---|
| 4.1-R1 | Medium | 4.1.2 원고 | TF는 프레임별 부모가 최대 1개인 트리/연결 요소로 구성되며, 프레임이 반드시 전부 연결된 것은 아니다. '모두 서로 연결' 표현을 '연결된 트리 안'으로 한정한다. |
| 4.1-R2 | Medium | 4.1.3 원고 | `map`은 전역적으로 일관된 기준이지만 엄밀한 '절대좌표'는 아니다. `odom`은 연속적이지만 드리프트할 수 있고, `map→odom`은 위치 추정기가 갱신한다. |
| 4.1-R3 | Medium | 4.1.4 원고 | 기본 로봇 좌표축 전방 +X, 좌측 +Y, 위쪽 +Z와 카메라 optical frame의 별도 축 규약을 구분한다. RPY는 특정 축·순서 계약에 의존한다. |
| 4.1-R4 | Low | 4.1.5 원고 | `TransformStamped.header.frame_id`는 부모, `child_frame_id`는 자식; 변환은 '부모 기준 자식 포즈'로 읽는다. `tf2_echo` 인자 방향과 구분해 연습한다. |
| 4.1-R5 | Medium | Ch04 패키지 | 버퍼·프레임 관계·쿼터니언 정규화에 대한 자동화 테스트가 없다. 다음 절까지 연결되는 최소 진단 체크리스트가 필요하다. |

## 3. 실습 계약 및 Acceptance

- 부모 `world`, 자식 `base_link`를 서로 다른 프레임으로 선언하고 하나의 정적 TF를 제공한다.
- `tf2_echo world base_link`로 기대하는 위치·단위 쿼터니언을 확인한다.
- `ros2 topic info /tf_static -v`에서 transient-local durability와 게시자를 확인한다.
- `view_frames`로 연결/비연결, 순환 및 중복 부모를 점검한다.
- 같은 `child_frame_id`를 다른 발행자에서 동시에 발행하지 않는다.

## 4. 테스트 상태

| 검사 | 판정 |
|---|---|
| 원고 4.1절 분류와 코드 파일 유무 확인 | 정적 확인 |
| TF 메시지의 의미·프레임 방향 검토 | 정적 확인 |
| Jazzy 환경의 `tf2_echo`·RViz·`view_frames` 실측 | **NOT RUN** |
| 자동 테스트, colcon 빌드 | **NOT RUN** |

실제 실행 수치, 화면 검증, PASS 개수는 생성하지 않았다. [실습 가이드](LAB_4_1_GUIDE_KO.md)에 재현 명령과 체크포인트를 제공한다.

## 5. 출처

- 코드: [Ch04 my_robot_tf](https://github.com/silverbjin/Pysical_AI_ROS2/tree/main/Ch04/ros2_ws/src/my_robot_tf)
- 규약: [REP 105](https://www.ros.org/reps/rep-0105.html), [REP 103](https://www.ros.org/reps/rep-0103.html)
- 다음 절: [4.2절 보고서](SECTION_4_2_REPORT_KO.md) (해당 브랜치 병합 후 접근)
