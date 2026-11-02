# SECTION 8.1 코드·원고 정합성 리뷰 — 강화학습의 필요성

- 기준: 2026-10-20 KST, `main` 38fb4647aeff2d3ab951404d78e1812e598f2308
- 근거: 첨부 8장 원고 8.1~8.1.2, `Ch08/ros2_ws/my_robot_env.py`, `rl_env.py`, `train_reach.py`
- 검증 수준: GitHub 원격 소스 열람 및 정적 의미 검토. **MuJoCo/Gymnasium 실제 실행·ROS 2/WSLg 동작 검증은 수행하지 않음.**
- 판정: **교육용 개념 실습 조건부 적합, 본문 의사 코드의 직접 실행 불가**. 이번 브랜치는 리뷰 문서만 추가하며 소스는 수정하지 않는다.

## 학습 목표·대상 코드
독자가 관측→행동→보상→다음 관측의 흐름, MDP와 모델 기반 계획/강화학습의 역할 차이, sim-to-real의 의미를 설명할 수 있도록 한다. 8.1절 자체에 대응하는 별도의 실행 파일은 없다. 후속 절의 `my_robot_env.MuJoCoArmEnv`와 `rl_env.ReachEnv`의 `reset/step`가 구체적 실험 대상이다.

## 리뷰 결과
| ID | 심각도 | 근거 | 문제와 영향 | 권장 수정 |
|---|---|---|---|---|
| 8.1-R1 | HIGH(원고) | 8.1.1 의사 코드 `agent.predict()`, `agent.learn(state,...)` | 이 코드는 설명용이다. SB3 PPO의 `learn(total_timesteps=...)` API와 다르며 `compute_dynamics()`도 정의되지 않아 그대로 실행할 수 없다. | 의사 코드를 **비실행**으로 표시하고 실제 호출 `PPO(...).learn(...)`과 구분 |
| 8.1-R2 | MEDIUM | 8.1 서론·8.1.1 | MoveIt 2를 '자유공간만', 강화학습을 '접촉의 유일한 해법'으로 읽히게 해서는 안 된다. 계획+임피던스/힘 제어, 최적화·모델기반 제어도 가능하다. | 접근법의 장단점과 사용 조건을 병렬 비교 |
| 8.1-R3 | MEDIUM | 8.1.2 | 도메인 랜덤화·노이즈 주입은 소개되지만 현재 주력 `ReachEnv`에서 파라미터 랜덤화는 구현되어 있지 않다. | '향후 실습 예정/제안'과 '현재 구현' 분리 |
| 8.1-R4 | MEDIUM | 8.1.1, `my_robot_env.py`, `rl_env.py` | 원고는 Jazzy 연결 로봇 팔이라고 하지만 PPO 학습 환경은 독립 MuJoCo Python 클래스이며 ROS 2 컨트롤러와 직접 연결돼 있지 않다. | ROS 독립 학습과 후속 브리지 설계를 분리 |
| 8.1-R5 | LOW | 8.1.1 의사 코드 | `done`만 검사하면 Gymnasium의 `truncated` 처리가 빠진다. | 개념 예제도 `terminated or truncated` 설명 추가 |

## 확인된 사실과 한계
- `train_reach.py`는 `stable_baselines3.PPO`와 `ReachEnv`를 사용한다. 원고의 `agent.learn(state,action,...)`을 호출하지 않는다.
- `my_robot_env.py`는 3개 액추에이터/12차원 관측, 주력 `rl_env.py`는 6개 액추에이터/`model.nq + model.nv + 6`차원 관측이다. 모델 계약이 같지 않아 정책을 교차 투입하면 안 된다.
- 훈련 수렴·접촉 제어 성공·실기 이전의 안전성은 미검증이다.

## 검증 계획과 인수 조건
1. `cd Ch08/ros2_ws`에서 아래 실습 가이드의 관측/행동 출력 코드를 실행해 차원과 자료형을 기록한다.
2. `reset(seed=42)` 두 회의 목표 재현 여부, `terminated`/`truncated` 의미를 기록한다.
3. `PPO.learn(...)`와 설명용 의사 코드의 차이를 표로 정리해 설명할 수 있으면 개념 목표 통과.
4. 실제 실험에 대한 PASS는 **실험 증거(명령, 종료 코드, 로그, 환경 버전)** 확보 후 별도 기록한다.

## 관련 문서
- [실습 가이드](LAB_8_1_GUIDE_KO.md)
- [Ch12 문서 구성 참고](../../Ch12/README.md) (동일한 '절별 가이드/보고서' 체계를 따르되, Ch12 검증 결과를 Ch08의 결과로 전용하지 않음)
