# 14.8 강화학습 정책 배포 실습 — G07 (G08 물리 제어 별도)

> 출고 상태(2026-11-26): [최신 인수 원장](CH14_ACCEPTANCE_LEDGER.md), [출판 QA](reports/G09_RELEASE_CLOSEOUT_QA_20261126_KO.md) 우선. 아래 기존 checkpoint는 역사적 증거이며, G09 WSL2 L3는 14.9의 네 선택 경로에만 해당합니다. 전체 출고 HOLD, 권리 및 범위 승인 필요. 실제 실행 PIN은 G09_WSL2_OWNER_ACCEPTANCE_KO.md를 참조합니다.

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

## 7. 실제 검수 결과와 재사용 (2026-11-26)
Run45763347165 source 21d4281f825ed23938a399377b29bad5252fde25; artifact15090667475 (ZIP c8defc1a154c3d0ec92ddd3a7fbd70f8d3b012dc21d375acde9f5c5f9be9641d; 23/23). 이미 학습한 final_model.zip 및 export를 사용: archive 보존 및 SHA 검증 후 `python scripts/g07_verify_reuse.py --root /absolute/extracted_artifact`. ONNX/contract SHA c6bc846346ea156f39b31a84da3e2051e17d377b39b825eb08ba3ef77f51e546 / 1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168. 128 실제 환경 관측+8 수치 입력, max abs7.45e-8, 240 DDS shadow 추론, command0, max.325422ms. 신규 학습을 반복하지 않는다. 14 additional wheels hash lock `requirements/rl.lock.txt` is derived from successful pip install report; clean locked reinstall is next G08 environment check. Artifact contains newly generated smoke evaluation binaries (public repo Actions artifact, 30d), not original external weights or release. No model binaries Git committed. Actual physical control/WSL2 NOT_RUN. See reports/G07_EXECUTION_REPORT_KO.md.

## 8. 코드 14-19 — 실제 제어 (G08 SMOKE_ONLY 범위 검수 완료)
G07 원본 ZIP (run 45763347165, artifact 15090667475)의 파일을 다운로드하여 ZIP SHA256을 확인한 뒤 압축을 푼다. 원본 ZIP이 없거나 일치하지 않으면 중단하며 자동 학습/export하지 않는다. G08 모델은 학습된 보행 제품이 아닌 SMOKE_ONLY. 실제 MuJoCo 정상 경로 검수는 45787876247, Gazebo는 45799511462에서 성공했으며 보호 계약 및 clock reset은 별도 CI에서 검수했다.

실제 Ubuntu24.04/Jazzy CPU 환경에서 검증된 cpu.lock.txt와 rl.lock.txt를 적용한 venv 및 ROS underlay를 활성화하고 vendor/ch12 패키지를 설치한다. Ch14 기준:
```bash
python scripts/g07_verify_reuse.py --root /absolute/extracted_g07
cd ros2_ws
colcon build --packages-select ch14_rl_deployment
source install/setup.bash
```
두 터미널에서 동일 underlay/overlay/venv, ROS_DOMAIN_ID를 사용한다. 먼저 `ros2 run ch14_rl_deployment mujoco_bridge`로 물리를 실행한다. 다른 터미널에서 controller를 실행한다. 모델/계약은 위 원본 archive를 사용한다. 기본은 disabled; 실제 시뮬레이션만 명시적으로 enable한다. 다른 명령 발행 노드와 동시에 사용 금지.
```bash
EXPORT=/absolute/extracted_g07/export
ros2 run ch14_rl_deployment rl_controller --ros-args \\
  -p use_sim_time:=true -p backend:=mujoco -p enabled:=false \\
  -p onnx_path:="$EXPORT/quadruped_policy.onnx" \\
  -p contract_path:="$EXPORT/policy_contract.json" \\
  -p contract_sha256:=1209b04f0d6f31d12249b7fd355ba4ed7d45789cfee8d94486d869608c48d168
```
실제 명령 실습은 disabled 실행을 종료한 다음 동일 명령에서 enabled:=true로 재실행. /rl/controller_status, /rl/joint_targets, /joint_states, /simulation/odom을 별도로 관측한다. `ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.2}}'`는 관측 명령의 변화를 확인하기 위한 것이며 보행 거리 성공 판정 아님. 명령 발행 중단 후 .5 sim seconds에 관측 command가 0으로 돌아오는지 확인. 먼저 controller를 종료하고 이어 bridge를 종료한다. 

CI 실제 증거: ACTIVE400, 50Hz, 독립 DDS 목표400/400 (최대 차이0), 400 실제 피드백쌍, 최대 연속 목표 변화 .0249288rad, 높이 .39247m, 0.169344ms 최대 추론, pause/resume, exit0/0. 해당 수치는 클라우드 CI이며 사용자 WSL2 인수값이 아니다. Gazebo와 보호 시험 결과는 아래와 같다.

## 9. Gazebo 실제 제어 및 실습 관측
G08-D 실제 CI: 45799511462. Ch11/Ch12 exact source 9개는 vendor/ch11_g08/REUSE_MANIFEST.json으로 추적한다. G08 실제 검수는 scripts/g08_gazebo_ci.sh와 g08_gazebo_probe.py를 이용한 isolated CPU container에서 실행했다. WSL2 수동/Gazebo GUI 실행은 이번 CI로 인수하지 않는다. 수동 실습을 준비할 때 xacro, ros_gz_bridge, ros_gz_sim 설치 및 기존 동일 ROS domain/단일 clock/제어권 조건을 확인한다. 다음은 검수 코드의 실행 순서이며 WSL2에서 실제 실행 확인된 원샷은 아니다.
1. Ch14/vendor/ch11_g08/gazebo_description.py의 prepare_description으로 urdf/robot.urdf.xacro를 변환한다. 원본 xacro를 수정하지 않는다.
2. gz sim -s -r --headless-rendering으로 worlds/empty_world.sdf 실행, /world/my_empty_world/create 서비스 확인.
3. ros_gz_bridge parameter_bridge에 config/ros_gz_bridge.yaml 설정. ros_gz_sim create로 준비한 URDF를 이름 my_quadruped, z=.5에 생성한다.
4. 8절 controller 명령의 backend:=gazebo로 설정하고 실제 시뮬레이션에서만 enabled:=true. /rl/controller_status, /joint_states, /imu/data_raw, /simulation/odom 및 /model/my_quadruped/joint/<joint_name>/cmd_pos 12개 관측. Gazebo에는 JointState 명령 대신 Float64 12개를 사용한다.
5. 종료는 controller→bridge→Gazebo /server_control stop 요청, 실제 exit code 확인. ACK만으로 종료 성공 선언 금지. 일반 Ctrl+C/GUI 종료 문제는 별도 검수 경계.

두 엔진 결과: MuJoCo 400/400 DDS 및 피드백, Gazebo 399/399, 모두 50Hz. Gazebo 명령 Float64에는 header가 없어 witness receipt ±100ms 창에서 per-joint 순서를 유지해 비교했다. 실제 최대 차이 2.980167ms이며 source timestamp 지연으로 해석하지 않는다. 4788개 관절 목표값 최대 오차0, 399 feedback pair 중 393 target 방향 성분 양수. 목표의 물리 추종 오차나 인과 지연을 확정한 것이 아니다. Gazebo 최소 높이 .390415m, 최대 추론 .144613ms, 세 프로세스 exit0. 

## 10. 보호 계약과 학습 질문
실제 MuJoCo 보호 시험 45799639451: 잘못된 IMU frame에서 hold 19 DDS/19 상태, 추가 writer 발견 시 신규 발행0 및 rearm 거절, writer 제거 후 복구, explicit rearm의 arming→active, 실제 ORT 호출 뒤 시험 전용 35ms 지연으로 overrun 35.147894ms/새 명령0, disabled publisher0. 시험용 harness는 교육용 일반 controller 실행 경로가 아니다. Clock reset 45799888629: 합성 센서 기반 실제 DDS에서 5.8→2.02s, 43 hold targets, new policy0, 43 active recovery, old command cleared. 물리 엔진 미사용. 
- 왜 명령이 0이 되더라도 관절 위치 명령이 계속 나올 수 있는가? 속도 요청 만료는 관절 제어 해제나 긴급정지와 같지 않다.
- 왜 hold가 필요한가? 기존 마지막 유효 위치를 유지하는 동안 신규 정책 출력은 금지한다. 외부 writer가 실제 명령을 발행하는 상황의 안전 보장까지 의미하지 않는다.
- 왜 receipt와 source timestamp를 구분하는가? DDS Float64는 header가 없어 실제 명령 생성 시간의 정확한 지연을 주장할 수 없다.
- 왜 50Hz와 ONNX parity가 안정적 보행을 보장하지 않는가? 짧은 SMOKE_ONLY policy의 물리 연결 확인과 학습 품질 평가의 목표가 다르다.

G08 CPU T19 SCOPED_PASS; both normal physics engines, MuJoCo protection and synthetic reset. WSL2 L3/GPU/learned locomotion NOT_ACCEPTED or NOT_RUN as applicable. 기존 G01 및 전체 배포 HOLD 유지. 자세한 데이터 및 출처는 reports/G08_EXECUTION_REPORT_KO.md.
