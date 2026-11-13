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

---

## 후속 검수 — 저장된 PPO의 0/10 도달 실패 원인 분리 (2026-11)

기존 공개 CI [#43361732383](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43361732383)는 원본 PPO를 10개 시드(1000~1009)에 적용했을 때 **성공 0/10, 마지막 EE–target 평균 거리 0.432753m**로 보고했다. 평가 계산은 정상이라는 사실과 정책 성능이 목표에 미달한다는 사실을 구분해야 한다.

성능 개선을 위한 최초 진단은 **실패한 10개 목표 자체가 원본 MuJoCo 로봇의 기구학적 작업공간 안에 있는지** 확인하는 것이다. 이를 확인하지 않고 PPO 학습률이나 보상 가중치를 임의로 바꾸면 원인을 찾기 어렵다.

- 실행기: `ci/ch08_87_kinematic_diagnosis.py`
- 독립 감사: `ci/ch08_87_verify_kinematic_receipt.py`
- 공개 CI: `.github/workflows/book-ch08-87-kinematic-feasibility.yml`
- 의존성: Python 3.12 / MuJoCo 3.3.7 / Gymnasium 1.1.1 / NumPy 2.2.6. ROS 2, PyTorch, SB3 재실행은 이 단계에서 불필요하다.

실행 시 기존 `ReachEnv.reset(seed=1000~1009)`가 만드는 **실제 목표 3D 좌표**를 사용하고, `mujoco.mj_jacSite`의 3×6 위치 Jacobian으로 제한 스텝(≤0.20rad) DLS 역기구학 검색을 수행한다. 관절 제한은 원본 MuJoCo 모델의 `jnt_limited`와 `jnt_range`를 따른다. 각 목표에 8개 서로 다른 초기 관절 상태를 사용하고, 3D 말단 위치 오차 0.05m 미만인 해를 찾았는지 기록한다.

**주의:** 이 검수는 토크 명령이나 동역학 시뮬레이션, 충돌 검사 또는 PPO 추론을 하지 않는다. `IK 해 발견`은 **해당 목표의 위치 기구학적 실현 가능성에 관한 수치 증거**일 뿐, PPO가 그 목표를 학습했다거나 안전하게 움직인다는 의미가 아니다. 반대로 IK 해를 못 찾았다고 물리적으로 도달 불가능하다고 단정해서도 안 된다.

~~~bash
cd ~/Pysical_AI_ROS2
python3 -m venv /tmp/ch08-87-geometric
source /tmp/ch08-87-geometric/bin/activate
python -m pip install 'mujoco==3.3.7' 'gymnasium==1.1.1' 'numpy==2.2.6'
python ci/ch08_87_kinematic_diagnosis.py
python ci/ch08_87_verify_kinematic_receipt.py \
  ci-results/ch08-87-geometry/receipt.json \
  Ch08/ros2_ws/models/ppo_reach_final.zip \
  Ch08/ros2_ws/src/my_robot_description/assets/simple_arm_6dof.xml \
  Ch08/ros2_ws/rl_env.py
~~~

검증 성공의 의미는 **원본 목표 생성/기하학적 접근 가능성에 관한 독립 수치 진단**만이다. 기존 정책 ZIP·XML·환경 소스의 SHA256이 실행 전후 일치해야 하며, PPO 성공률 0/10은 이 시험에서 재평가하지 않으므로 이전 결과 그대로 유지한다.

후속 개발 판단: 많은 목표에서 기구학적 해가 실제 발견되면 학습 설정·관측·탐색·보상 및 동역학 제어를 점검한다. 목표 대부분에서 수치 해를 찾지 못하면 작업공간/목표 샘플링과 IK 초기화 방법부터 검토한다. 어느 경우에도 성공률을 인위적으로 승격하지 않는다. Ch10 #123은 HOLD.

### 실제 검수 결과 및 해석

같은 10개 시드의 목표는 기구학적 위치 IK로 **10/10 모두 오차 0.05m 미만**의 해를 찾았다. 공개 CI #43417674577의 독립 receipt 감사 PASS이며, 기존 PPO의 **실제 성공률 0/10은 그대로 유지**한다. 자세한 10개 시드 원본 데이터와 다음 진단 단계는 [§8.7 기구학적 실패 원인 분석 보고서](SECTION_8_7_KINEMATIC_DIAGNOSIS_KO.md)를 참고한다.

---

## 다음 검수 — 실제 MuJoCo 토크 제어와 원본 목표 거리 변화 (2026-11-13)

앞선 [위치 IK 검수 #43417674577](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43417674577)에서 같은 10개 시드의 목표 중 **10/10**에서 위치 기구학 해를 발견했다. 이는 저장된 PPO의 기존 **0/10 성능 실패**를 해결한 것이 아니다. 남은 문제는 실제 6개 모터 토크의 동적 실행과 학습된 정책의 차이를 분리하는 일이다.

### 새 시험의 제한 범위

- **실제 원본 환경:** `Ch08/ros2_ws/rl_env.py`의 `ReachEnv`, 원본 `simple_arm_6dof.xml`, 실제 `env.step(action)`과 MuJoCo `mj_step`. PPO 모델 ZIP은 SHA256만 확인하고 추론·재훈련하지 않는다.
- **시드:** 우선 1000,1001,1002 세 목표만 별도 비교한다. 각 시드에서 **원본 모터 토크 0**과 **진단용 관절 PD+중력 보상**을 동일한 초기 상태에서 각각 실행한다. 초기 조건은 MuJoCo `mj_resetData`로 분리한다. 이는 원본 `ReachEnv.reset`가 MuJoCo 시간·구동 상태까지 모두 초기화한다는 의미가 아니다.
- **토크 제한:** 여섯 원본 모터 `ctrlrange[-1,1]`과 XML의 `gear`를 그대로 따른다. 진단용 제어 입력은 `clip((40*(q_goal-q)-5*qvel+qfrc_bias)/gear,-1,1)`. 이는 **교재 기본 PPO가 아닌 시험용 대조 제어기**이다.
- **시간·종료:** 각 시드별 최대 원본 `env.step` 300회, 스텝당 MuJoCo 5×0.002초 → 최대 3초. 초기/최소/종료 시점 EE–목표 거리(m), 실제 관절 움직임(rad), 최대/평균 모터 명령, 목표 반경 0.05m 도달 여부를 분리 기록한다.
- **PASS 경계:** 실제 `env.step`에서 유한한 관절 운동과 토크 제한 준수를 확인하고, 세 목표 중 최소 하나에서 초기 거리 대비 0.10m 이상의 접근을 관찰한다. **최소 거리 개선 ≠ 최종 목표 도달 또는 안정적 추종**이다. 결과가 부족하면 FAIL과 원본 로그를 남긴다.
- **실행기:** `ci/ch08_87_torque_dynamics_once.py`, 독립 감사 `ci/ch08_87_verify_dynamics_receipt.py`, 공개 CI `.github/workflows/book-ch08-87-torque-dynamics.yml`. 기존 §8.6 PPO 학습과 §8.7 저장 ZIP 평가를 재실행하지 않는다.

~~~bash
cd ~/Pysical_AI_ROS2
python -m pip install 'mujoco==3.3.7' 'gymnasium==1.1.1' 'numpy==2.2.6'
python ci/ch08_87_torque_dynamics_once.py
python ci/ch08_87_verify_dynamics_receipt.py \
  ci-results/ch08-87-dynamics/receipt.json \
  Ch08/ros2_ws/models/ppo_reach_final.zip \
  Ch08/ros2_ws/src/my_robot_description/assets/simple_arm_6dof.xml \
  Ch08/ros2_ws/rl_env.py
~~~

이 실험을 성공하더라도 기존 PPO의 0/10 목표 성능은 그대로다. 동적 접근과 별개로 정책의 보상·탐색·학습·홀드아웃 평가 검수는 다음 단계에서 진행한다. 충돌 안전성·모터 과열·물리 하드웨어·GUI는 NOT_RUN, Ch07 RGB-D BLOCKED, Ch10 HOLD.
