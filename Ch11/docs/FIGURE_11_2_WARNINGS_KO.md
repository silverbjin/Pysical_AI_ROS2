# Figure 11-2 센서·TF 경고 해설과 수정

검증일: 2026-10-17. ROS 2 Jazzy / Gazebo Harmonic, ros_gz_bridge 1.0.22.

## 로그의 의미

| 로그 | 의미와 처리 |
|---|---|
| `gz_frame_id ... not defined in SDF` | Harmonic 센서가 읽는 Gazebo 전용 확장 태그지만 표준 SDF 스키마에는 없어 경고가 출력됐다. 태그를 제거하고 ROS 브리지의 토픽별 `frame_id`로 옮겼다. |
| `Waiting for timestamp-matched ... TF` 반복 | 100 Hz IMU의 새 샘플이 30 Hz EKF TF보다 먼저 도착할 수 있다. 실제로 자세가 계속 출력되는데도 잠깐의 대기마다 WARN을 출력하던 것이 원인이었다. 정상 대기는 DEBUG로 바꿨다. |
| `time 0.002 ... earlier than ... transform cache` | 첫 스캔의 측정 시각이 최초 EKF TF보다 이르므로 RViz가 해당 스캔을 버렸다. 초기 한 번의 손실은 정상 초기화 과정이며 이후 스캔까지 실패하는지 따로 확인해야 한다. |
| `Passing message ... Float64 ... Double` | 관절 명령을 ROS에서 Gazebo로 변환했다는 최초 1회 INFO다. 오류가 아니다. |

## 코드 변경

- `urdf/common/gazebo_control.xacro`: 두 센서의 `<gz_frame_id>` 제거.
- `config/ros_gz_bridge.yaml`: IMU에 `frame_id: base_link`, LiDAR에 `frame_id: lidar_link` 설정. 센서 장착 위치와 회전은 기존 URDF/SDF를 유지한다. 이 설정은 좌표 변환을 수행하는 것이 아니라 실제 장착에 대응하는 ROS 헤더 이름을 지정한다.
- `my_quadruped_bot/imu_pose_viz.py`: 짧은 대기는 DEBUG. **시뮬레이션 0.5초**를 넘긴 샘플이 버려지고 최근 자세 출력도 없으면 WARN을 출력한다. TF가 실제로 끊기면 경고가 유지된다. 측정 시각은 그대로 사용하며 최신 TF로 대체하거나 임의 시각을 넣지 않는다.
- 테스트: 실제 tf2 Buffer로 대기 후 보간, 최초 TF 부재, 정상 출력 중 오래된 입력 폐기, 정상 출력 후 TF 단절을 검사한다. SDF 변환 시 비표준 태그 경고가 없는지도 검사한다.

## 확인 결과

수정 전 관측에서는 실제 시간 12초에 IMU 502개, 표시 자세 143개가 수신됐다. IMU 도착 즉시 TF를 조회하면 495회가 미래 시각 외삽 대기였다. 이는 TF 단절이 아니라 EKF가 다음 TF를 발행하기 전의 짧은 대기였다.

전체 **38개 테스트가 skip 없이 통과**했다. 수정 전에는 SDF 경고 검사와 짧은 대기 경고 검사 등이 실패했다. 중간 보간 테스트의 5e-8 m 차이는 나노초 시각 반올림에 따른 수치 오차로 확인하고, 위치 허용 오차를 1e-6 m로 명시했다.

실제 기본 실행에서도 비표준 SDF 태그 경고와 반복되는 TF 대기 WARN이 사라졌다. 시작할 때 TF가 아직 없는 초기 샘플의 만료 WARN 1회와 RViz의 시각 0.002초 스캔 폐기 INFO 1회는 남았고, 이후 반복되지 않았다.

TF 준비 이후 검사에서 스캔 45개 모두 측정 시각의 TF 조회에 성공했고 만료는 0개였다. 최대 TF 대기는 실제 시간 약 0.063초였다. 같은 관측에서 IMU 514개와 표시 자세 166개를 수신했으며, 프레임은 각각 `base_link`, `odom`, 스캔은 `lidar_link`였다.

최초 검증 프로브는 실행 중인 시뮬레이터에 새 TF 구독자로 합류하자마자 모든 스캔을 평가하여, 자기 버퍼에 과거 TF가 없는 초기 스캔 7개를 만료로 기록했다. 이 검사 결과는 FAIL로 보존했다. 다음 검사는 TF를 처음 받은 뒤 실제 시간 2초의 버퍼 준비 구간을 명시적으로 제외하고, 이후 스캔을 원래 측정 시각으로 변환할 수 있는지 확인했다. 로그를 숨기거나 센서 시각을 덮어써서 통과시킨 것이 아니다.

증거: [경고 검증 로그와 수치](../evidence/figure_11_2_warnings_20261017/).

## 재실행과 Nav2 연결

기존 실행을 종료한 뒤 저장소 루트에서 다음 명령으로 빌드와 실행을 함께 수행한다.

```bash
bash Ch11/scripts/run_figure_11_2.sh
```

직접 실행할 때는 변경된 workspace를 빌드하고 source한다.

```bash
source /opt/ros/jazzy/setup.bash
cd Ch11/ros2_ws
colcon build --symlink-install --packages-up-to my_quadruped_bot
source install/setup.bash
ros2 launch my_quadruped_bot figure_11_2.launch.py
```

Nav2에서 중요한 것은 경고 문자열의 유무보다 측정 시각에 유효한 TF와 실제 센서 수신이다. 현재 구성은 `odom → base_footprint → base_link → lidar_link`를 제공한다. Nav2 통합 시에는 AMCL 또는 SLAM이 제공하는 `map → odom`과 관련 노드의 `use_sim_time: true`가 추가로 필요하다. `map → odom`을 임의의 고정 TF로 대체하지 않는다. 이번 작업은 센서·TF 경로를 검사했으며 Nav2 전체 주행을 실행·보증한 것은 아니다.

근거:

- [ros_gz Jazzy 토픽별 frame_id 파싱 구현](https://github.com/gazebosim/ros_gz/blob/jazzy/ros_gz_bridge/src/bridge_config.cpp)
- [Gazebo Sensors 8의 gz_frame_id 처리 구현](https://github.com/gazebosim/gz-sensors/blob/gz-sensors8/src/Sensor.cc)
- [Nav2 Jazzy TF 구성 안내](https://ros-navigation.github.io/mkdocs.nav2.org/jazzy/configuration_and_development/first_time_robot_setup_guide/transformation/setup_transforms/)
