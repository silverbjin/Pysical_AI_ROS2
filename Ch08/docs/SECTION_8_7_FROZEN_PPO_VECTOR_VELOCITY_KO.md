# Ch08 §8.7 — 동결 PPO의 3D 목표방향 속도 실측 및 재이탈 진단

> 2026-11-14 KST, **실제 MuJoCo 2개 시드의 좁은 벡터 계측 SCOPED PASS**. 기존 동결 PPO 정책의 성공률은 여전히 **0/10 PERFORMANCE FAIL**. PPO 학습·모델 교체 없음. Ch10 #123 HOLD.

## 검증 목적

[기존 PPO 평가 #43361732383](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43361732383)는 10개 시드×최대 300스텝에서 **0/10 목표 성공**, 평균 최종 거리 0.432753m였다. [기존 단기 행위 진단 #43426946500](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43426946500)은 Distance 변화만 저장했고, [기존 오프라인 재분석 PR #164](https://github.com/silverbjin/Pysical_AI_ROS2/pull/164)는 접근 후 재이탈 사실을 확인했다. **그 정보만으로 3D EE 속도를 확정하지 못했다.**

이번에는 원본 동결 ZIP·원본 `ReachEnv.step`에서 새로 **seed=1000,1001 각각 120 스텝**을 실행하여 실제 EE와 목표 XYZ를 관측한다. 종전 10×300 전체 평가 및 이전 3×120 action/reward 검사 자체는 다시 실행하지 않고, 3D 벡터를 얻는 두 시드로 범위를 축소한다.

## 측정 및 수식

- 매 스텝 세계 좌표 말단 `EE_t = obs[12:15]`, 타깃 `G_t = obs[15:18]`, 실제 `data.time`, 실제 6개 행동을 저장한다.
- 유한차분 속도: `v_t = (EE_t - EE_(t-1)) / Δt` (m/s)
- **목표방향 속도**: `v_goal,t = v_t · ((G - EE_(t-1)) / ||G - EE_(t-1)||)`.
- 양수면 그 순간 목표 방향으로 이동, 음수면 목표 반대 방향 성분이 더 큼. 매 스텝 거리 변화율 `Δ||G-EE||/Δt`도 독립 기록하여 산술적으로 대조한다.
- 이전에 이미 기록된 최소거리 스텝 전과 후를 분리한다. **평균 속도가 음수라도 모든 순간에 멀어졌다는 뜻은 아니다.**

| 원본 PPO 시드 | 최소거리 스텝 | 최소거리(m) | 최소 전 평균 목표방향 속도(m/s) | 최소 후 평균 목표방향 속도(m/s) | 최소 이후 거리 증가(m) | 이후 목표에서 멀어진 스텝 비율 |
|---|---:|---:|---:|---:|---:|---:|
| 1000 | 34 | 0.355190 | **+1.214867** | **−0.431889** | 0.404446 | 56.98% |
| 1001 | 42 | 0.292691 | **+1.317032** | **−0.161559** | 0.193633 | 52.56% |

두 시드 모두 최소거리까지 접근한 뒤 실제 목표방향 속도 평균이 음수로 역전되었다. 하지만 0.05m 목표 반경에는 한 번도 진입하지 못했다. 이는 **관측된 재이탈의 기구학적 원인 경계**이며, PPO 보상함수 문제·모터 이득·관절 관성·goal conditioning 중 무엇이 주원인인지는 아직 증명하지 않는다.

## 실제 CI·증거

- 소스 HEAD `315aa670425291e325d4930f31891dfb597df861`; Actions synthetic checkout `955573a5ec215670e16665419a9e4bb0e0745aed`.
- [공개 CI #43475456577](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43475456577) **SUCCESS**, [원본 Artifact #14062646338](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43475456577/artifacts/14062646338) ZIP SHA256 `f55001b50785701009db1405c67f567372f1a2207b1e6880f921f002d2e0ac83` (GitHub 업로드 로그 동일). 총 8파일 직접 다운로드·검토, `vector_trace_seed_1000.json`, `vector_trace_seed_1001.json`, `receipt.json`, `independent_audit.log`.
- 실제 `CH08_168_REAL_FROZEN_PPO_EE_VECTOR_MEASUREMENT_SCOPED_PASS`; 독립 감사 `CH08_168_INDEPENDENT_EE_TARGET_VECTOR_PROJECTION_RECEIPT_PASS seeds=2 max_steps_each=120` 기록.
- 동결 PPO ZIP SHA256 `78f85cc0d8cee868b66fe6b538fcf7b7a64b2d65632bd8036c01d8afeaceda92`, XML `ffa277c1eda287e76279153c5c48075c0f8f03676ff6cde4fa0e7802e84daa99`, 원본 환경 `rl_env.py` `c89a8bd1b2cac0ca230b98aa01f765a517af9e6ca6dff064a879531c9f83439f` 불변. CPU torch 2.5.1/MuJoCo 3.3.7/SB3 2.6.0 기존 의존성 버전 재사용.
- 별개 `ci/ch08_168_audit_vector_receipt.py`가 원본 센서/환경을 다시 실행하지 않고 JSON과 SHA에서 속도·목표방향 투영·거리 일치 및 원본 성공반경 미달을 재계산한다.

## 실습 재현 및 다음 결정

- 전용 워크플로 `.github/workflows/book-ch08-168-vector-projection.yml`과 실행기 `ci/ch08_168_frozen_ppo_vector_once.py`를 사용한다. 원본 10×300 반복이나 학습 명령 없음.
- **새 모델 학습은 아직 시작하지 않는다.** 다음 필요 범위는 저장된 행동 방향과 동역학 편향(중력/가속도), 타깃 근접 후 Feedback 반응을 각각 하나씩 반사실적 테스트로 분리하고, 가장 작은 모델/제어 수정 후 독립 holdout 시드에서 정책 자체의 **실제 0.05m 목표 성공**으로 평가하는 것.
- **NOT_RUN:** 새로운 PPO 학습 결과, 일반화된 성공률, 장기간 안정 제어, 실제 하드웨어, GUI, 실물 안전성.
- 기존 PPO **0/10 PERFORMANCE FAIL**은 유지하고, 이번의 **측정 무결성 SCOPED PASS를 정책 성공으로 승격하지 않는다.** Ch10 HOLD.
