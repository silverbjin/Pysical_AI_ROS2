# LAB 8.3 — MuJoCoArmEnv의 Gymnasium 5-반환값 검사

**학습 목표:** Box 공간, 환경 초기화, `step` 호출, 종료 조건을 측정 가능한 테스트로 익힌다. 주 대상은 3DOF `my_robot_env.py`다. 6DOF `rl_env.py`와 정책 파일은 여기서 사용하지 않는다.

## 준비
```bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
python3 -m venv .venv
source .venv/bin/activate
python -m pip install mujoco gymnasium numpy "stable-baselines3"
```

## 시연: 랜덤 에이전트
GUI가 가능할 때만 다음을 실행한다.
```bash
python test_env.py
```
화면에는 3자유도 로봇이 움직이고 터미널에는 보상과 거리가 출력되도록 작성돼 있다. GUI 없는 서버는 다음 headless 테스트로 대체한다.

## 따라하기: 입출력 계약
```bash
python - <<'PY'
import numpy as np
from stable_baselines3.common.env_checker import check_env
from my_robot_env import MuJoCoArmEnv
env=MuJoCoArmEnv(render_mode=None)
try:
    print("action", env.action_space, "observation", env.observation_space)
    obs,info=env.reset(seed=42)
    assert obs.shape==(12,) and obs.dtype==np.float32
    assert np.isfinite(obs).all()
    a=np.zeros(3,dtype=np.float32)
    next_obs,r,term,trunc,info=env.step(a)
    print("reward",r,"terminated",term,"truncated",trunc,"distance",info["distance"])
    assert next_obs.shape==(12,) and np.isfinite(r)
    check_env(env,warn=True)
    print("API check completed (성능 증명은 아님)")
finally:
    env.close()
PY
```

## 탐구: 시드 재현성, 액추에이터 스케일
```bash
python - <<'PY'
import numpy as np
from my_robot_env import MuJoCoArmEnv
env=MuJoCoArmEnv()
try:
    a,_=env.reset(seed=123)
    b,_=env.reset(seed=123)
    print("target A",a[6:9],"target B",b[6:9],"same",np.array_equal(a[6:9],b[6:9]))
    print("ctrlrange",env.model.actuator_ctrlrange,"gear",env.model.actuator_gear[:,0])
    print("current source scales action by 50 additionally")
finally:
    env.close()
PY
```

**해석:** 같은 `seed`라면 일치해야 하는 것이 목표지만 현 소스는 전역 NumPy RNG를 사용하므로 재현성 실패가 예상된다. action을 50배 확대하는 것은 XML의 gear 지정과 구별하여 분석한다. 사용 중인 MuJoCo의 제어 클램프 여부도 확인한다.

## 원리·응용 과제
1. 12차원 관측에서 `qpos`, `qvel`, `target`, `rel_vec` 각 인덱스를 적는다.
2. `terminated`와 `truncated`를 별개로 반환해야 하는 이유, `TimeLimit( ..., max_episode_steps=300)`를 붙였을 때의 변화를 설명한다.
3. 3DOF `link_ee`와 6DOF `ee_site`가 같은 환경이 아님을 설명한다.
4. 작은 `-distance`가 반드시 성공률 향상을 뜻하지 않는 이유를 기술한다.

## 문제 해결과 통과 판정
- 파일 경로 오류 → `pwd`가 `Ch08/ros2_ws`인지 확인.
- 화면 오류 → headless 테스트 우선.
- assertion 실패 → traceback, `python --version`, 설치 버전, XML 파일명을 기록한다.
- **통과:** 환경 생성/5개 반환값/유한 관측 3항목을 로그로 확인. 시드/제어 계약 결함은 숨기지 않고 리뷰 보고서의 개선 대상으로 남긴다.

[리뷰 보고서](SECTION_8_3_REPORT_KO.md)
