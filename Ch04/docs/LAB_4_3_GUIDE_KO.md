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

타이머는 0.033s로 약 30.3Hz이고 `theta`는 콜백마다 0.05rad 증가한다. 따라서 타이머가 이상적으로 실행될 때 회전 한 바퀴에 `2π/0.05≈126`회 갱신이 필요하다. 이는 **기대 계산값**이며 실측 결과가 아니다.

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

원의 접선 속도를 `(-2ωsinθ, 2ωcosθ)`로 유도한다. `yaw=θ+π/2`는 접선 방향을 나타낸다. 선속도 크기 기대값은 `2×(0.05/0.033)≈3.03 m/s`. **단순 가상 프레임 이동 속도**이지 로봇 액추에이터 속도가 아니다.

**응용:** 소스의 `radius`와 `timer_period`를 바꾸어 반경·업데이트 주기 변화에 대한 관찰 결과를 기록한다. 한 번에 하나의 변수만 조정한다. 시간 정확도가 중요하면 `dt=(현재 ROS 시간-이전 ROS 시간)`와 `θ+=ωdt`로 바꾸는 개선을 설계한다(현재 코드는 고정 증분).

## 6. 실패 진단 / Acceptance

| 증상 | 점검 |
|---|---|
| `turtle_frame`을 찾지 못함 | 방송 노드 실행, 다른 ROS_DOMAIN_ID 여부 |
| TF가 갱신되지 않음 | `ros2 topic hz /tf`, 노드 로그, CPU 및 시뮬레이션 시계 |
| RViz에서 좌표축 안 보임 | Fixed Frame `world`, TF Display 체크 |
| 역방향 값이 기대와 다름 | `tf2_echo world turtle_frame`과 `tf2_echo turtle_frame world`은 서로 역변환 |

결과물은 실행 OS, ROS 버전, 주파수 측정값, 대표 `tf2_echo` 출력, RViz 화면 및 실패 로그다. 보고서 [SECTION_4_3_REPORT_KO.md](SECTION_4_3_REPORT_KO.md)에 근거를 반영한다.

---

## 4.3 실제 ROS /tf의 원운동 검수 (공개 CI)

기존 Ch04 4.2 정적 TF의 PASS는 보존하고 반복 실행하지 않는다. 이번 검수는 원본 dynamic_tf_broadcaster를 직접 실행하여 world→turtle_frame의 실제 메시지 35개 이상에서 다음을 확인한다: 원운동 반경 2.0m±0.02m, 좌표 x/y 변화폭 각각 0.5m 이상, quaternion 정규화 오차 <=0.001, yaw가 궤적 접선 방향과 0.015rad 이내, 중복되지 않는 nonzero stamp 35개 이상.

실행기: ci/ch04_43_44_tf_once.sh / 관찰기: ci/ch04_43_44_tf_probe.py / 공개 워크플로: .github/workflows/book-ch04-43-44-dynamic-tf.yml.

실제 CI 로그에 CH04_43_REAL_2M_CIRCULAR_TF_AND_TANGENT_YAW_PASS가 표시되고, 독립 receipt와 종료코드가 모두 통과한 경우에만 scoped PASS다. CI에서 GUI, 실제 로봇, Gazebo, 정적 TF 재시험은 수행하지 않는다. Ch10 HOLD.
