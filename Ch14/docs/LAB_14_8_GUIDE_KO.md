# 14.8 강화학습 정책 배포 실습 — G07 (G08 물리 제어 별도)
## 0. 실습 목표
Ch12 locomotion-v1-48의 PPO Actor를 CPU ONNX로 변환하고 동일한 관측에 대한 12차원 행동을 비교한다. 48차원이라는 숫자가 같아도 goal/avoidance 정책과 섞지 않는다. VecNormalize 없음. G07은 Shadow, 실제 관절 명령 publisher를 생성하지 않는다. 안정적 보행은 별도 검수이며 짧은 smoke 정책을 완성 보행 모델로 부르지 않는다.
## 1. 실행 환경
Ubuntu24.04/ROS Jazzy, Python3.12, CPU lock 기존 유지, 별도 RL venv system-site-packages. `requirements/rl.in`은 Ch12 원본 SB3 2.7.1, MuJoCo 3.3.7, Gymnasium1.2.1, TensorBoard2.20.0의 고정 직접 의존성. 실제 추가 wheel 해결 결과/해시 lock은 CI 결과에 따라 보존. `vendor/ch12/REUSE_MANIFEST.json` 19개 blob과 원본 Ch12 소스는 동일. Ch12 source license owner review pending. 외부 모델이나 신뢰되지 않는 PPO ZIP을 로드하지 않는다 (SB3 checkpoint는 pickle 역직렬화 포함). 
## 2. 모델 준비
먼저 이미 생성한 검증된 smoke receipt와 checkpoint SHA256, manifest SHA256을 확인한다. 원본 Ch12 모델 ZIP은 현 Git/Release에서 미확보. CI는 단일 2048 transition 학습 경로를 사용하며 후속 시험은 동일 번들만 재사용. 새 학습을 실습마다 반복하지 않는다. 사용자가 권리 확인된 원본 locomotion bundle을 제출하는 경우 별도 해시 검증 후 `OWNER_VERIFIED_BUNDLE` 범위로 구분한다.
## 3. 코드14-17 — 정책 변환
검증된 RL venv와 ROS underlay를 활성화하고 Ch14 기준으로 실행한다. 먼저 vendor/ch12를 로컬 임시 작업 디렉토리에 복사하고 `python -m pip install --no-deps --no-build-isolation /absolute/ch12-copy`로 설치. ROS workspace는 `colcon build --packages-select ch14_rl_deployment`로 빌드하고 install/setup.bash source. 예시에서 BUNDLE은 실제 확보한 checkpoint+manifest가 위치한 디렉토리이며 SHA는 승인된 receipt에서 읽는다.
```bash
BUNDLE=/absolute/smoke_bundle
OUT=/absolute/new_policy_export
python python/export_rl_policy.py --bundle "$BUNDLE" --checkpoint final_model.zip \
  --checkpoint-sha256 VERIFIED_CHECKPOINT_SHA \
  --manifest-sha256 VERIFIED_MANIFEST_SHA \
  --out "$OUT" --scope SMOKE_ONLY
```
Ch12 load_bundle validator가 환경 schema·normalization·space·내장 metadata를 확인. ActorExport는 deterministic distribution action을 얻고 action space bounds로 clamp. ONNX checker, static (1,48)→(1,12), CPU provider, finite, actual replay128 + numeric edges8의 원소별 allclose를 검수. `parity.json`, `policy_contract.json`, `parity_samples.npz`, `sensor_replay.json` 확인. 128개 실제 MuJoCo 환경 기록은 PPO 원본으로 실행한 관측 자료이며 ROS ONNX closed-loop 물리 시험은 아님. 입력 경계 8개는 수치 검수용으로 구분.
## 4. 코드14-18 — 관측 조립기
Ch12 ControllerCore를 호출하는 `ObservationAdapter`를 사용한다. 0:3 body linear, 3:6 body angular, 6:9 projected gravity, 9:12 command, 12:24 q-nominal, 24:36 qdot, 36:48 previous applied residual. FR FL RR RL hip/thigh/calf; 실제 문자열은 contract. 단위 SI, xyzw quaternion, body twist, 이름으로 재정렬. 임의 zero fill 금지. 마지막 action은 실제 적용 이력이며 Shadow에서 제어 명령이 없으므로 zero 초기 이력을 유지한다. 센서 .25s, skew .1s, command .5s, wall .5s, tilt45deg, 20ms inference, sim period.02s. nominal/scale/step limit/joint limits는 원본 유지.
## 5. ROS Shadow 실행과 관측
```bash
# 이미 설치된 ROS package와 검증된 model, contract 사용
ros2 run ch14_rl_deployment rl_shadow --ros-args \
  -p use_sim_time:=true -p onnx_path:="$OUT/quadruped_policy.onnx" \
  -p contract_path:="$OUT/policy_contract.json" \
  -p contract_sha256:=VERIFIED_CONTRACT_SHA
```
실행 후 /imu/data_raw, /joint_states, /simulation/odom, /cmd_vel, /clock가 필요. 상태는 /rl/controller_status. `SHADOW`의 observation48, shadow_action12, published=0, enabled=false 확인. 별도 실행기 `python scripts/g07_shadow_probe.py --export "$OUT" --out /absolute/new_evidence`는 installed Shadow를 직접 구동하고 actual DDS 센서를 재생하므로 위 수동 노드와 동시에 실행하지 않는다. 정상 및 shuffled, missing/duplicate, NaN, invalid frame/quaternion, stale/skew, command expiry, wall pause/recovery를 관측. 실제 제어 토픽 publisher0. 정상 종료와 status JSON 저장.
## 6. 과제와 경계
왜 PPO와 ONNX 수치 동등성은 보행 성공이 아닌가? 왜 관측의 이름·좌표·시각과 이전 applied action이 중요한가? 왜 /clock 정지 시 wall watchdog이 필요한가? G08에서 동일 ONNX와 계약, 실제 두 물리 엔진의 센서→명령→관절 응답·제어권·보호 검증을 수행한다. 이번 G07은 L2/L3/GPU 미검증. 
