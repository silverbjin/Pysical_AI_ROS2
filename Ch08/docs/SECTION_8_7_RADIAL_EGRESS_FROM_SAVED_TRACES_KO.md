# Ch08 §8.7 — 원본 동결 PPO의 최단 접근 이후 재이탈: 기존 실측 Artifact 재분석

> 분석일: 2026-11-14 KST. **새 PPO 모델/추론/학습 없음, Gazebo/MuJoCo 재실행 없음.** 이 문서는 기존 공개 CI가 저장한 실제 궤적 360스텝의 **독립 사후 산술 분석**이다. 원본 정책 목표 성공률 **0/10 PERFORMANCE_FAIL 유지**, Ch10 #123 HOLD.

## 증거 출처와 변조 방지

- [기존 실측 공개 CI #43426946500](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43426946500) **SUCCESS**, [원본 Artifact #14038346717](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43426946500/artifacts/14038346717) ZIP을 직접 다운로드하여 `trace_seed_1000.json` ~ `1002.json` 120스텝씩 총 360행을 다시 계산했다.
- 다운받은 ZIP SHA256: `5a8dd50d8b123e26253ba619622378849894731cd6033852dac2b4c5811f77b9`. 원본 CI synthetic checkout `ca7d5beab5112e2a72c4001861ae5405171928b7`.
- 기존 Receipt에 기록된 변경 불가 원본 자산: PPO ZIP `78f85cc0d8cee868b66fe6b538fcf7b7a64b2d65632bd8036c01d8afeaceda92`; MuJoCo XML `ffa277c1eda287e76279153c5c48075c0f8f03676ff6cde4fa0e7802e84daa99`; `rl_env.py` `c89a8bd1b2cac0ca230b98aa01f765a517af9e6ca6dff064a879531c9f83439f`. 어떤 파일도 덮어쓰거나 학습하지 않았다.
- 기존 [10×300스텝 최종 평가 #43361732383](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43361732383): PPO 진짜 목표 성공 **0/10**, 평균 최종 거리 0.432753m. 이 평가를 재실행하지 않았다.

## 정의 — 위치 벡터 대신 거리 변화율만 가능

`trace_seed_*.json`은 실제 `ReachEnv.step`의 `sim_time_sec`, `distance_m`, 실제 6개 관절속도와 행동을 기록한다. 목표와 EE의 XYZ 벡터를 매 단계 기록한 것은 아니므로, 아래 값은 **거리함수 r(t)의 유한차분 dr/dt**일 뿐, EE의 3D 목표상대 속도 벡터나 광학 유량이 아니다.

- `k_min = argmin(distance_m)`
- `pre_rate = (r[k_min]-r[0])/(t[k_min]-t[0])` (초기→최소 평균 방사 거리 변화율)
- `post_rate = (r[-1]-r[k_min])/(t[-1]-t[k_min])` (최소→종료 평균 방사 거리 변화율)
- `away_fraction = mean(diff(r[k_min:]) / diff(t[k_min:]) > 0)`; 매 스텝 거리 증가 비율이며 전체 구간이 단조롭게 멀어짐을 뜻하지 않는다.

| 원본 시드 | 최소거리 시점 (스텝/초) | 최소거리(m) | 최소→종료 거리 증가(m) | 접근 평균 dr/dt (m/s) | 이후 평균 dr/dt (m/s) | 이후 거리 증가 비율 |
|---|---|---:|---:|---:|---:|---:|
| 1000 | 34 / 0.34 | 0.355190 | **+0.404446** | −1.237686 | **+0.470286** | 56.98% |
| 1001 | 42 / 0.42 | 0.292691 | **+0.193633** | −1.325524 | **+0.248247** | 56.41% |
| 1002 | 100 / 1.00 | 0.198555 | +0.001560 | −0.738836 | +0.007799 | 60.00% |

**해석:** 세 시드 모두 초기에 목표까지 가까워졌지만, 최소거리 이후 평균 거리 변화율은 양수. 특히 1000, 1001은 각각 0.404m, 0.194m 다시 멀어졌다. 실제 목표 반경 0.05m에 들어간 적 없음. 일부 순간 거리 증가·감소가 반복되므로 직선으로 목표를 지나쳤다고 단정할 수 없고, '관절속도 과대' 혹은 'goal conditioning 결함' 하나로 원인을 확정할 수도 없다.

원본 관절속도 측정의 최소거리 이후 절대 최대는 시드별 약 **13.339 / 13.571 / 3.572 rad/s**. 이는 해당 원본 MuJoCo 수치 기록이지 실제 로봇 안전 허용 값이 아니다. 원본 action 포화율 0% 및 Goal을 변경한 한 상태에서 action 최대 L2 차이 0.124649 역시 기존 실측 사실로 유지한다.

## 재현 계산 — 원본 JSON만 사용

~~~python
import json, zipfile
import numpy as np
with zipfile.ZipFile("book_ch08_87_frozen_action_43426946500.zip") as z:
    for seed in (1000, 1001, 1002):
        rows = json.loads(z.read(f"trace_seed_{seed}.json"))
        t = np.array([r["sim_time_sec"] for r in rows], dtype=float)
        d = np.array([r["distance_m"] for r in rows], dtype=float)
        k = int(np.argmin(d))
        assert len(rows) == 120 and np.all(np.diff(t) > 0)
        pre = (d[k] - d[0]) / (t[k] - t[0])
        post = (d[-1] - d[k]) / (t[-1] - t[k])
        away = np.mean(np.diff(d[k:]) / np.diff(t[k:]) > 0)
        print(seed, k + 1, pre, post, away)
~~~

## 미완료의 실제 경계와 다음 최소 시험

1. **NOT_RUN:** 원본 환경의 EE 실제 3D 위치/속도 벡터, 목표 방향 투영 속도, 최소거리 전후 제어 명령 방향·중력보상과의 관계. 이번 리시트의 `distance_m`만으로 3D 방향/축을 복원할 수 없다.
2. **NOT_RUN:** 장기 정책 개선/재학습 및 독립 홀드아웃 10+ 시드 평가. 원본 PPO 정책의 **0/10 성능 FAIL**과 구분한다.
3. 다음 1회 좁은 시험이 꼭 필요하면, 원래 환경 코드와 PPO ZIP은 그대로 두고 **새 test-only 계측기**에서 원본 동일 시드 단기 rollout의 각 스텝 EE XYZ/target XYZ를 추가 기록하여 `(target-ee)·v_ee / norm(target-ee)`와 수치 `dr/dt`의 부호를 비교한다. 한정된 3시드/120스텝 이상 반복하지 않는다. 새로운 CI/Artifact 전까지 **vector velocity = NOT_RUN**.

**현재 판정:** `EXISTING_ARTIFACT_OFFLINE_ANALYSIS` 완료. 이는 검증된 원본 MuJoCo 로그의 해석이지 별도 실행의 새로운 PASS가 아니며, 교재 원본 RL 성능은 FAIL이다. Ch07 RGB/Depth 별도 scoped PASS와 독립, Ch10 HOLD.
