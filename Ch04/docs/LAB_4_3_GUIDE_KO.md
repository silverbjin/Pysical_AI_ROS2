> 개정(2026-10-21): 실제 ROS 시간 기준의 원운동 `angular_speed=1.5 rad/s`, `timer=1/30 s`로 개선했다. 아래 예측값은 새 소스 기준이다.

# 4.3절 실습 가이드: 2m 원운동 TF 방송

## 학습 목표

고정 TF와 달리 `/tf`가 시간에 따라 변한다는 사실을 확인하고, 위치·방향·시간·주파수 계약을 점검한다. `world→turtle_frame`은 **가상의 프레임**이며 로봇 모델이나 Path 시각화는 제공하지 않는다.

## 1. 빌드·환경

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_ROS2/Ch04/ros2_ws # 실제 clone 위치에 맞게 수정
rosdep install --from-paths src --ignore-src -r -y
colcon build --packages-select my_robot_tf --symlink-install
source install/setup.bash
ros2 pkg executables my_robot_tf
```

## 2. 실행 (터미널 1)

```bash
ros2 run my_robot_tf dynamic_tf_broadcaster
```

타이머는 1/30초(명목 30Hz)이고, 각도는 실제 ROS 시간 간격 `dt`와 각속도 `1.5 rad/s`를 곱해 갱신한다. 한 바퀴 시간은 약 4.19초다(이론값). 지연이 과도하면 `dt`는 최대 0.25초로 제한하며 /clock 역행 시 이번 콜백은 건너뛴다. 이 값들은 예측값이며 실측 결과가 아니다.

## 3. 확인 (터미널 2)

```bash
source /opt/ros/jazzy/setup.bash
ros2 topic list -t
ros2 topic hz /tf
ros2 run tf2_ros tf2_echo world turtle_frame
```

- `/tf`가 존재하고 갱신된다.
- `tf2_echo`의 x,y가 변하며 `x²+y²≈4.0 m²`.
- 좌표는 반경 2m를 유지하고, z는 0이다.
- quaternion은 정규화돼 있으며 x,y는 0 근처, z,w는 회전에 따라 변한다.
- 출력 주기는 CPU 부하·DDS 환경에 따라 이상적인 약 30Hz에서 차이가 날 수 있다.

## 4. RViz 시각화 (터미널 3)

```bash
rviz2
```

Global Options → Fixed Frame `world`, Add → TF, Show Axes/Names 활성화. `turtle_frame` 축이 world 원점을 중심으로 원주를 이동하는지 관찰한다. TF 표시만으로 이동 경로의 지속적인 흔적(Path)은 자동으로 그려지지 않는다. 경로 궤적선을 원한다면 별도 `nav_msgs/Path` 발행 또는 Marker 노드를 구현해야 한다.

## 5. 원리 확인과 응용

원의 접선 속도를 `(-2ωsinθ, 2ωcosθ)`로 유도한다. `yaw=θ+π/2`는 접선 방향을 나타낸다. 선속도 크기 기대값은 `2×1.5=3.0 m/s`. **단순 가상 프레임 이동 속도**이지 로봇 액추에이터 속도가 아니다.

**응용:** 소스의 `radius`와 `timer_period`를 바꾸어 반경·업데이트 주기 변화에 대한 관찰 결과를 기록한다. 한 번에 하나의 변수만 조정한다. 시간 정확도가 중요하면 `dt=(현재 ROS 시간-이전 ROS 시간)`와 `θ+=ωdt`로 바꾸는 개선을 설계한다(현재 코드는 실측 dt).

## 6. 실패 진단 / Acceptance

| 증상 | 점검 |
|---|---|
| `turtle_frame`을 찾지 못함 | 방송 노드 실행, 다른 ROS_DOMAIN_ID 여부 |
| TF가 갱신되지 않음 | `ros2 topic hz /tf`, 노드 로그, CPU 및 시뮬레이션 시계 |
| RViz에서 좌표축 안 보임 | Fixed Frame `world`, TF Display 체크 |
| 역방향 값이 기대와 다름 | `tf2_echo world turtle_frame`과 `tf2_echo turtle_frame world`은 서로 역변환 |

결과물은 실행 OS, ROS 버전, 주파수 측정값, 대표 `tf2_echo` 출력, RViz 화면 및 실패 로그다. 보고서 [SECTION_4_3_REPORT_KO.md](SECTION_4_3_REPORT_KO.md)에 근거를 반영한다.
