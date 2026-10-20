# LAB 8.5 — 보상 구성 요소 분해 및 경계 테스트

**학습 목표:** '밀집 거리 보상 + 행동 비용 + 변화량 비용 + 성공 보너스'를 숫자로 분석한다. 실행 대상은 원고의 `compute_reward`가 아닌 저장소 `ReachEnv.calculate_reward`다.

## 사전 준비
```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
source .venv/bin/activate  # 없는 경우 LAB_8_4_GUIDE_KO.md에서 venv 준비
python -m pip install mujoco gymnasium numpy
```

## 시연: 한 스텝의 보상 항 확인
```bash
python - <<'PY'
import numpy as np
from rl_env import ReachEnv
env=ReachEnv(render_mode=None)
try:
    obs,_=env.reset(seed=10)
    action=np.zeros(env.action_space.shape, dtype=np.float32)
    _,total,term,trunc,detail=env.step(action)
    print("total",total,"terminated",term)
    for k,v in detail.items(): print(k,v)
    total_parts=sum(detail[k] for k in
        ["reward_dist","reward_ctrl","reward_smooth","reward_contact","reward_bonus"])
    assert np.isclose(total, total_parts)
finally: env.close()
PY
```

## 따라하기: 성공 반경 경계
```bash
python - <<'PY'
import numpy as np
from rl_env import ReachEnv
env=ReachEnv()
try:
    env.reset(seed=1)
    action=np.zeros(env.model.nu,dtype=np.float32)
    env.last_action=action.copy()
    for distance in (0.049,0.050,0.051):
        total, info=env.calculate_reward(
            np.array([0.,0.,0.]),
            np.array([distance,0.,0.]),action)
        print(distance, "success",bool(info["is_success"]),
              "bonus",info["reward_bonus"],"reward",round(float(total),4))
finally: env.close()
PY
```
**예상 해석:** `distance < 0.05`가 조건이므로 정확히 0.050은 성공이 아니다. `data.ncon`은 테스트 상태의 접촉 개수에 따라 0 또는 다른 값일 수 있다.

## 원리 확인·확장 실험
1. `r_ctrl` 가중치가 .01에서 .1로 커지면 큰 action의 불이익이 어떻게 바뀌는가? (코드 수정 전 수식으로 예측)
2. `last_action = -ones(6)`, `action=ones(6)`인 상황의 `r_smooth` 값을 계산한다.
3. `env.step`의 `info.keys()`에서 `distance` 부재를 확인한다. 이 상태로 `evaluate_robot.py`가 출력하는 정착 오차 `0.0`을 성능 증거로 삼아서는 안 된다.
4. 보상이 커져도 실제 도달률이 낮을 수 있는 이유(목표 분포/탐색/성공 보너스)를 논의한다.

## 산출물과 평가
보상 계산 표(거리·제어·변화량·접촉·보너스·총합), 거리 경계 시험 로그, 오류·개선 아이디어를 제출한다. 숫자 비교 시 시드, MuJoCo 버전, XML 모델명을 함께 기록한다. 이 문서 작성 과정은 실기 실행을 수행하지 않았으므로 실제 성공률·수렴을 주장하지 않는다.

[리뷰 보고서](SECTION_8_5_REPORT_KO.md)
