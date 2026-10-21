# SECTION 8.5 코드 리뷰 — 보상 함수와 안전성

- 기준: 2026-10-20 / main `38fb4647aeff2d3ab951404d78e1812e598f2308`
- 검토 범위: 원고 8.5.1~8.5.6 및 `Ch08/ros2_ws/rl_env.py`의 `calculate_reward()`, `reset()`, `step()`, `evaluate_robot.py`
- 결론: **보상 계산 구조는 존재하나 통계 계약과 평가 지표의 정합성 결함**. 정적 확인, 실험 미실행.

## 현재 실제 보상
`r_dist = -||EE-target||₂`, `r_ctrl=-sum(action²)`, `r_smooth=-sum((action-last_action)²)`, `r_contact=-data.ncon`, `r_bonus=10.0` (distance<0.05)이며 합계는
`1.0*r_dist + .01*r_ctrl + .05*r_smooth + .01*r_contact + r_bonus`. 원고의 `compute_reward`가 아니라 `calculate_reward`라는 메서드명이다. `last_action`은 `reset`에서 초기화, `step`에서 보상을 계산한 뒤 갱신한다.

## 리뷰 이슈
| ID | 등급 | 근거 | 수정/분석 |
|---|---|---|---|
| 8.5-R1 | HIGH | `calculate_reward`의 반환 info에는 `distance`가 없다. `evaluate_robot.py`는 `if 'distance' in info`에서만 거리 취합, 없으면 SSE를 `0.0`으로 출력 | 실제 거리도 info로 반환; 데이터 0건은 `N/A`로 표시하고 0mm '완벽' 판정 금지 |
| 8.5-R2 | HIGH | `reset()`에서 목표는 랜덤 생성되지만 도달가능 workspace/충돌 제약을 이용한 성공 가능성 검사는 없다. | 목표 샘플의 도달 가능 비율/거리 분포와 실패 유형 측정 |
| 8.5-R3 | MEDIUM | `data.ncon`으로 모든 접촉을 동일하게 벌점 처리 | 정상 접촉/위험 접촉 구분; 충돌 비활성인 링크의 제약도 별도로 검토 |
| 8.5-R4 | MEDIUM | 원고 8.5.3의 `compute_reward`와 실제 `calculate_reward`가 이름·추가 항·가중치 불일치 | 8.4에 적용된 최종 함수 중심으로 수식·예시 수정 |
| 8.5-R5 | MEDIUM | `last_action`은 초기에 zero지만 에피소드 리셋과 물리 ctrl 상태의 전면 초기화가 불완전할 수 있다 | `mj_resetData`와 action history 순서 회귀 테스트 |
| 8.5-R6 | MEDIUM | 제어 규제화는 정규화 행동 크기; 전력 소비나 실제 모터 jerk(Nm/s³)의 직접 측정값 아님 | 'Action difference'와 '물리 토크/에너지/jerk' 용어 구분 |
| 8.5-R7 | LOW | 원고 8.5.3 다음이 8.5.5로 넘어간다 | 소절 8.5.4의 원고 누락/번호 확인 |

## 최소 검증 계약
- 고정된 `ee_pos`, `target_pos`, `action`, `last_action`으로 항목별 반환 부호/합을 계산한다.
- `distance=0.049`와 `0.051`의 성공 경계 비교.
- 액션이 동일할 때 `r_smooth=0`; 최대 반대 방향일 때 음수가 되는지 검사.
- 여러 시드·목표에서 성공률과 거리·충돌 페널티를 분리해 기록. 보상 총합 상승만으로 성공 판정하지 않는다.

**검증 상태:** 수식·메서드 구조 정적 확인 완료; MuJoCo 런타임·학습 곡선/물리성능 미검증. 문서만 변경.

[실습 가이드](LAB_8_5_GUIDE_KO.md)
