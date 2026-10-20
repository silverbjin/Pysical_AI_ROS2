# 6.1절 실습 가이드 — 2자유도 IK를 직접 관찰하기

> 기준: 2026-10-20 KST · GitHub main 1b9e8215e213 · 원고 6.1절 · ROS 2 Jazzy / Ubuntu 24.04 기준
> 범위: 저장소 소스 및 원고 정적 검토. 현재 세션에 ROS 2/Gazebo 실행 환경이 없으므로 실제 빌드·GUI·물리 시뮬레이션 결과는 **미검증**이다. 성공·PASS를 추정하지 않는다.
> 검토 대상: https://github.com/silverbjin/Pysical_AI_ROS2/tree/1b9e8215e2130c492969bb0da52a82e707c3a16f/Ch06

## 학습 목표
FK/IK 차이, 야코비안의 의미, 초기값·특이점·작업영역이 결과에 미치는 영향을 수치와 그래프로 확인한다. **따라 실행 → 오차 확인 → 실패 원인 설명** 순서로 학습한다.

## 준비 및 실행
```bash
cd ~/Pysical_AI_ROS2  # 실제 clone 위치로 바꾸기
python3 -m venv /tmp/ch06-ik-venv
source /tmp/ch06-ik-venv/bin/activate
python -m pip install numpy matplotlib
python3 Ch06/1_simple_ik_concept.py
python3 Ch06/2_simple_ik_concept_animated.py
python3 Ch06/3_interactive_ik_solver.py
python3 Ch06/4_divergence.py
```
GUI 실행 시 WSLg/X11 창을 확인한다. `2_simple...`은 Space 키로 시작/정지, `3_interactive...`는 목표 및 초기각을 슬라이더로 변경, `4_divergence.py`는 발산·롤백을 비교한다.

## 따라 하기
1. `1_simple_ik_concept.py`를 실행하고 최종 각도(rad)를 다시 FK에 입력하여 목표 (0.7,0)m와 거리 오차를 계산한다. tolerance는 0.001m, 즉 1mm다.
2. 코드에서 목표를 (1.2,0)m로 변경하고 도달 가능 여부와 반복 종료 메시지를 기록한다(링크 합=1m).
3. 초기 관절값을 (0,0)rad와 다른 seed로 바꾸어 반복 횟수와 결과를 비교한다. 특이점에서 역행렬·의사역행렬·DLS의 차이를 토의한다.
4. `2_simple...`에서 팔 끝단의 흔적과 Delta Theta가 감소하는 구간을 찾는다. `3_interactive...`에서 작업영역 바깥 목표를 넣고, 그래프 종료와 수렴을 구별한다.
5. `4_divergence.py`에서 alpha를 변경해 큰 갱신량·롤백 현상을 관찰한다. 이 코드는 **의도적인 실패 시각화**이며 실제 모터에 보내지 않는다.

## 확인 기준 및 기록
| 증거 | 합격 기준 |
|---|---|
| FK/IK | 도달 가능 목표의 최종 거리 오차가 1mm 미만인지 실제 산출, 미달이면 FAIL 기록 |
| 작업영역 | 목표 반경이 1m 초과하면 해가 없음을 설명할 수 있음 |
| 특이점 | `det(J)≈0` 및 작은 특이값에서 수치 불안정 이유 설명 |
| 그래프 | 각도·델타·말단 궤적·오차 스냅샷 1개 이상 저장 |

## 오해 방지
`pinv`는 기하학적 비도달 목표를 도달 가능하게 만들지 않는다. 실시간 제어·관절 한계·충돌 검사 기능도 없다. 간단한 수치 예제를 통과했다고 MoveIt이나 Gazebo 실행이 검증된 것은 아니다.

참고: [1번 스크립트](https://github.com/silverbjin/Pysical_AI_ROS2/blob/main/Ch06/1_simple_ik_concept.py), [검토 보고서](SECTION_6_1_REPORT_KO.md).
