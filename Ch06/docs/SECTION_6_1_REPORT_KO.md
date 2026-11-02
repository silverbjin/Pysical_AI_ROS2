# 6.1절 코드 리뷰 — IK 기초 수치해석

> 기준: 2026-10-20 KST · GitHub main 1b9e8215e213 · 원고 6.1절 · ROS 2 Jazzy / Ubuntu 24.04 기준
> 범위: 저장소 소스 및 원고 정적 검토. 현재 세션에 ROS 2/Gazebo 실행 환경이 없으므로 실제 빌드·GUI·물리 시뮬레이션 결과는 **미검증**이다. 성공·PASS를 추정하지 않는다.
> 검토 대상: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 대응 원고와 코드
- 원고 6.1.1~6.1.2: 다중 해, 작업공간, 특이점, 야코비안 기반 IK.
- 실제: `Ch06/1_simple_ik_concept.py`, `2_simple_ik_concept_animated.py`, `3_interactive_ik_solver.py`, `4_divergence.py`. 뒤의 세 파일은 원고의 단일 예제를 시각화·실험으로 확장한다.

## 정적 검토 결과
| ID | 수준 | 근거 | 판단 및 수정 제안 |
|---|---|---|---|
| IK61-01 | MEDIUM | 첫 3개 예제의 `np.linalg.pinv(J)`, 고정 `learning_rate=0.1`, 반복 상한 100/150 | 의사역행렬만으로 특이점 근방의 큰 관절 업데이트가 안전해지지 않는다. DLS, 최대 스텝 및 오차 로그를 도입한다. |
| IK61-02 | MEDIUM | 솔버는 위치 오차만 계산하며 관절 상·하한, joint speed, 충돌을 검사하지 않음 | 이 파일은 제어기가 아닌 **개념 학습용**이라고 명시하고 로봇 모터에 연결하지 않는다. |
| IK61-03 | MEDIUM | animated/interactive 함수는 계산 기록을 반환하지만 최종 성공 여부·오차를 명시적으로 반환하지 않음 | 애니메이션 종료와 수렴을 구분하고 실패 상태(ITER_LIMIT, OUT_OF_REACH)를 표시한다. |
| IK61-04 | LOW | `4_divergence.py`는 의도적으로 `np.linalg.inv(J)`를 사용하고 작은 행렬식/큰 업데이트에서 중단 | 안전한 실습이 아니라 발산 재현 실험임을 명시하고 baseline과 수치값 비교에만 사용한다. |
| IK61-05 | LOW | GUI 예제 `plt.show()`, Matplotlib animation/slider 의존 | WSLg 또는 그래픽 백엔드 필요. 무창 환경에서 GUI 성공을 주장하지 않는다. |

## 검증 계약
- 정적: Jacobian 미분식은 2링크 평면팔의 FK 식과 일치한다. 링크 길이 0.5m+0.5m에 대한 최대 반경은 1.0m이다.
- 미실행: `python3 Ch06/1_simple_ik_concept.py`, GUI 2~4, 수치 결과·프레임 렌더링.
- 재현: 목표 (0.7,0), (1.2,0), 초기 `theta=(0,0)`, 다른 seed를 각각 실험한다. 최종 `||FK(theta)-target||<1e-3`인 경우만 수렴 PASS. 도달 불가 목표가 조용히 성공 처리되지 않는지 확인한다.

## 개선 우선순위
1. 수렴 결과 구조화(최종오차·iteration·status), 테스트 자동화.
2. 스텝 제한·DLS 및 seed 민감도 비교. 개선 전에는 `pinv`가 특이점을 '해결'한다고 가르치지 않는다.
3. 그래프에서 마지막 상태와 목표 오차를 명확히 구별한다.

**판정: 교육용 개념 자료로 활용 가능(조건부). 로봇 안전 제어 코드로 사용 불가. 실제 실행 검증 미완료.**
