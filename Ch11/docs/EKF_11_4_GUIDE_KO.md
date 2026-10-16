# 11.4 EKF 오도메트리 비교 실습 — 실행 및 원고 보완 안내

기준 main: `4ae9d6c0c9afc6ca5f9bb65c69e61c11ac2cec13`
수정 브랜치: `feat/ch11-ekf-lab`
환경: ROS 2 Jazzy / Gazebo Harmonic / Ubuntu 24.04 / WSL2

## 1. 실습 목표와 중요한 한계

원고의 명령 기반 추측 항법·공분산·robot_localization 설정·TF 확인·Before/After 비교를 실행 가능한 별도 실습으로 추가했다.

**명령 적분은 실제 다리 오도메트리가 아니며, IMU+명령 속도만으로 지속적인 미끄러짐이나 일정 속도의 오차가 자동으로 해결되지는 않는다.** 이번 실습은 융합 설정과 오차를 측정하는 방법을 배우며, EKF가 항상 더 정확하다는 결론을 미리 정하지 않는다.

기존 `config/ekf.yaml`, `localization.launch.py`, `sim_odometry` 경로는 유지한다. 기존 관측 기반 위치 추정과 실습용 명령 적분을 혼합하지 않는다.

## 2. 실행 구조

| 구분 | 입력 | 출력 | TF |
|---|---|---|---|
| 기존 위치 추정 | Gazebo 모델 관측 + IMU | /odom | odom → base_footprint 발행 |
| 11.4 모의 다리 오도메트리 | /cmd_vel 또는 격리된 명령 토픽 | /ekf_lab/raw | 발행하지 않음 |
| 11.4 IMU 준비 | /imu/data_raw | /ekf_lab/imu | 발행하지 않음 |
| 11.4 실습 EKF | /ekf_lab/raw + /ekf_lab/imu | /ekf_lab/filtered | publish_tf=false |
| 비교 기록기 | raw·filtered·/simulation/odom | CSV·메타데이터 | 발행하지 않음 |

Gazebo 모델 위치는 비교 기준에만 사용하며 실습 EKF의 입력 목록에는 없다. 기존 EKF가 발행하는 TF는 IMU 장착 프레임 연결·로봇 표시 등에 쓰인다. IMU는 base_link, EKF 몸체 프레임은 기존 URDF의 base_footprint이며 이 둘은 현재 고정 영변환이다.

## 3. 추가 파일

my_quadruped_bot 패키지:

- my_quadruped_bot/leg_odometry.py: 원고 실행 이름을 복원하되 **기본 출력을 /ekf_lab/raw로 격리**
- my_quadruped_bot/localization/lab_math.py: 명령 적분·수신 타임아웃·잡음·공분산 유틸리티
- my_quadruped_bot/ekf_lab_imu.py: sensor_msgs/Imu의 미상 공분산에 교육용 가정 적용
- config/ekf_command_lab.yaml: 속도 + IMU 자세·각속도
- config/ekf_command_lab_accel.yaml: 위 설정 + 선가속도·중력 제거
- launch/ekf_lab.launch.py: 한 번에 모의 오도메트리·IMU 준비·실습 EKF 실행
- setup.py: leg_odometry, ekf_lab_imu 실행 항목 추가

Ch11 아래:

- scripts/record_ekf_lab.py: 실제 수신 메시지 기록·시간 짝맞춤·상대 오차 CSV
- scripts/plot_ekf_lab.py: 기록된 궤적·오차 그래프 및 RMSE
- tests/test_ekf_lab.py: 11개 회귀 검사

## 4. 원고의 수정이 필요한 내용

### 4.1 “IMU가 가속하지 않았으므로 안 움직였다”는 결론

정지와 일정 속도 운동은 모두 선형 가속도가 0일 수 있다. 따라서 가속도 0만으로 속도가 0이라고 결론 내릴 수 없다. 지속적인 명령 속도 편향을 확실히 구분하려면 접촉 기반 관측, LiDAR/비전 오도메트리, SLAM 등 독립 관측이 필요하다.

“EKF가 미끄러짐을 알아내 실제로 거의 이동하지 않았음을 반영한다”는 결과는 보장하지 않는다. Before/After는 반드시 실제 기준 궤적과 비교하여 해석한다.

### 4.2 분산과 ±오차

±0.2 m는 분산이 아니다. 이를 표준편차 σ=0.2 m로 가정한다면 분산은 0.04 m²다. σ=0.5 m이면 분산 0.25 m²다.

독립적인 두 위치 측정을 단순 역분산 가중 평균하면 1.0 m와 0.8 m의 결합값은 약 0.9724 m다. 이 계산은 공분산 직관용 예시이며 시간 예측·측정 갱신을 수행하는 전체 EKF 자체와 동일하지 않다.

### 4.3 명령·노이즈·실제 미끄러짐

scale=0.9는 모의 추정 속도를 줄이는 계수다. 실제 Gazebo 위치에 비해 항상 10% 틀린다는 뜻이 아니고, 물리 바닥 마찰도 바꾸지 않는다. 기본 선형 잡음 표준편차는 0.01 m/s, yaw 속도 잡음은 0.005 rad/s이며 seed=42로 재현한다. 영속도·수신 타임아웃 중에는 잡음을 넣지 않는다.

물리 미끄러짐 실험은 별도로 바닥 접촉·마찰·제어 조건을 정하고 관측된 실제 이동량을 측정해야 한다. 기존 empty_world.sdf는 저마찰 실험 설정을 포함하지만 값만으로 실제 미끄러짐 정도를 확정하지 않는다.

### 4.4 11.2 출력은 Imu 메시지가 아니다

11.2의 /imu/rpy_filtered는 Float32MultiArray다. robot_localization에 그대로 넣을 수 없다. 이 실습은 Gazebo의 /imu/data_raw(sensor_msgs/Imu)를 받아 공분산을 준비한 /ekf_lab/imu를 사용한다. orientation도 Gazebo가 제공한 값이며 11.2의 RPY 배열을 quaternion으로 바꾼 출력이 아니다.

### 4.5 선가속도·중력 제거

기본 프로필은 선가속도를 융합하지 않는다. use_acceleration=true 프로필은 ax/ay/az를 켜고 imu0_remove_gravitational_acceleration=true를 함께 설정한다. 이때 유효한 IMU orientation이 없으면 입력을 거부한다.

중력 제거는 센서가 제공하는 orientation과 선가속도 규약이 맞아야 한다. “가속도 사용 = 자동 중력 보정”은 아니다. 가속도계를 켜면 항상 결과가 좋아지는 것도 아니다.

### 4.6 TF와 YAML

패키지명은 quadruped_system이 아니라 my_quadruped_bot이다. 현재 TF는 odom → base_footprint → base_link → lidar_link이며 IMU는 base_link에 장착되어 별도 imu_link가 없다.

실습 EKF는 기존 TF와 충돌하지 않도록 TF를 발행하지 않는다. 따라서 view_frames에 새 EKF용 별도 가지가 생기는 것을 기대하지 않는다.

process_noise_covariance에 “... 생략 ...”을 넣은 YAML은 실행할 수 없다. 제공 파일은 이 항목을 생략해 패키지 기본값을 사용한다. 사용자 지정 시에는 15×15의 전체 행렬이 필요하다.

## 5. 코드 받기·설치·빌드

가상환경을 해제하고 저장소 루트에서 진행한다.

```bash
cd ~/Pysical_AI_ROS2_publish
git status --short
git fetch origin
git switch --track origin/feat/ch11-ekf-lab
source /opt/ros/jazzy/setup.bash
sudo apt update
sudo apt install -y ros-jazzy-robot-localization ros-jazzy-tf2-tools python3-matplotlib
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
```

로컬 브랜치가 이미 있으면 `git switch feat/ch11-ekf-lab`을 사용한다. 경로는 실제 저장소 위치에 맞춘다. 각 새 터미널에서도 ROS와 Ch11 install 환경을 source한다.

## 6. Step 1~3: 시뮬레이션과 실습 EKF

### 터미널 1: 기존 로봇·센서·TF

```bash
ros2 launch my_quadruped_bot SLAM_simulation.launch.py
```

이 실행의 기존 EKF는 로봇 표시·관측 기반 위치 추정 경로다. 다음 실습 EKF의 입력을 대신하지 않는다.

### 터미널 2: 실습 노드 세 개 실행

```bash
ros2 launch my_quadruped_bot ekf_lab.launch.py
```

내부적으로 leg_odometry, ekf_lab_imu, ekf_lab_filter가 시작된다. 원고처럼 /odom/raw를 덮어쓰지 않고 /ekf_lab/raw를 사용한다.

주요 파라미터:

| 파라미터 | 기본값 | 설명 |
|---|---:|---|
| use_acceleration | false | true이면 중력 제거와 함께 IMU 가속도 융합 |
| scale | 0.9 | 명령에 곱하는 교육용 속도 계수 |
| noise_stddev | 0.01 | 활성 명령 중 선형 속도 잡음, m/s |
| angular_noise_stddev | 0.005 | 활성 명령 중 yaw 속도 잡음, rad/s |
| command_topic | /cmd_vel | 실제 시뮬레이션 명령과 같은 입력을 관찰 |
| use_sim_time | true | Gazebo 시각 사용 |

모의 오도메트리는 50 Hz로 발행하며 명령 수신 후 기본 0.3초가 지나면 속도를 0으로 둔다. 이 타임아웃은 **모의 추정 노드**의 기능이며 기존 FSM의 실제 정지 watchdog을 추가한 것이 아니다. 시각 역행이나 0.2초 초과 시각 점프에서는 포즈·명령을 초기화하므로 전체 실험을 재시작해 비교한다.

### EKF 설정의 의미

15개 상태 순서는 [x,y,z,roll,pitch,yaw,vx,vy,vz,vroll,vpitch,vyaw,ax,ay,az]다.

- odom0에서는 vx·vy·vyaw만 사용한다. 명령에서 적분한 위치를 같은 데이터의 속도와 중복 융합하지 않는다.
- imu0에서는 roll·pitch·3축 각속도를 사용하며 절대 yaw는 끈다.
- 가속도 사용 프로필에서만 마지막 ax·ay·az를 켠다.
- imu0_relative=false로 중력 방향과 자세의 기준을 임의로 초기 기울기에 맞추지 않는다.
- 3D 모드지만 기본 프로필에는 z·vz의 독립 관측이 없다. 수직 위치 정확도를 보장하지 않으며 비교는 평면 이동만 대상으로 한다.

공분산은 교육용 가정이다. 알려진 IMU 공분산과 -1(미제공)은 보존하고, 전부 0(미상)인 공분산에는 orientation=0.01 rad², 각속도=0.0004 (rad/s)², 가속도=0.25 (m/s²)²를 적용한다. 실측 교정값으로 소개하지 않는다. 모의 오도메트리 속도 분산 0.04 역시 임의 가정이다.

## 7. Step 4: 입력·출력·TF 확인

```bash
ros2 node info /ekf_lab_filter
ros2 topic info /ekf_lab/raw -v
ros2 topic echo /ekf_lab/imu --once
ros2 topic echo /ekf_lab/filtered --once
ros2 param get /ekf_lab_filter publish_tf
ros2 run tf2_ros tf2_echo odom base_footprint
ros2 run tf2_tools view_frames
```

publish_tf는 false, /ekf_lab/filtered 발행자는 실습 EKF 한 개여야 한다. 기본 /odom의 발행자는 여전히 기존 EKF다. TF 조회가 실패하면 센서 입력·시각·기존 위치 추정 상태를 확인한다. 단일 원인으로 단정하지 않는다.

## 8. Step 5: Before/After 측정

### 8.1 먼저 “자동으로 해결되지 않는 경우” 확인

로봇을 움직이지 않고 명령 적분만 움직이는 실험이다. 기존 ekf_lab.launch를 종료하고 다음처럼 격리 명령 토픽으로 바꾼다.

```bash
ros2 launch my_quadruped_bot ekf_lab.launch.py \
  command_topic:=/ekf_lab/cmd_vel scale:=1.0 \
  noise_stddev:=0.0 angular_noise_stddev:=0.0
```

별도 터미널에서 기록기를 시작한다. 저장소 루트 기준이다.

```bash
python3 Ch11/scripts/record_ekf_lab.py --seconds 30 --output /tmp/ekf_baseline.csv
```

또 다른 터미널에서 다음 명령을 약 3초 발행한 뒤 Ctrl+C한다.

```bash
ros2 topic pub -r 20 /ekf_lab/cmd_vel geometry_msgs/msg/Twist \
  "{linear: {x: 0.1}, angular: {z: 0.0}}"
```

/ekf_lab/cmd_vel은 FSM 입력이 아니므로 로봇에 전진 명령을 전달하지 않는다. /cmd_vel에 다른 발행자가 없는지 함께 확인한다. 모의 오도메트리는 명령 종료 뒤 타임아웃으로 멈춘다.

이 경우 명령 오도메트리와 EKF의 위치가 모두 증가할 수 있다. IMU 가속도 0만으로 “속도 0”을 알 수 없다는 한계를 설명하는 실험이다.

### 8.2 가속도 사용 설정과 비교

실습 launch를 종료하고 use_acceleration=true로 재실행한다.

```bash
ros2 launch my_quadruped_bot ekf_lab.launch.py \
  use_acceleration:=true command_topic:=/ekf_lab/cmd_vel \
  scale:=1.0 noise_stddev:=0.0 angular_noise_stddev:=0.0
```

같은 절차로 `/tmp/ekf_accel.csv`에 기록한다. 각 실험에서 전체 노드 상태를 새로 시작하고 동일한 입력·안정화 시간을 사용한다. 기존 Gazebo에 실제 외란이 있었다면 초기 조건도 맞춘다. 두 실행 결과가 반드시 달라지거나 개선될 것이라고 가정하지 않는다.

### 8.3 실제 저속 주행 비교는 선택 실험

격리 토픽 대신 기본 command_topic=/cmd_vel로 실습을 재시작한다. 기존에 검증한 낮은 속도·짧은 구간에서 명령하고, 종료 시 영속도 명령으로 실제 정지를 확인한다. 기본 제어기에는 명령 단절 시 watchdog이 없다는 점을 유의한다.

10 m 주행이나 강한 외란부터 시작하지 않는다. scale를 바꾸는 실험과 물리 마찰을 바꾸는 실험은 별도로 수행하여 원인을 구분한다.

## 9. CSV 그래프·수치

기록 종료 후:

```bash
python3 Ch11/scripts/plot_ekf_lab.py /tmp/ekf_baseline.csv --output /tmp/ekf_baseline.png
python3 Ch11/scripts/plot_ekf_lab.py /tmp/ekf_accel.csv --output /tmp/ekf_accel.png
```

출력은 상대 평면 궤적, 시간별 위치 오차, Raw·EKF의 RMSE다. *.metrics.json에 수치도 저장한다.

기록기는 /ekf_lab/filtered 시각에 가장 가까운 raw·Gazebo 샘플을 최대 0.05초 차이까지 짝맞춘다. 세 궤적을 첫 짝맞춤 포즈의 위치·yaw 기준으로 각각 정렬한다. **이는 초기 절대 위치 오차를 제거한 상대 평면 오차 비교이며 정밀 동시 측정은 아니다.** CSV에 시각 차이도 기록한다.

메시지가 부족하거나 시각 역행이 있으면 비교 CSV를 만들지 않는다. 실제 기록 없이 예시 데이터를 EKF 실행 결과처럼 그리지 않는다.

결과가 나빠졌다면 실패를 숨기지 않는다. 가속도 오차·중력 제거·초기 자세·공분산 가정·독립 관측 부족을 조사한다. 그래프가 부드러워진 것과 실제 위치 오차 감소는 다른 기준이다.

## 10. 검증 범위

신규 검사는 명령 적분·계수·재현 가능한 잡음·수신 타임아웃·시각 점프·공분산·격리 토픽·TF 설정을 검사한다. 기존 관측 기반 기본 설정도 유지되는지 확인한다.

- 수정 전: 신규/계약 검사 11개 중 10 FAIL, 기존 기본 설정 계약 1 PASS
- 수정 후: 11 PASS
- 전체: 61개 실행, 55 PASS, 기존 ROS/Gazebo 의존 6 SKIP
- Python·YAML·문서 Bash 문법 검사
- 새 ROS 노드·실제 robot_localization 실행·WSL2/Gazebo 비교 측정: **현재 환경에서 미수행**

이 회귀 검사들은 robot_localization의 EKF 수학 구현이나 실제 추정 성능을 테스트한 것이 아니다. 실제 기록 CSV와 런타임 로그가 있어야 해당 실험 결과를 판단할 수 있다.

## 11. 공식 참고 자료

- [센서 구성·중복 관측](https://github.com/cra-ros-pkg/robot_localization/blob/rolling-devel/doc/configuring_robot_localization.rst)
- [중력 제거·상태 추정 설정](https://github.com/cra-ros-pkg/robot_localization/blob/rolling-devel/doc/state_estimation_nodes.rst)
- [IMU 좌표·데이터 준비](https://github.com/cra-ros-pkg/robot_localization/blob/rolling-devel/doc/preparing_sensor_data.rst)

외부 rolling-devel 문서는 개념 참고용이며 실제 설치한 Jazzy 버전과 함께 대조한다.
