# Ch08 §8.7 — PPO 평가 지표의 결측 오류 제거와 실제 목표 거리 측정

> 이 절의 공개 CI는 기존 Git에 저장된 6DOF 정책 모델 ZIP을 로드해 **10개의 고정 시드**에서 실제 MuJoCo rollout을 수행한다. 256-step 신규 훈련은 §8.6에서 이미 별도 검증했고 재실행하지 않는다.

## 원본 코드에서 확인한 오류

과거 evaluate_robot.py는 env.step()의 info에 distance가 없을 경우 평균 정착 오차를 0.0mm로 출력했다. 하지만 이 0은 거리가 0이었다는 측정이 아니라 **결측값**이었다.

이번 교정에서 ReachEnv.calculate_reward()가 이미 계산한 실제 EE와 target 간 유클리드 거리(m)를 info.distance에 추가한다. 평가기는 이를 관측 배열의 EE [12:15] 및 목표 [15:18] 좌표로 다시 계산한 값과 비교하며, 누락·비유한·불일치 시 FAIL 처리한다.

## 준비 — ROS 2가 아닌 Python 3.12 환경

~~~bash
cd ~/Pysical_AI_ROS2/Ch08/ros2_ws
source .venv/bin/activate
python -m pip install mujoco gymnasium numpy stable-baselines3
~~~

CI에서는 앞 절과 같은 호환 패키지 및 PyTorch CPU를 재사용한다. 저장된 models/ppo_reach_final.zip은 **절대 덮어쓰지 않는다**.

## 원본 평가 스크립트 실행

~~~bash
python evaluate_robot.py \
  --model models/ppo_reach_final.zip \
  --episodes 10 \
  --max-steps 300 \
  --seed 1000 \
  --output-json evaluation_8_7.json
python -m json.tool evaluation_8_7.json
~~~

실제 평가에서는 정책 observation 18개/action 6개 계약이 일치해야 한다. 모델 ZIP이 다른 차원으로 학습된 것이라면 변경 없이 **INCOMPATIBLE FAIL**을 보존하고, 임의로 모델을 변환하지 않는다.

평가기는 각 에피소드에 seed=1000~1009를 적용한다. 종료 상태는 SUCCESS, TRUNCATED, TERMINATED 또는 STEP_LIMIT로 기록하고, 후자의 경우 성공으로 세지 않는다. 각 episode의 실제 최종거리, 총보상, 스텝수, 평균 액션 변화량을 JSON에 기록한다.

정상 출력 형식(실제 수치는 CI에서 검증한 후 보고):

~~~text
CH08_87_ACTUAL_POLICY_EVALUATION_PASS episodes=10 success_count=... mean_final_distance_m=... success_rate_pct=...
CH08_87_REAL_EE_DISTANCE_AND_BOUNDED_METRICS_SCOPED_PASS
~~~

정책의 성공률이 낮더라도 **평가 파이프라인은 PASS일 수 있다**. 10개 에피소드 실측 수치를 장기학습 품질 인증이나 실기 배포 판단으로 해석하지 않는다.

## TensorBoard와 RGB 녹화의 분리된 판정

§8.6에서 TensorBoard 이벤트 파일 생성은 실제 PASS했으나, 서버 브라우저 렌더링은 이번 CI에서 수행하지 않는다. 확인하려면 별도 로컬 GUI 셸에서 다음을 실행한다.

~~~bash
tensorboard --logdir smoke_runs --host 127.0.0.1 --port 6006
~~~

현재 ReachEnv.render_mode="rgb_array"에서 RGB uint8 프레임 반환이 구현되어 있지 않으므로, 실제 RGB 녹화는 **BLOCKED/NOT_RUN**으로 구분한다. 이번 평가 CI에서는 GPU, 화면, RecordVideo를 실행하지 않으며 성능 성공으로 승격하지 않는다.

## 공개 CI와 증거

- 워크플로: .github/workflows/book-ch08-87-policy-evaluation.yml
- 원본 실행: python evaluate_robot.py
- 독립 감사: ci/ch08_87_verify_receipt.py
- 증거: 기존 모델 ZIP SHA256, source SHA, Actions run ID, 10개 시드별 실제 거리·보상·상태, 300-step 상한 및 결과 JSON.
- Ch08 §8.6 기존 PPO 학습은 NOT_RERUN, Ch10 HOLD 유지.

[이전 정적 리뷰](SECTION_8_7_REPORT_KO.md)는 결함 기록으로 보존한다.
