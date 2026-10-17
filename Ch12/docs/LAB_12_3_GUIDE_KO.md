# 12.3절: 상태·행동·보상 실습

Ubuntu 24.04 / Python 3.12에서 리포지토리 루트 기준으로 실행한다.

```bash
source .venv/bin/activate
python -m pip install -e './Ch12[test,visual]'
quadruped-rl --section 12.3 --policy stand --command 0 0 0 --steps 1000
quadruped-rl --section 12.3 --policy random --command .5 .2 .3 --steps 1000
quadruped-rl --section 12.3 --policy stand --render --command 0 0 0
quadruped-rl --section 12.3 --reward-config Ch12/config/section12_3_reward.json --action-scale .5
MUJOCO_GL=egl CH12_TEST_RENDER=1 python -m pytest Ch12
```

관측은 48차원이다. 몸체 선속도(3), 몸체 각속도(3), 몸체 좌표계 단위 중력(3), 명령 vx/vy/yaw rate(3), 명목 자세 대비 관절각(12), 관절속도(12), 직전 적용 행동(12) 순이다. 초안의 45차원 표는 명령 3개를 빠뜨렸다. 직립 시 중력은 [0,0,-1]이다. 선속도 명령은 m/s, 회전속도는 rad/s이며 각 성분은 [-3,3]이다.

```python
import numpy as np
from quadruped_rl import QuadrupedLocomotionEnv
with QuadrupedLocomotionEnv(command=[0,0,0]) as env:
    obs, info = env.reset(seed=42)
    obs, reward, terminated, truncated, info = env.step(np.zeros(12))
    print(info['reward_terms'], info['reward_raw'])
```

정규화 행동은 명목 자세 + 0.35 × 행동(rad)으로 변환한 뒤 관절 한계로 제한한다. PD 모터의 실제 토크 한계도 적용된다. `--control-mode torque`로 직접 토크 제어와 비교할 수 있다. `last_action`은 직전 적용 행동의 복사본이며 보상 계산 후 현재 행동으로 갱신된다.

선속도·회전·자세 보상은 exp(-제곱오차/sigma)이다. 실제 actuator 토크 제곱합, 행동 차 제곱합, 발 이외 지면 접촉 링크 수를 감점한다. 지속 항목에는 제어 주기 dt=0.02를 곱하고 낙상은 일회 -10이다. 토크 제곱합은 에너지 소비 자체와는 다르다. `reward_terms`는 가중 기여도이며 합이 반환 보상과 일치한다.

높이 ≤0.2m, 몸체 수직축의 총 기울기 ≥45도, 몸통 지면 접촉은 terminated다. 1,000스텝/20초는 truncated이며 보행 성공을 뜻하지 않는다. 어느 종료든 reset해야 한다. 낙상 순간에는 양의 추종·자세 보상을 주지 않는다. 물리 하위 스텝의 낙상·비발 접촉도 기록한다.

고정 명령, `reset(options={'command':[0,0,0]})`, `set_command(...)`, `command_ranges=[[-.5,.5],[-.2,.2],[-.3,.3]]`를 사용할 수 있다. 동일 reset 시드는 동일 초기 상태와 명령을 만든다. 다음 reset은 기본 명령 또는 명령 범위로 돌아간다.

이 절의 stand는 PD 기준 자세 유지이고 random은 무작위 행동이다. 아직 학습한 보행 정책은 아니다. 움직이지 않는 기준 자세에서 이동 명령의 추종 보상이 낮아지는 것을 먼저 확인한 뒤 다음 절에서 PPO를 연결한다.
