# 12장: 강화학습 기반 4족 보행

- [12.1 실습 가이드](docs/LAB_12_1_GUIDE_KO.md) · [보고서](docs/CHANGE_REPORT_KO.md)
- [12.2 실습 가이드](docs/LAB_12_2_GUIDE_KO.md) · [보고서](docs/SECTION_12_2_REPORT_KO.md)
- [12.3 실습 가이드](docs/LAB_12_3_GUIDE_KO.md) · [보고서](docs/SECTION_12_3_REPORT_KO.md)
- [12.4 PPO 실습 가이드](docs/LAB_12_4_GUIDE_KO.md) · [보고서](docs/SECTION_12_4_REPORT_KO.md)
- [12.5 목표 이동 실습 가이드](docs/LAB_12_5_GUIDE_KO.md) · [보고서](docs/SECTION_12_5_REPORT_KO.md)
- [12.6 장애물 회피 실습 가이드](docs/LAB_12_6_GUIDE_KO.md) · [보고서](docs/SECTION_12_6_REPORT_KO.md)
- [12.7 강건성·병렬 처리 가이드](docs/LAB_12_7_GUIDE_KO.md) · [보고서](docs/SECTION_12_7_REPORT_KO.md)
- [12.8 ROS 2 통합 실습 가이드](docs/LAB_12_8_GUIDE_KO.md) · [보고서](docs/SECTION_12_8_REPORT_KO.md)


리포지토리 루트에서 Ubuntu/WSL 가상환경을 활성화하고 실행한다.

```bash
python -m pip install -e './Ch12[test,visual]'
quadruped-rl --section 12.3 --policy stand --command 0 0 0 --steps 1000
quadruped-rl --section 12.2 --policy random --render --steps 1000
quadruped-rl --policy random --observation-mode full --steps 1000
MUJOCO_GL=egl CH12_TEST_RENDER=1 python -m pytest Ch12
```

12.1은 30차원(또는 45차원)·100Hz·토크 제어, 12.2는 31차원·50Hz·위치 제어,
12.3은 48차원·몸체 좌표계 속도 명령·50Hz·위치 잔차 제어를 기본으로 한다.
`from quadruped_env import QuadrupedEnv`는 12.2 호환 환경이다.
MuJoCo 실습은 ROS 없이 실행할 수 있다. Gazebo 비교 검증은 가상환경을 비활성화한
새 Ubuntu/WSL 터미널에서 `bash Ch12/scripts/verify_gazebo.sh`로 수행한다.

12.4·12.5 학습 도구는 선택 의존성을 설치한 뒤 실행한다.

```bash
python -m pip install -e './Ch12[test,visual,train]'
quadruped-train --task goal --env-config Ch12/config/section12_5_goal.json \
  --output Ch12/runs/goal-smoke --total-timesteps 512 --n-envs 2 \
  --n-steps 64 --batch-size 64 --n-epochs 2 --eval-every 256 --eval-episodes 2
quadruped-play --output Ch12/runs/goal-smoke --expected-task goal --render --steps 200
quadruped-goal --policy stand --target 2 1 --render --steps 200
```

짧은 학습은 실행 경로 확인용이다. 안정적 보행·목표 도착 능력은 검증하지 않았다.
새 goal 환경도 48차원이지만 속도 명령 환경과 의미가 달라 정책 파일을 혼용할 수 없다.
