# 12.8 ROS 2와 PPO 통합 실습

## 목표와 계약

같은 PPO 번들의 관측·관절 순서·기본 자세·스케일·제어 주기를 MuJoCo와 Gazebo에 적용한다. 이 실습의 ROS 어댑터는 **locomotion 48차원 위치 잔차 정책**을 지원한다. goal도 48차원이지만 의미가 다르므로 거부한다. avoidance 정책에는 목표·LiDAR ROS 입력을 추가 설계해야 한다.

관측 순서는 몸체 선속도(3), 몸체 각속도(3), 몸체 중력(3), 몸체 속도 명령(3), 기본 자세 대비 관절각(12), 관절속도(12), 실제 발행된 위치 타깃의 잔차 행동(12)이다. 관절 순서는 FR, FL, RR, RL 각각 hip/thigh/calf이다. ROS JointState는 이름으로 정렬한다. ROS 쿼터니언은 xyzw, MuJoCo는 wxyz이며 중력은 Rᵀ[0,0,-1]이다. 단위는 m, s, rad, rad/s이다.

## 설치와 빌드

Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic 환경에서 리포지토리 루트를 현재 폴더로 사용한다. 먼저 기존 Ch11 의존성을 설치하고 빌드한다. Windows Python으로 ROS 노드를 실행하지 않는다.

```bash
source /opt/ros/jazzy/setup.bash
python3 -m venv --system-site-packages /tmp/ch12-ros-venv
source /tmp/ch12-ros-venv/bin/activate
python -m pip install 'torch==2.5.1' --index-url https://download.pytorch.org/whl/cpu
python -m pip install -e './Ch12[ros,train,test,visual]'
(cd Ch11/ros2_ws && colcon build --symlink-install)
(cd Ch12/ros2_ws && colcon build --symlink-install)
source Ch12/scripts/ros_env.sh
export ROS_DOMAIN_ID=89
```

`ros_env.sh`가 Python 패키지와 두 ROS overlay를 연결한다. 새 터미널마다 venv 활성화와 이 스크립트 source를 반복한다. `[ros]`는 NumPy 1.26.4를 사용한다. Ubuntu의 cv2 바이너리와 NumPy 2를 섞으면 import 과정에서 ABI 오류가 발생한다. 학습과 추론도 같은 NumPy 주버전을 사용한다. 다른 주버전에서 저장한 체크포인트는 원래 환경에서 실행하거나 다시 학습한다.

## 학습 번들 만들기

```bash
quadruped-train --task locomotion --output Ch12/runs/ros-smoke \
  --total-timesteps 2048 --n-envs 2 --n-steps 64 --batch-size 64 \
  --n-epochs 2 --eval-every 1024 --eval-episodes 1
```

이 짧은 실행은 연결 검증용이다. 실용적인 보행에는 별도의 충분한 학습과 평가가 필요하다. 모델 ZIP 하나가 아니라 manifest.json을 포함한 출력 폴더를 전달한다. 환경·관측 의미·스케일과 체크포인트 일치를 검사하므로 이름만 바꾼 타 과제 모델은 사용할 수 없다. VecNormalize는 이 실습에서 사용하지 않는다.

## 시뮬레이터 실행

먼저 기본 모니터링 모드에서 센서와 `/rl/controller_status`를 확인한다.

```bash
ros2 launch quadruped_rl_ros rl_simulation.launch.py \
  backend:=mujoco bundle_path:="$PWD/Ch12/runs/ros-smoke"
```

종료 후 아래 명령으로 실제 MuJoCo 제어를 실행한다. Gazebo는 `backend:=gazebo`로 바꾼다. 두 시뮬레이터를 동시에 실행하려면 ROS_DOMAIN_ID를 분리한다. 기존 Ch11 FSM launch는 함께 실행하지 않는다.

```bash
ros2 launch quadruped_rl_ros rl_simulation.launch.py \
  backend:=mujoco enabled:=true bundle_path:="$PWD/Ch12/runs/ros-smoke"
# 다른 터미널: 같은 venv/overlay/domain
ros2 topic pub --once /cmd_vel geometry_msgs/msg/Twist '{linear: {x: 0.2}}'
ros2 topic echo /rl/controller_status
```

Gazebo launch는 검증에 적합한 headless server로 시작한다. 별도 GUI가 필요하면 동일한 GZ_PARTITION에서 클라이언트를 연결한다. Rviz2는 base_link 및 기존 TF, `/rl/command_marker`의 명령 화살표를 표시할 수 있다.

## 토픽과 보호 동작

| 방향 | 토픽 | 의미 |
|---|---|---|
| 입력 | /imu/data_raw | 자세와 몸체 각속도 |
| 입력 | /joint_states | 이름을 가진 12관절 위치·속도 |
| 입력 | /simulation/odom | 위치와 몸체 선속도, base_link child frame |
| 입력 | /cmd_vel | 몸체 vx, vy, yaw 속도 명령 |
| MuJoCo 출력 | /rl/joint_targets | 이름·시각을 가진 JointState 위치 타깃 |
| Gazebo 출력 | /model/my_quadruped/joint/각관절/cmd_pos | Float64 위치 타깃, rad |
| 진단 | /rl/controller_status | 관측·명령·추론 시간·보호 상태 |

학습의 action_scale=0.35 rad와 nominal=[0,-0.5,1]×4를 번들 환경에서 읽는다. 위치 타깃은 제어 step당 0.1 rad와 관절 한계로 제한하고, 초기에는 측정 자세에서 nominal로 1 rad/s로 이동한다. 실제 발행 타깃으로 행동 이력을 갱신한다. 위치를 effort 토픽에 보내지 않는다. Gazebo는 기존 Ch11 위치 제어기 인터페이스에 연결하며, 초기 관절 자세도 nominal로 설정한다.

50Hz는 시뮬레이션 시간 기준이다. status의 시각과 추론 시간을 함께 확인한다. 센서 지연 0.25초, 센서간 시각 차이 0.1초, 역순·미래·NaN·누락 데이터는 새 정책 명령을 차단한다. /cmd_vel은 0.5초 뒤 영명령으로 만료된다. 시뮬레이션 시계가 멈춰도 STEADY 시계 감시기가 0.5초 뒤 hold 상태를 알린다. 추론 20ms 초과 시 해당 결과를 버린다. 출력 토픽에 다른 publisher가 있으면 제어를 차단한다. fault 복구 후 필요하면 `/rl/rearm` Trigger 서비스를 호출한다. 이 보호는 실제 하드웨어 비상 정지 장치를 대체하지 않는다.

## 실제 통합 재검증

```bash
python Ch12/scripts/verify_ros_integration.py --backend mujoco \
  --bundle Ch12/runs/ros-smoke --output Ch12/runs/check-mujoco
# 첫 실행 종료 후
python Ch12/scripts/verify_ros_integration.py --backend gazebo \
  --bundle Ch12/runs/ros-smoke --output Ch12/runs/check-gazebo
MUJOCO_GL=egl CH12_TEST_RENDER=1 python -m pytest Ch12 -q
```

검증기는 실제 ROS launch, 센서→PPO→위치 타깃→물리 엔진 루프, 명령 전달과 만료, 유한 관측, 관절 개수, 주기, 몸통 높이, 정상 종료를 검사한다. MuJoCo에서는 pause 후 벽시계 감시기와 재개까지 확인한다. 90초 내 제어가 시작되지 않으면 실패한다. 원시 로그와 result.json을 함께 확인한다. 짧은 통과 결과를 학습된 보행 능력이나 두 물리 엔진의 동역학 일치로 해석하지 않는다.