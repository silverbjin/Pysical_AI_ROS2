# LAB 8.6 — PPO 스모크 학습, 저장 및 재로드

> ROS 2를 사용하지 않는 독립 Python/MuJoCo 실습. 긴 학습이 아닌 256 스텝 PPO의 실제 gradient update, ZIP 저장·재로드, 실제 환경 추론을 검수한다. 단기 학습 성공이 목표 도달 성능을 보장하지 않는다.

## 준비(새 터미널, ROS 2 overlay 제외)

~~~bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install mujoco gymnasium numpy stable-baselines3 tensorboard
~~~

공개 CI의 Python 3.12 고정 버전은 torch CPU 2.5.1, MuJoCo 3.3.7, Gymnasium 1.1.1, SB3 2.6.0, NumPy 2.2.6, TensorBoard 2.19.0이며, 검수 Artifact에 실제 pip freeze를 기록한다.

## 원본 책 코드의 짧은 PPO 학습 실행

원본 기본 실행은 2,000,000 timesteps로 장시간 학습을 시작했다. 이번 교정으로 train_reach.py의 기본 모드는 안전한 256-step smoke다. 대용 검수기를 학습시키지 않고 원본 진입점을 실행한다.

~~~bash
python train_reach.py --mode smoke --seed 42
~~~

고유 경로를 명시하면 중복 실행/모델 덮어쓰기를 방지할 수 있다.

~~~bash
python train_reach.py --mode smoke --seed 42 \
 --output-dir smoke_runs/manual_001
~~~

이미 존재하는 폴더라면 실패하고 기존 데이터를 보존한다. models/ppo_reach_final.zip은 덮어쓰지 않는다.

**정상 예상 출력(실제 실행 결과가 나와야 PASS):**

~~~text
CH08_86_OUTPUT_ISOLATED_PASS dir=...
CH08_86_REAL_REACH_ENV_SB3_API_PASS observations=18 actions=6
CH08_86_ACTUAL_PPO_GRADIENT_UPDATE_PASS steps=256 max_weight_delta=...
CH08_86_MODEL_SAVE_RELOAD_REAL_ENV_PREDICT_PASS sha256=...
CH08_86_TENSORBOARD_EVENT_FILE_PASS count=...
CH08_86_REAL_PPO_SMOKE_SCOPED_PASS_NO_PERFORMANCE_CLAIM
~~~

### 어떤 원리를 검증하는가?

1. 기존 6DOF ReachEnv에서 6개 정규화 action과 18개 observation의 Gymnasium 규격을 확인한다.
2. TimeLimit 300스텝을 적용해 장기학습 중 비정상적으로 끝나지 않는 에피소드를 방지한다. 원본 환경을 변경하지 않고 Wrapper만 적용한다.
3. 학습 전후 PPO 정책 가중치 최대 차이가 0을 초과하는지 직접 비교한다. 로그에 step 숫자만 찍혔다는 이유로 학습 성공을 주장하지 않는다.
4. 저장한 ZIP을 다시 열고 올바른 6차원 action으로 실제 MuJoCo environment step을 수행한다.
5. TensorBoard 이벤트 파일, XML SHA256, ZIP SHA256, 소스 SHA 및 패키지 버전을 기록한다.

## 결과 확인

~~~bash
find smoke_runs -name receipt.json -o -name smoke_policy.zip
# 위 명령으로 확인한 실제 디렉터리를 지정한다.
python -m json.tool smoke_runs/manual_001/receipt.json
~~~

각 receipt에는 모델 ZIP 해시, 실제 완료 스텝, 정책 가중치 변화량, 관측/행동 차원, 환경 버전 등이 들어간다. 256스텝 결과를 곧바로 성공률·수렴·실기 배포 가능성으로 해석하지 않는다.

## 장시간 학습 — 별도 선택

~~~bash
python train_reach.py --mode full --seed 42
~~~

위 명령은 2,000,000 스텝이다. 충분한 CPU/저장 공간 확인 후 별도 실행하고, Ch08 §8.6 공개 CI에서는 수행하지 않는다. 장시간 학습의 성공률/성능 향상은 별도 다중 시드 평가가 필요하다.

## 공개 CI 검수

- 워크플로: .github/workflows/book-ch08-86-ppo-smoke.yml
- 실제 원본 실행: python train_reach.py --mode smoke --seed 42 --output-dir ...
- 독립 감사: ci/ch08_86_verify_receipt.py
- 증거: source SHA, Actions run ID, 실제 ZIP 및 SHA256, JSON, TF가 아닌 진짜 PPO 가중치 변화, Python/PyTorch 패키지 버전, 학습/재로드 로그, 에피소드 타임아웃 정책.
- NOT_RUN: 장기 학습, 목표점 도달률 및 수렴, 렌더링/GUI, 실제 로봇. Ch10 HOLD.

[원본 정적 검토](SECTION_8_6_REPORT_KO.md)는 과거 설계 오류 기록으로 보존한다. 최종 PASS 판정은 새로운 공개 CI의 실제 원본 Artifact가 증명하는 범위에 한정한다.
