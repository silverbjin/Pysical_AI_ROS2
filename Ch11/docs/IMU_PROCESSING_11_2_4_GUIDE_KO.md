# 11.2.4 IMU 데이터 처리 노드 실습

- 기준: main `e3574207300f5ca11868243e70e60bc27baf00c0` (figure 11-2 debug)
- 반영 브랜치: `feat/ch11-imu-processing`
- 환경: Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic / 시스템 Python 3.12
- 새 입력: 가속도와 각속도만 사용한다. 입력 Imu.orientation은 읽지 않는다.
- 입력 토픽: `/imu/data_raw` (sensor_msgs/msg/Imu)
- 출력 토픽: `/imu/rpy_filtered` (std_msgs/msg/Float32MultiArray)
- 출력 순서·단위: `[roll, pitch, yaw]`, **rad**

## 1. 이번에 적용한 파일

my_quadruped_bot 패키지 아래:

```text
my_quadruped_bot/
├── sensors/
│   ├── __init__.py
│   ├── complementary_filter.py   # 수식·시각 처리, ROS 없이 검사 가능
│   └── imu_processor.py          # 원고의 ROS 2 구독·발행 노드
└── imu_processor.py              # 이전 import 경로를 위한 호환 모듈
launch/
└── imu_processing.launch.py      # 센서 처리 노드만 실행
setup.py                         # 실행 항목을 sensors.imu_processor:main으로 연결
```

원고의 `~/ros2_ws`는 예시 경로다. 이 저장소의 실제 워크스페이스는 `Ch11/ros2_ws`다.

새 sensors 디렉터리에 __init__.py를 넣어 setup.py의 find_packages가 하위 패키지를 설치하도록 했다. 기존 실행 이름을 유지하여 ch11_bringup.launch.py에서도 새 구현을 사용한다.

## 2. 원고 예제와 달라진 부분

| 원고 예제 | 패키지 적용 |
|---|---|
| /imu/data 구독 | 실제 브리지 출력 /imu/data_raw 구독 |
| 콜백 도착 시각 차이 | msg.header.stamp의 센서 획득 시각 차이 |
| 0으로 시작하는 자세 | 첫 유효 가속도에서 roll/pitch 초기화, yaw=0 |
| 같은 시각 또는 역행 처리 없음 | 같은 stamp는 무시, 역행 시 새 시각 구간으로 재초기화 |
| 수신 단절 동안 큰 dt 적분 | max_dt 초과 시 roll/pitch 재초기화·yaw=0 |
| 각도 경계 미처리 | ±π의 최단 각도 차이로 roll/pitch 보정, yaw 정규화 |
| 센서 유효성 미처리 | 미제공(-1 covariance), NaN/Inf, 거의 0인 가속도 거부 |
| 종료 시 shutdown 반복 가능 | ROS context가 살아 있을 때만 shutdown |

원시 orientation_covariance[0]=-1이어도 가속도·각속도가 유효하면 처리한다. 이 실습은 orientation을 계산하는 과정이기 때문이다. 반면 가속도 또는 각속도의 covariance[0]=-1이면 해당 샘플을 사용하지 않는다. 공분산 전체가 0인 경우는 “오차 0”이 아니라 “미상”이므로 입력 자체를 거부하지 않는다.

## 3. 코드 받기와 빌드

저장소 위치에 맞게 첫 줄을 수정한다. 가상환경·Conda를 해제한 새 WSL 터미널에서 진행한다.

```bash
cd ~/Pysical_AI_ROS2_publish
git status --short
git fetch origin
git switch --track origin/feat/ch11-imu-processing
source /opt/ros/jazzy/setup.bash
cd Ch11/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 pkg executables my_quadruped_bot
```

브랜치가 이미 있으면 `git switch feat/ch11-imu-processing`을 사용한다. rosdep 최초 사용자는 먼저 `sudo rosdep init`, `rosdep update`가 필요하다.

실행 목록에서 imu_processor를 확인한다. 추가적인 SciPy·tf_transformations 설치는 필요 없다. 이 브랜치는 main의 기존 파일을 그대로 기준으로 삼으며 이전 그림 브랜치로 되돌아가지 않는다.

## 4. Gazebo 센서 실습

각 새 터미널에서 다음 환경을 준비한다.

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2_publish/Ch11/ros2_ws
source install/setup.bash
```

### 터미널 1: 기존 센서 시각화 실행

```bash
ros2 launch my_quadruped_bot SLAM_simulation.launch.py
```

이 launch는 Gazebo·RViz·기립 제어·센서·EKF를 실행하며 이번 필터 노드는 실행하지 않는다. 기립과 센서 수신을 확인한 뒤 터미널 2를 실행한다.

GUI가 필요 없는 데이터 경로 점검에는 simulation.launch.py를 대신 사용할 수 있다. 다만 이 launch만 실행하면 FSM이 기립을 유지하지 않으므로 넘어져 있는 로봇의 자세를 측정할 수 있다.

### 터미널 2: 11.2.4 처리 노드 실행

```bash
ros2 launch my_quadruped_bot imu_processing.launch.py alpha:=0.98
```

또는 같은 노드를 직접 실행한다. 두 명령 중 하나만 사용한다.

```bash
ros2 run my_quadruped_bot imu_processor --ros-args \
  -p use_sim_time:=true -p alpha:=0.98 -p max_dt:=0.2
```

### 터미널 3: 메시지와 계산 결과 확인

```bash
ros2 interface show sensor_msgs/msg/Imu
ros2 topic echo /imu/data_raw --once --qos-reliability best_effort
ros2 topic echo /imu/rpy_filtered
```

data[0], data[1], data[2]는 각각 roll, pitch, yaw다. 예를 들어 0.1 rad는 약 5.73°다. 측정값은 실제 실행 자세에 따라 달라지므로 고정 숫자를 정상 기준으로 삼지 않는다.

`ch11_bringup.launch.py`를 사용하면 필터 노드도 포함되므로 별도 imu_processing.launch.py를 중복 실행하지 않는다.

### 선택: 시간 그래프

```bash
sudo apt install -y ros-jazzy-rqt-plot
ros2 run rqt_plot rqt_plot \
  '/imu/rpy_filtered/data[0]' \
  '/imu/rpy_filtered/data[1]' \
  '/imu/rpy_filtered/data[2]'
```

필요하면 rqt_plot GUI의 Topic 입력란에서 위 경로를 하나씩 추가한다. 세로축 단위는 rad다. 정지 중 기울기, 보행 중 흔들림, yaw 누적을 비교한다.

Figure 11-2의 기존 XYZ 축은 **Gazebo가 제공한 orientation**으로 만든 표시다. 이번 /imu/rpy_filtered 그래프와 자료원이 다르다. 이 변경은 그림의 축을 필터 출력으로 바꾸거나 EKF 입력을 교체하지 않는다.

## 5. Gazebo 없이 계산을 확인하는 두 샘플 실습

아래는 별도 /lab 토픽의 **합성 입력**이다. 실제 로봇 제어 명령을 발행하지 않는다. 각 터미널에서 ROS·워크스페이스 환경을 source한다.

### 터미널 A: 격리된 필터

```bash
ros2 launch my_quadruped_bot imu_processing.launch.py \
  use_sim_time:=false input_topic:=/lab/imu output_topic:=/lab/rpy
```

### 터미널 B: 결과 관찰

```bash
ros2 topic echo /lab/rpy
```

### 터미널 C: 0.1초 차이의 두 센서 샘플 전송

```bash
ros2 topic pub --once /lab/imu sensor_msgs/msg/Imu \
  "{header: {stamp: {sec: 1, nanosec: 0}, frame_id: base_link}, angular_velocity: {z: 1.0}, linear_acceleration: {z: 9.81}, orientation_covariance: [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"
ros2 topic pub --once /lab/imu sensor_msgs/msg/Imu \
  "{header: {stamp: {sec: 1, nanosec: 100000000}, frame_id: base_link}, angular_velocity: {z: 1.0}, linear_acceleration: {z: 9.81}, orientation_covariance: [-1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]}"
```

기대 결과:

| 샘플 | 센서 시각 | 출력 |
|---|---:|---|
| 첫 번째 | 1.0초 | [0, 0, 0]으로 초기화 |
| 두 번째 | 1.1초 | [0, 0, 약 0.1] rad |

Yaw 계산은 1.0 rad/s × 0.1 s = 0.1 rad다. 두 CLI 명령 사이의 실제 벽시계 시간이 더 길어도 센서 stamp 차이로 계산한다.

같은 두 번째 메시지를 다시 보내면 stamp가 같으므로 출력이 추가되지 않는다. 첫 번째 메시지를 다시 보내면 시각 역행으로 판정하여 초기화한다. orientation 미제공(-1)인데도 계산되는 점을 확인한다.

## 6. 필터 수식과 해석

첫 유효 입력에서:

```python
roll_acc = math.atan2(ay, az)
pitch_acc = math.atan2(-ax, math.hypot(ay, az))
```

연속 입력의 작은 각도 구간에서 다음 관계를 적용한다.

```python
roll_pred = roll + gx * dt
roll = alpha * roll_pred + (1.0 - alpha) * roll_acc
yaw = yaw + gz * dt
```

실제 코드는 각도 경계에서 다음과 같이 최단 각도 차이를 사용한다.

```python
roll = wrap_angle(roll_pred + (1.0 - alpha) * wrap_angle(roll_acc - roll_pred))
```

각도 경계를 넘지 않으면 원고 공식과 동일하다. alpha는 한 샘플 갱신에 적용되는 계수이므로 센서 주기를 바꾸면 필터 특성도 달라진다. 0.98을 모든 IMU에서 검증된 최적값으로 설명하지 않는다.

- alpha가 커지면 자이로 예측의 비중이 커지고 가속도 보정의 반영은 느려진다.
- alpha가 작아지면 가속도 기반 기울기를 빠르게 반영하지만 보행 충격의 영향도 커진다.
- alpha·max_dt는 시작 시 읽는 파라미터다. 비교하려면 노드를 종료하고 값만 바꿔 재실행한다.

## 7. 실습의 한계

1. 가속도계는 중력 방향뿐 아니라 몸체의 선형 운동·충격도 반영한다. 충격을 완전히 분리하거나 억제한 필터가 아니다.
2. gx/gy/gz를 각 Euler 각도에 직접 적분하는 것은 수평 근처의 작은 기울기·완만한 회전에 대한 교육용 근사다. 큰 복합 회전에는 일반적인 자세 추정 방식을 사용해야 한다.
3. yaw는 6축 센서만으로 절대 방위를 관측할 수 없다. 정규화는 각도 범위만 제한하고 드리프트를 없애지 않는다.
4. 0에 가까운 가속도(예: 자유낙하)는 중력 방향을 정할 수 없어 이 실습에서 샘플을 거부한다.
5. 수신 간격이 기본 0.2초를 넘으면 누락된 회전을 추정해낼 수 없어 자세를 재초기화하고 yaw를 0으로 재설정한다. 연속성이 끊기는 사건이다.
6. Float32MultiArray 출력에는 Header가 없다. 원고 호환·학습용으로 유지했으며, 실무 센서 융합 입력으로 그대로 사용하지 않는다.
7. 입력 센서 축의 방향이 일정하다는 전제다. 서로 다른 장착 프레임의 샘플을 같은 필터에 섞으면 안 된다.

## 8. 문제 확인과 테스트

```bash
ros2 node info /imu_processor
ros2 topic info /imu/data_raw -v
ros2 topic info /imu/rpy_filtered -v
ros2 param get /imu_processor use_sim_time
ros2 param get /imu_processor alpha
```

입력이 있는데 출력이 없으면 stamp가 고정되어 있지 않은지, 가속도·각속도가 미제공(-1)인지, /clock이 갱신되는지 확인한다. 출력 발행자가 둘 이상이면 필터 노드를 중복 실행했는지 점검한다.

ROS 없이 실행 가능한 수식 회귀 검사:

```bash
cd ~/Pysical_AI_ROS2_publish
python3 -m unittest discover -s Ch11/tests -p test_imu_processing.py -v
```

전체 검사는 ROS·Gazebo 설치 여부에 따라 기존 모델 변환·기구학 검사 일부가 skip될 수 있다.

## 9. 이번 변경의 검증 상태

- 신규 필터 검사: 11 FAIL(수정 전) → 11 PASS
- 전체 Ch11 검사: 34개 실행, 32 PASS, 기존 ROS/Gazebo 의존 검사 2 SKIP
- 문법·패키지 경로·launch 자료형 확인
- **이번 새 노드의 실제 ROS 빌드·WSL2/Gazebo 실행은 현재 환경에서 미수행**
- 기존 main의 Figure 11-2 디버깅 보고서는 이전 구현에 대한 실행 기록이며 새 필터의 실행 성공 증거로 사용하지 않는다.

검사 로그: Ch11/evidence/imu_processing_red.log, imu_processing_green.log.

공식 메시지 규약: https://github.com/ros2/common_interfaces/blob/jazzy/sensor_msgs/msg/Imu.msg
