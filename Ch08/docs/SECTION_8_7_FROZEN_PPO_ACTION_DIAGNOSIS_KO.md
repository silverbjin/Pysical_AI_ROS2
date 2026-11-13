# Ch08 §8.7 — 원본 저장 PPO 행동·포화·보상 진단 공개 CI 검수

> 실제 실행일: 2026-11-13. **정량 행동 진단의 SCOPED PASS**이며, 정책의 목표 도달률·안정성 PASS는 아니다.

## 검수 배경과 범위

- 기존 원본 PPO 10개 시드×최대 300스텝 평가 [#43361732383](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43361732383)는 **목표 성공 0/10**, 평균 최종 EE 거리 0.432753m였다. 이번에는 해당 전체 평가를 반복하지 않았다.
- 기존 원본 MuJoCo 기하학 [#43417674577](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43417674577)은 위치 IK **10/10**, 별개 시험용 PD 토크 제어 [#43422430577](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43422430577)은 세 시드 **3/3** 목표 도달을 확인했다. 이는 **PPO의 성능이 아니다.**
- 새 진단은 기존 저장 PPO ZIP을 수정하지 않고 CPU에서 로드하여 시드 1000~1002를 각 **120 원본 ReachEnv.step = 1.2초**만 실행했다. 모든 액션과 원본 reward info 및 실제 joint state를 기록한다.

## 실제 원본 PPO 실행 데이터

| 시드 | 시작 EE 거리(m) | 실행 중 최소거리(m) | 종료거리(m) | 모터 포화율 (|action|≥0.98) | 연속 액션 변화 L2 평균 |
|---:|---:|---:|---:|---:|---:|
| 1000 | 0.76361 | **0.35519** | 0.75964 | 0% | 0.05428 |
| 1001 | 0.83627 | **0.29269** | 0.48632 | 0% | 0.04847 |
| 1002 | 0.92998 | **0.19856** | 0.20011 | 0% | 0.05199 |

- **실제 목표 거리 0.05m 이내 도달 없음(이 짧은 세 시드 진단에서만).** 이미 검증된 전체 정책 0/10 성능 실패는 변경되지 않는다.
- 시드 1000의 최소 0.35519m 이후 종료 거리는 0.75964m, 시드 1001의 최소 0.29269m 이후 종료 거리는 0.48632m였다. **접근 후 재이탈**이 존재하여 일시적 거리 감소를 목표 정착·성공으로 잘못 해석해서는 안 된다.
- 모든 모터와 모든 360개 스텝에서 |action|≥0.98 포화 비율은 **0%**였다. 입력이 원본 MuJoCo actuator ctrl에 그대로 전달되는 것도 검증했다. 단, 포화가 없다고 모터 사용이 안전하거나 충분히 강하다고 추론할 수는 없다.
- 원본 정책의 실제 액션은 0 또는 일정 상수만 출력하지 않았다. 명령별 signed mean, mean absolute, 표준편차, near-zero 비율과 타임스탬프는 raw receipt에 있다.

## 목표 조건 민감도 및 보상 구성 요소

- 상태를 고정한 채 원본 시드 1000~1009의 **목표 좌표만 변경**한 10회 deterministic PPO 추론에서 최대 두 액션의 L2 차이는 **0.124649**이었다. 각 motor별 목표 조건 액션 span은 **[0.03119, 0.06800, 0.04035, 0.07410, 0.01344, 0.06783]** 이었다.
- 이 수치는 특정 한 로봇 상태에 한정된 제어 변수 민감도다. 0은 아니므로 '목표를 전혀 무시한다'고 단정할 수 없고, 다른 상태나 학습 데이터의 일반화 성능도 이 숫자만으로 판단할 수 없다.
- 이번 세 짧은 rollout의 실제 원본 보상 항목 합계는 **거리 −221.52184, 제어 비용 −1.75747, 액션 변화 비용 −0.18073, 접촉 비용 −0.70000, 목표 보너스 0**이었다. 모든 원본 step reward가 구성 요소 합과 정확히 부합하는 것을 독립 감사했다.
- 이번 조건에서는 거리 손실이 다른 비용보다 훨씬 크다. 그렇다고 실제 장기 학습에서 거리 보상이 충분히 효과적이었다는 결론이나 smoothness penalty가 실패의 원인이라는 결론은 아직 불가능하다.

## 증거 체인

- 전용 공개 CI: [Run #43426946500](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43426946500) — SUCCESS.
- 원본 Artifact: [#14038346717](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43426946500/artifacts/14038346717), `receipt.json`, `trace_seed_1000.json`~`1002.json`, `frozen_actions.log`, `independent_audit.log`, `pip_freeze.txt`, `checkout_sha.txt` 포함.
- 독립 감사 마커: `CH08_87_INDEPENDENT_FROZEN_PPO_ACTION_AND_REWARD_RECEIPT_PASS steps=360 max_goal_conditioned_action_delta=0.124649`.
- 실제 PR CI checkout SHA: `ca7d5beab5112e2a72c4001861ae5405171928b7`; 저장 PPO ZIP SHA256 `78f85cc0d8cee868b66fe6b538fcf7b7a64b2d65632bd8036c01d8afeaceda92`, XML `ffa277c1eda287e76279153c5c48075c0f8f03676ff6cde4fa0e7802e84daa99`, 환경 소스 `c89a8bd1b2cac0ca230b98aa01f765a517af9e6ca6dff064a879531c9f83439f` — 변경 없음.
- 실행기 `ci/ch08_87_frozen_ppo_actions_once.py`, 감사 `ci/ch08_87_verify_action_diagnostic.py`, CI `.github/workflows/book-ch08-87-frozen-action-diagnostics.yml`.

## 다음 개선 경계

1. **정책의 폐루프 유지·조기 이탈:** 실제 EE 속도, 목표 방향 성분과 action 반응을 같은 시드의 목표 최소거리 전·후로 나눠 분석하여 지나침/방향 역전/중력 영향 여부를 구분한다. 단일 진단 없이 reward 파라미터를 무작정 바꾸지 않는다.
2. **목표 조건 민감도:** 목표 좌표만 바꿨을 때의 출력 차이가 상태 변화 대비 얼마나 작은지, 여러 초기 상태 및 목표 배치에서 재현되는지 검증한다.
3. **별도 PPO 개선:** 원본 ZIP 보존, 신규 모델 SHA·학습 설정·시드와 결과 분리. 실제 도달 성공 판정은 원래 0.05m 반경, 기존 10개 시드 + 독립 홀드아웃 시드로 수행한다.

**판정:** 저장된 원본 PPO의 실제 액션/보상/목표 민감도 측정·독립 감사 **SCOPED PASS**. 기존 저장 PPO 정책의 10/10 성공이 아니라 **0/10 성능 미달 유지**. GUI·실물 로봇·충돌 안전성 NOT_RUN, Ch07 OGRE2 RGB-D #127 BLOCKED, Ch10 #123 HOLD.
