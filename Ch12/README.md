# 12장: 강화학습 기반 4족 보행

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
