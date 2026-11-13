# Ch08 §8.7 후속 검수: 저장된 PPO 0/10 실패 목표의 실제 MuJoCo 기구학적 접근성

> 2026-11-13 KST, 공개 CI 실제 실행 수치 보고서. **기구학 IK 검수와 PPO 학습·동역학 성공률을 구분한다.**

## 검수 목적과 선행 증거

기존 원본 저장 PPO 모델의 정량 평가 [CI #43361732383](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43361732383) 및 [PR #145](https://github.com/silverbjin/Pysical_AI_ROS2/pull/145)는 10개 고정 시드(1000–1009)에서 **목표 도달 0/10, 평균 최종 거리 0.432753m**였다. 평가 도구의 거리 계산은 별도 PASS였으나 정책 성능은 불합격이었다.

이번 신규 검수는 원인을 분리하기 위해 같은 10개 시드의 **원본 `ReachEnv.reset` 목표를 사용**했지만, 저장된 PPO는 **다시 추론하거나 훈련하지 않았다**. 원본 MuJoCo XML의 6관절에 대해 `mj_jacSite` 기반 3D 위치 Jacobian과 한 스텝 최대 0.20rad의 테스트 전용 DLS로 IK 해를 8개 시작 자세에서 검색했다. `mj_forward`만 호출했으며 `mj_step`, 실제 토크·충돌·제어기나 하드웨어는 실행하지 않았다.

## 독립 원본 측정

| 시드 | 시작 EE 목표 거리(m) | 최량 IK 잔여거리(m) | 위치 IK |
|---:|---:|---:|:---:|
| 1000 | 0.76361 | 0.01096 | 가능 |
| 1001 | 0.83627 | 0.01112 | 가능 |
| 1002 | 0.92998 | 0.01107 | 가능 |
| 1003 | 0.86717 | 0.01069 | 가능 |
| 1004 | 0.86129 | 0.01091 | 가능 |
| 1005 | 0.77309 | 0.01782 | 가능 |
| 1006 | 0.97018 | 0.01544 | 가능 |
| 1007 | 0.88431 | 0.02299 | 가능 |
| 1008 | 0.82348 | 0.00875 | 가능 |
| 1009 | 0.89640 | 0.01152 | 가능 |
| **평균** | **0.86058** | **0.01313** | **10/10** |

- **원본 샘플 목표 10개 모두에서** 원래 성공 판정 임계값 `0.05m` 안의 위치 IK 해를 찾았다. 잔여거리 최솟값 `0.00875m`, 최댓값 `0.02299m`.
- 6개 original MuJoCo hinge 관절 모두 `jnt_limited=True`; 제약 범위는 joint1/4/6 ±π, joint2/3 ±2.61799rad, joint5 ±2.09440rad. 기구학 업데이트는 원본 제한을 넘기지 않도록 clamp했다.
- 해를 못 찾은 것은 절대적 도달 불가능의 증명이 아니며, 발견한 해도 **동역학적으로 안정적이고 안전하게 도달한다는 증거는 아니다**.
- 따라서 기존 0/10 실패를 **10개 목표가 모두 기구학적으로 도달 불가능하기 때문이라고 설명할 수는 없다**. 남은 주요 검수 방향은 PPO 모델 학습 품질, 토크 액추에이터, 폐루프 동역학·관측/보상 설계의 구분이다. 원본 PPO 성공률은 **여전히 0/10**이며 승격하지 않는다.

## 공개 CI 원본 증거

- PR: [#157](https://github.com/silverbjin/Pysical_AI_ROS2/pull/157)
- 실제 Actions [Run #43417674577](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43417674577): **SUCCESS**.
- 원본 [Artifact #14031729831](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43417674577/artifacts/14031729831): `receipt.json`, 10개 시드별 로그, `receipt_audit.log`, `checkout_sha.txt`, `pip_freeze.txt`.
- 테스트 소스 헤드 SHA `a9c322f08639424bd60b7b60cae76fe367e719bd`; 실제 PR CI synthetic checkout SHA `bf2e13894c641b7befc3563aa50c3de543b8b85b`.
- 최초 배포된 PPO ZIP SHA256 `78f85cc0d8cee868b66fe6b538fcf7b7a64b2d65632bd8036c01d8afeaceda92`, 원본 모델 XML SHA256 `ffa277c1eda287e76279153c5c48075c0f8f03676ff6cde4fa0e7802e84daa99`이며, 두 파일과 `rl_env.py`의 변경 없음이 실행 전후 검증됐다.
- Python 3.12, MuJoCo 3.3.7, Gymnasium 1.1.1, NumPy 2.2.6. ROS/Gazebo/GUI/torch/SB3 추론·학습은 재수행하지 않았다.
- 독립 영수증 감사 `CH08_87_INDEPENDENT_GEOMETRIC_TARGET_REACHABILITY_RECEIPT_PASS found=10/10`.

## 다음 조치 — 기존 성공 증거 보존

1. **동역학·제어 경계:** 목표 IK 솔루션이 있어도 원래 6개 토크 모터의 제어가 가능한지, 유한 토크에서 EE가 실제로 목표에 접근하는지 새로운 시드별 토크/관절 계측이 필요하다. 시험 전 임의로 성공 반경 0.05m나 평가 시간을 늘리지 않는다.
2. **PPO 학습 경계:** 기존 ZIP을 덮어쓰지 않고 버전·시드·데이터·reward 지표를 분리한 실험으로만 다시 학습한다. 학습 품질은 별도 동일한 10개 시드 + 홀드아웃 시드에 대해 실제 성공 횟수/거리로 판정한다.
3. RGB `RecordVideo` 문제는 별도 그래픽 환경/코덱 경계이며 모델 목표 도달성 PASS와 혼동하지 않는다.

**판정:** Ch08 §8.7 **목표 기구학적 접근성 수치 진단만 SCOPED PASS**. PPO 정책 성공률 0/10 **성능 미달 유지**, 물리 토크 제어·실기 안전·GUI NOT_RUN. Ch07 §7.2 RGB-D #127 BLOCKED, Ch10 #123 HOLD.
