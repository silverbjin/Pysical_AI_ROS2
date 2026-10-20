# 6.7절 코드 리뷰 — IK 실패 모드 및 진단

> 기준일 2026-10-20 KST | 기준 main `1b9e8215e213` | 첨부 원고 6.7절 | Ubuntu 24.04 · ROS 2 Jazzy · MoveIt 2
> 판정 수준: **정적 검토**. 실제 ROS 2/WSLg/Gazebo 실행·테스트 로그가 이 작업에는 없으므로 동적 검증은 미수행/미검증으로 표시한다.
> 원본 경로: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 실습 경계
원고 6.7.1~6.7.5(특이점·다중해·와인딩·툴 간섭·실시간성)는 별도의 `section6_7.py` 완성 코드를 제공하지 않는다. 관련 실제 구현은 개념 시각화 `Ch06/4_divergence.py`와 `hello_moveit.py`, `cartesian_path.py`, YAML/URDF. 원고 중 예시 코드를 **현재 저장소에서 그대로 실행 가능한 코드로 오인하면 안 된다**.

## 검토/교정
| ID | 수준 | 원고/코드 문제 · 보완 |
|---|---|---|
| IK67-01 | HIGH | 6.7의 `arm_group.get_current_state()`→`set_start_state(current_joint_values)` 예시는 현행 MoveItPy 함수 인자·객체와 일치하는지 불명. 실제 코드에선 `set_start_state_to_current_state()` 사용. 문서 API로 검증한 후 수정 필요. |
| IK67-02 | HIGH | OrientationConstraint 예시에서 `Constraints` import/전달 인자 및 사용 가능한 메서드 검증이 빠져 있음. 설정은 '도달한다' 보증이 아니라 계획 제약이며 경로/플러그인 지원 확인 필요. |
| IK67-03 | HIGH | `Trac-IK=내부 DLS`로 단정한 문구는 확인된 구현 설명이 아니다. 특이점에서 모든 폭주를 방지한다고 보장 금지; 수치 Jacobian condition 및 실행 제한 필요. |
| IK67-04 | HIGH | 관절 한계 예시에서 `revolute`를 `continuous`로 임의 변경하면 실제 하드웨어의 케이블·기구 한계를 우회할 위험. 지원 장치가 확인된 관절에만 허용. |
| IK67-05 | MEDIUM | `default_collision_padding: 0.05`만으로 케이블-장애물 거리가 전 경로 5cm 이상임을 보장할 수 없음. 실제 충돌 형상/패딩 적용 위치/ACM 제외 쌍 검사 필요. |
| IK67-06 | MEDIUM | 실시간 작업에서 solver timeout만 5ms로 낮추거나 'visual servoing이 유일 해법'으로 표현하는 것은 과도한 일반화. 측정한 지연·동작 시스템 요구에 따라 Servo/replanning/예측 제어 비교가 필요. |
| IK67-07 | MEDIUM | `4_divergence.py`는 시각화를 위해 명시적으로 `np.linalg.inv(J)`와 발산 역학을 사용함. 실제 관절/속도 제한 없이 안전 제어 코드로 재사용하면 안 된다. |

## 검증 계획(미수행)
- 특이점: `min singular value`, `condition number`, `||Δθ||`, 목표 오차를 각 seed에서 로그.
- 다중 해: 서로 다른 seed의 궤적·연속 joint 차분/시간 재매개변수화 비교.
- 관절 한계: URDF limits와 실제 controller constraints가 일치하고 위반을 거부하는지 테스트.
- 환경 충돌: Planning Scene 장애물·tool collision geometry 및 ACM을 확인하고 경로 전 샘플 충돌 검사.
- 지연: IK/계획/실행 시간 분포(평균뿐 아니라 P95/P99), stale feedback, 회복 조건 기록.

**판정: 개념 토론 자료로 적합, 검증된 '실무 완성 안전 솔루션'으로 단정 불가. 현장 로봇 실행 금지.**

근거: [MoveItPy 예제](https://github.com/moveit/moveit2_tutorials/blob/main/doc/examples/motion_planning_python_api/motion_planning_python_api_tutorial.rst), [MoveIt 충돌/Servo 자료](https://moveit.picknik.ai/main/index.html).
