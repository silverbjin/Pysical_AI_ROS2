# 12장: 강화학습 기반 4족 보행

## 12.2절: 학습 환경 구축

[12.2절 실습 가이드](docs/LAB_12_2_GUIDE_KO.md)와
[수정·검증 보고서](docs/SECTION_12_2_REPORT_KO.md)를 제공한다.

```bash
python -m pip install -e './Ch12[test,visual]'
quadruped-rl --section 12.2 --policy random --steps 1000
quadruped-rl --section 12.2 --policy stand --render --target-velocity 0
python Ch12/examples/12_2_random_motion.py --render --steps 1000
```

12.2절 기본은 31차원 쿼터니언 관측·50 Hz·위치 제어다.
`--control-mode torque`로 토크 제어를 비교한다.
본문의 `from quadruped_env import QuadrupedEnv`도 지원한다.

## 12.1절: 상태·행동·보상 입문

[12.1절 실습 가이드](docs/LAB_12_1_GUIDE_KO.md)에서 설치·실행·관측 및 보상 해석을 시작한다.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e './Ch12[test,visual]'
quadruped-rl --policy random --steps 1000 --observation-mode full
python -m pytest Ch12
```

실행 위치는 리포지토리 루트다. MuJoCo 실습은 ROS 없이 실행할 수 있다.
Gazebo 비교 검증은 가상환경을 비활성화한 새 Ubuntu/WSL 터미널에서
`bash Ch12/scripts/verify_gazebo.sh`로 수행한다.

[수정·검증 보고서](docs/CHANGE_REPORT_KO.md)와 [설계](docs/DESIGN_KO.md),
[구현 계획](docs/IMPLEMENTATION_PLAN_KO.md)을 함께 제공한다.
