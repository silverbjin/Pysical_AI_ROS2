# LAB 8.6 — PPO 스모크 학습, 저장, 추론

**목표:** 짧은 PPO 학습이 실제로 gradient update를 수행하고 모델을 저장/읽을 수 있는지 확인한다. **짧은 학습=학습 파이프라인 검증이지 목표 도달 성능 증명이 아니다.**

## 준비(ROS 2 불필요)
```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install mujoco numpy gymnasium "stable-baselines3[extra]" tensorboard
python - <<'PY'
import mujoco, gymnasium, stable_baselines3, torch
print("mujoco",mujoco.__version__,"gymnasium",gymnasium.__version__,
      "sb3",stable_baselines3.__version__,"torch",torch.__version__)
PY
```

## 1. 환경 사전 점검
```bash
python - <<'PY'
from rl_env import ReachEnv
from stable_baselines3.common.env_checker import check_env
env=ReachEnv(render_mode=None)
try:
    check_env(env,warn=True)
    print("obs",env.observation_space.shape,"action",env.action_space.shape)
finally: env.close()
PY
```
현재 소스는 **18관측/6행동**이다. 초판 원고의 12/3과 혼합 금지.

## 2. 안전한 임시 폴더에서 소량 학습
아래 코드는 기존 `train_reach.py`를 수정하거나 `models/ppo_reach_final.zip`을 덮어쓰지 않는다.

```bash
python - <<'PY'
from pathlib import Path
from uuid import uuid4
from stable_baselines3 import PPO
from stable_baselines3.common.monitor import Monitor
from gymnasium.wrappers import TimeLimit
from rl_env import ReachEnv
out=Path("smoke_runs")/("ppo-"+uuid4().hex[:8])
out.mkdir(parents=True,exist_ok=False)
env=Monitor(TimeLimit(ReachEnv(render_mode=None),max_episode_steps=300))
try:
    model=PPO("MlpPolicy",env,verbose=1,device="cpu",
              n_steps=64,batch_size=64,n_epochs=2,seed=42)
    model.learn(total_timesteps=256)
    target=out/"smoke_model"
    model.save(str(target))
    reloaded=PPO.load(str(target)+".zip",env=env)
    obs,_=env.reset()
    action,_=reloaded.predict(obs,deterministic=True)
    print("model",target.with_suffix(".zip"),"observation",obs.shape,"action",action.shape)
    assert action.shape==(6,)
finally:
    env.close()
PY
```

## 3. 전체 학습(선택, 별도 실행)
현재 `python train_reach.py`를 실행하면 **2,000,000 timesteps**가 시작된다. 먼저 2번 smoke가 성공하고 저장 공간·CPU 시간을 확보한 경우에만 진행한다. 동일한 `logs/`·`models/`에 출력하므로 기존 실험을 백업하고 덮어쓰기 위험을 확인한다. 원고의 100만 스텝과 다르며 도달률 보장은 없다.

```bash
# 위 조건 충족 후에만 별도로 실행
python train_reach.py
```

## 4. 추론과 평가
```bash
# 뷰어가 가능한 WSLg/Ubuntu GUI에서만
python test_model.py
# headless 평가(현재 코드의 SSE=0.0은 distance 누락 시 무효)
python evaluate_robot.py
```

## 5. 관찰 질문·합격 기준
- `rollout`, `train` 지표가 생성되는가? PPO 학습 전후 정책의 성능 변화는 아직 결론내리지 않는다.
- `TimeLimit`이 없는 원래 코드에서 `truncated`가 항상 False인 이유는?
- `seed`와 모델/환경 manifest를 저장하지 않으면 재현성에 어떤 문제가 생기는가?
- smoke 모델이 6행동을 출력하는지 확인한다. 3DOF 환경에는 **사용하지 않는다**.
- 제출: 패키지 버전, 종료 코드, 출력 모델 경로, 모델 해시, 5개 반환값, 개선 제안 2개. 실패는 그대로 기록.

[리뷰 보고서](SECTION_8_6_REPORT_KO.md)
