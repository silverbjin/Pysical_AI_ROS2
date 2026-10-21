# 12.4절: PPO 학습·평가·재생

Ubuntu 24.04/WSL, Python 3.12에서 리포지토리 루트 기준으로 실행한다. MuJoCo는 ROS 없이 동작한다. CPU MLP 학습을 기본으로 하며, GPU가 반드시 더 빠른 것은 아니다.

## 설치와 짧은 동작 확인

```bash
python3 -m venv .venv
source .venv/bin/activate
# CPU 전용 설치를 원할 때 먼저 공식 CPU wheel을 선택한다.
python -m pip install torch==2.5.1 --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e './Ch12[test,visual,train]'
quadruped-train --output Ch12/runs/ppo-smoke --total-timesteps 512 \
  --n-envs 2 --n-steps 64 --batch-size 64 --n-epochs 2 \
  --eval-every 256 --eval-episodes 2 --checkpoint-every 256
quadruped-play --output Ch12/runs/ppo-smoke --steps 200
quadruped-play --output Ch12/runs/ppo-smoke --render --steps 1000
```

각 학습은 새로운 output 폴더를 요구한다. 기존 실험을 덮어쓰지 않도록 다른 이름을 지정한다. 예제 파일 `python Ch12/examples/train_ppo.py ...`, `python Ch12/examples/play.py ...`도 동일한 인자를 받는다. 그래픽 없는 서버에서는 render를 생략하거나 `MUJOCO_GL=egl`과 `--frame-path frame.png`를 사용한다. human viewer에는 WSLg/X 디스플레이가 필요하다.

## 본 학습

```bash
quadruped-train --output Ch12/runs/ppo-2m --total-timesteps 2000000 \
  --n-envs 8 --backend subproc --device cpu
tensorboard --logdir Ch12/runs/ppo-2m/tensorboard
quadruped-play --output Ch12/runs/ppo-2m --render --steps 5000
```

`dummy`는 한 프로세스에서 여러 환경을 순차 실행한다. `subproc`는 spawn으로 별도 프로세스를 만든다. 환경 수만큼 속도가 증가하지는 않으므로 1/2/4/8개를 실제 장비에서 비교한다. 학습 스크립트를 직접 만들면 반드시 `if __name__ == '__main__':` 안에서 호출한다. 학습 환경에서는 창을 열지 않는다.

기본 PPO는 actor/critic 각각 256×256, Tanh, learning_rate=3e-4, n_steps=2048, batch_size=256, n_epochs=10, gamma=.99, GAE=.95, clip=.2, entropy=.005다. 관측은 12.3절의 48차원, 행동은 12개 위치 잔차다. 관측은 원시 단위를 사용하며 VecNormalize를 적용하지 않는다. 따라서 별도 정규화 통계가 누락되는 문제는 없지만 고속 명령 등 관측 범위가 크게 변하면 별도 스케일 튜닝이 필요할 수 있다.

PPO는 n_steps × n_envs 단위로 rollout을 수집하므로 요청 스텝 수보다 많이 진행될 수 있다. batch_size는 이 rollout 크기의 약수여야 한다. 평가와 checkpoint 간격은 **총 전이 수**이며 내부 callback 빈도는 max(간격 // n_envs, 1)이다. 배수가 아니면 가까운 작은 간격으로 맞춘다. 별도 시드의 Monitor 환경에서 deterministic 평가를 수행하며 학습 종료 후 최종 업데이트도 평가한다.

## 결과 파일과 모니터링

- `manifest.json`: 과제, 관측 규격, 환경·학습 설정, 실제 라이브러리 버전.
- `final_model.zip`: 마지막 업데이트. `best_model/best_model.zip`: 주기 평가와 최종 평가 중 최고 모델.
- `checkpoints/*.zip`: 중간 저장. `--model-name checkpoints/파일명.zip`으로 재생한다.
- `evaluation/evaluations.npz`, `monitor/*.monitor.csv`, `tensorboard/`: 평가·에피소드·학습 기록.
- `result.json`: 실제 학습 전이 수, 파라미터 변화량, 최종·최고 평가 점수.

`--env-config JSON파일`로 환경 옵션을 지정하면 manifest에 함께 저장한다. 재생은 그 환경을 복원하고 ZIP 내부의 과제·환경 설정을 manifest와 대조한다. 다른 과제나 설정의 모델을 섞으면 거부한다. 학습 Ctrl+C 시 `interrupted_model.zip`을 저장하고 환경을 닫는다. 재생은 terminated와 truncated 모두 처리하며 Ctrl+C/창 닫기로 종료할 수 있다.

TensorBoard에서 rollout/ep_rew_mean, train/value_loss, train/entropy_loss, eval/mean_reward를 함께 본다. 엔트로피 손실은 부호를 포함한 지표이므로 반드시 0으로 수렴해야 하는 것은 아니다. 보상 곡선이 평평하다는 사실만으로 원인을 단정할 수 없다. 평가·영상·낙상·명령 추종을 함께 확인한다.

PPO clipping은 정책 전체 변화가 20% 이하라는 보장이 아니다. 200만 스텝이나 특정 진행률에서 보행이 완성된다는 보장도 없다. 이 패키지의 짧은 검증은 실제 gradient update와 저장·추론 경로를 확인한다. 안정적인 전진 보행은 장시간 다중 시드 학습과 별도 성능 평가가 필요하다.

참고: [SB3 PPO](https://stable-baselines3.readthedocs.io/en/v2.7.1/modules/ppo.html), [평가 callback](https://stable-baselines3.readthedocs.io/en/v2.7.1/guide/callbacks.html), [평가 지침](https://stable-baselines3.readthedocs.io/en/v2.7.0/guide/rl_tips.html).

## 검증 재실행

검증 출력도 새 폴더를 사용한다. PPO 검증은 두 과제와 실제 subprocess 학습, 저장·로드, RGB, TensorBoard 이벤트를 확인한다.

```bash
MUJOCO_GL=egl CH12_TEST_RENDER=1 python -m pytest Ch12 -q
MUJOCO_GL=egl python Ch12/scripts/verify_ppo.py --output Ch12/runs/verify-ppo
python Ch12/scripts/verify_training_interrupt.py --output Ch12/runs/verify-interrupt
```

장시간 학습 결과 모델과 혼동하지 않도록 smoke 모델 ZIP은 Git 이력에 포함하지 않는다. 검증용 모델이 제공된 경우에도 학습된 보행·목표 이동 성능을 보장하는 모델은 아니다.


---

## 원고 연계 실습 보강 (2026-10-21 리뷰)

**학습 도달점:** PPO 학습·평가·체크포인트. 예제 코드의 목적과 실제 패키지의 제어·관측 계약을 구분하고, 재현 가능한 증거를 제출한다. 실행 위치는 `Pysical_AI_ROS2/` 저장소 루트다(기존 가이드가 별도 경로를 지정한 경우 그 지시를 우선한다).

### 따라하기: 최소 검증 루트

```bash
python -m pip install -e './Ch12[test,visual,train]'
python -m pytest Ch12/tests/test_ppo.py -q
quadruped-train --output Ch12/runs/review-12-4 --total-timesteps 512 --n-envs 2 --n-steps 64 --batch-size 64 --n-epochs 2 --eval-every 256 --eval-episodes 2 --checkpoint-every 256
quadruped-play --output Ch12/runs/review-12-4 --steps 200
```

### 관찰 → 설명 → 응용

`review-12-4` 출력 폴더가 이미 있다면 새로운 접미사를 쓰고 기존 기록을 덮어쓰지 않는다. `tensorboard --logdir Ch12/runs/review-12-4/tensorboard`에서 episode reward만 보지 말고 평가 곡선과 loss를 함께 비교한다. `dummy`와 `subproc`의 시작 비용 및 초당 전이 수를 측정하는 실험을 12.7로 넘긴다.

### 제출 증거 및 합격선

- 실행 명령과 사용 Python/라이브러리 버전, git 기준 커밋, seed, 주요 출력 수치/로그를 기록한다.
- **합격선:** 학습 output 신규 생성, manifest/final_model/best_model/평가 기록 생성 여부, 재생 시 schema 검사 및 에피소드 종료 처리 확인. 성공률·장기 보행은 별도 실험으로 판정한다.
- 기존 `evidence/`는 **과거 실행 기록**이고 위 명령을 새로 실행한 증거가 아니다. GUI·물리 엔진·ROS 환경을 실제로 확인하지 못했다면 '미검증'으로 기록한다.
- 보고서: [12.4절 코드 리뷰](SECTION_12_4_REPORT_KO.md). 기존 학습/시연 스크립트와 구성 파일 설명은 이 문서의 위쪽 절에 그대로 보존한다.
