# LAB 8.4 — 6자유도 ReachEnv 관측·물리계약 검증

**목적:** 원고의 3DOF 설계를 출발점으로 삼되, GitHub `main`의 **현재 실제 구현은 6DOF**라는 점을 눈으로 확인한다. 교육 활동: 모델 관찰 → 계약 비교 → Gymnasium 테스트 → 평가.

## 준비
```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
python3 -m venv .venv
source .venv/bin/activate
python -m pip install mujoco gymnasium numpy stable-baselines3
```
헤드리스 검사에는 ROS 2가 필요하지 않다. Viewer 실습은 Ubuntu GUI/WSLg 필요.

## 실습 A — 모델과 관측 차원 검사
```bash
python - <<'PY'
import numpy as np
from rl_env import ReachEnv
env=ReachEnv(render_mode=None)
try:
    m=env.model
    print("nq/nv/nu",m.nq,m.nv,m.nu,"observation",env.observation_space.shape,
          "action",env.action_space.shape)
    print("physical_dt",m.opt.timestep, "control_dt",m.opt.timestep*5,
          "control_Hz",1/(m.opt.timestep*5))
    a,_=env.reset(seed=42)
    print("EE",a[12:15],"target",a[15:18])
    assert a.shape==(18,)
    assert env.action_space.shape==(6,)
    assert m.nmocap>=1
    assert np.isfinite(a).all()
finally: env.close()
PY
```
**정답 포인트:** 관측의 `[6:9]`는 목표가 아니라 관절 속도의 일부다. 파일별 계약을 적고 원고의 12차원과 비교한다.

## 실습 B — 랜덤 동작 시뮬레이션
```bash
python - <<'PY'
import numpy as np
from rl_env import ReachEnv
env=ReachEnv(render_mode=None)
try:
    obs,_=env.reset(seed=7)
    for i in range(30):
        obs,reward,terminated,truncated,info=env.step(env.action_space.sample())
        assert obs.shape==(18,) and np.isfinite(obs).all()
        assert np.isfinite(float(reward))
        assert isinstance(terminated,bool)
        if i%10==0: print(i, "reward",reward,"success",info["is_success"])
        if terminated or truncated: obs,_=env.reset(seed=i)
finally: env.close()
PY
```

## 실습 C — GUI 시연(선택)
```bash
python test_reach_env.py
```
현재 스크립트의 `Target Pos: obs[6:9]` 출력은 목표 좌표가 아니므로 **결과를 그대로 신뢰하지 않는다.** 화면의 빨간 모캡 목표와 EE 위치를 구분해 관찰한다. 시연 `sleep(.05)`는 실제 제어주기와 같지 않다.

## 심화·분석 과제
1. `env.model.opt.timestep*5`를 직접 계산하여 100Hz를 설명한다.
2. `env.data.site("ee_site").xpos`와 `env.data.mocap_pos[0]`으로 거리를 별도 계산하고 성공 조건 0.05m를 확인한다.
3. 300 스텝 제한을 Gymnasium `TimeLimit`으로 적용하여 `truncated`에 반영하는 설계안을 제안한다.
4. `mj_resetData` 도입 시 기존 `mocap_pos`, `last_action`, `qpos/qvel` 초기화 순서를 설명한다.

## 성공·오류 기준
- 6DOF/18D/6-action/100Hz 확인과 finite 관측 30회면 API 스모크 통과.
- `AttributeError`, XML 컴파일 오류, 관측 차이 등은 그대로 로그 보존.
- 랜덤 행동으로 목표를 달성할 필요는 없다. **학습 성공 여부는 별도로 증명해야 한다.**

[코드 리뷰](SECTION_8_4_REPORT_KO.md)
