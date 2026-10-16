# Figure 11-2 실행 디버깅 보고서

검증일: 2026-10-17 (KST)  
실행 위치: `/home/jinho/Pysical_AI_book`

## 1. 결과

요청한 `bash Ch11/scripts/run_figure_11_2.sh`를 실제 WSL2 환경에서 실행했다. 최초 실행에서는 빌드는 성공했으나 Gazebo가 로봇을 생성하지 못했다. 모델을 복구한 뒤에는 로봇이 뒤집히는 추가 문제를 확인했다. 루트 링크 관성과 FSM의 기구학 매핑을 수정한 후 같은 명령으로 재실행하여 로봇 기립, LiDAR·IMU·자세 토픽, 오도메트리와 TF 수신을 확인했다.

Ch11 회귀 테스트는 **23개 모두 통과**했고, 별도 컨트롤러 SIGINT 종료 검사도 종료 코드 0이었다. 실행 스크립트 자체는 변경할 필요가 없었으며, 스크립트가 불러오는 모델과 제어기를 수정했다.

## 2. 실행 환경과 검증 방법

| 항목 | 확인값 |
|---|---|
| OS | Ubuntu 24.04.4 LTS, WSL2 |
| 커널 | `6.18.40.1-microsoft-standard-WSL2` |
| ROS | Jazzy (`/opt/ros/jazzy/setup.bash`) |
| Gazebo | Harmonic / Sim 8, `ros-jazzy-gz-sim-vendor` 0.0.10 |
| ros_gz_sim | 1.0.22 |
| RViz2 | 14.1.24 |
| robot_localization | 3.8.3 |
| GUI 환경 | `DISPLAY=:0`, `WAYLAND_DISPLAY=wayland-0` |

기존 시뮬레이터 프로세스가 없는 상태에서 기본 옵션으로 실행했다. `colcon` 빌드, launch 로그, `gz sdf -p` 변환, 실제 ROS 구독, TF 조회를 각각 확인했다. 처음 진단 스크립트를 빌드 완료 전에 실행했을 때 노드와 `/clock`이 없었던 것은 관측 시점 문제였으므로, 시작 완료 후 다시 검사했다.

## 3. 현상·원인·해결

### 3.1 빌드는 성공하지만 Gazebo 로봇이 생성되지 않음

최초 실행 로그에 다음 오류가 발생했다.

```text
link[base_footprint] has no <inertial> block defined
child joints ignored
child links ignored
A model must have at least one link.
```

뒤이어 `base_link`, 다리 및 LiDAR 프레임을 찾을 수 없다는 오류도 발생했다. `create` 노드는 `Entity creation successful`을 출력했지만, Gazebo 서버의 모델 변환은 실패했다. 따라서 이 메시지만으로 스폰 성공을 판단할 수 없었다.

원인은 `robot.urdf.xacro`에서 루트 링크 `base_footprint`의 관성 블록이 주석 처리된 상태로 `base_footprint_joint`의 `preserveFixedJoint=true`가 유지된 것이었다. 독립적으로 Xacro를 URDF로 변환하고 `gz sdf -p`를 실행해도 같은 실패를 재현했다.

기존에 준비되어 있던 질량 `0.0001 kg`, 대각 관성 `0.000001 kg·m²` 블록을 복구했다. 물리 몸체 `base_link`와 기존 TF 구조는 유지했다. 실제 SDF 변환의 성공 코드와 몸체·네 다리·IMU·GPU LiDAR 보존 여부를 검사하는 회귀 테스트를 추가하여 수정 전 실패, 수정 후 통과를 확인했다.

### 3.2 생성 후 로봇이 뒤집힘

모델 생성만 수정한 실행에서는 IMU quaternion의 `y ≈ 0.995`, 몸체 높이 약 `0.133 m`가 관찰됐다. TF에서는 roll이 약 180°로 나타나 로봇이 뒤집힌 상태임을 확인했다.

제어기와 실제 URDF를 비교한 결과 다음 불일치가 있었다.

| 항목 | 기존 FSM/IK | 실제 Ch11 URDF |
|---|---|---|
| 허벅지·종아리 길이 | 각각 0.20 m | 각각 0.25 m |
| 몸체→고관절 Y 오프셋 | ±0.15 m | ±0.10 m, 이후 허벅지 연결부에 ±0.05 m |
| 허벅지 고정 원점 회전 | 미반영 | +1.2 rad |
| 종아리 고정 원점 회전 | 미반영 | −2.4 rad |

일반 IK가 반환한 기하학적 각도를 그대로 관절 명령으로 보냈기 때문에, 초기 목표에서도 허벅지 명령 `−1.111 rad`가 URDF 하한 `−1.0 rad`를 벗어났다. 실제 다리 형상 역시 목표 발 위치와 달랐다.

`trot_controllerFSM.py`에서 Ch11 다리 길이를 0.25 m로 설정하고 고관절 오프셋을 맞췄다. 동일 길이 링크의 반대 무릎 해를 선택한 뒤 URDF 고정 회전을 빼도록 명령을 `[q1, −q2−1.2, −q3+2.4]`로 매핑했다. IK 실패 시에는 URDF 초기 웅크림 자세인 `[0, 0, 0]`을 사용하도록 했다.

새 회귀 테스트는 실제 Xacro를 전개한 URDF에서 연결 위치·원점 회전·관절 제한을 읽어 순기구학을 계산한다. 네 다리 모두 준비 높이 0.18 m 및 기립 높이 0.25 m에서 발 위치가 목표와 `1e-6 m` 이내로 일치하고 명령이 관절 제한 안에 들어가는지 검사한다. 수정 전 실패, 수정 후 통과했다.

### 3.3 Ctrl+C 종료 시 ROS context 중복 종료

최초 실행을 종료할 때 FSM에서 다음 예외가 발생했다.

```text
rclpy._rclpy_pybind11.RCLError: failed to shutdown:
rcl_shutdown already called on the given context
```

SIGINT 처리로 ROS context가 이미 종료된 뒤 `finally`에서 `rclpy.shutdown()`을 다시 호출한 것이 원인이었다. `rclpy.ok()`일 때만 shutdown하도록 수정했다. 종료 로그도 같은 조건에서 출력해, 이미 무효화된 rosout publisher로 로그를 보내는 현상을 방지했다. 수정 후 별도 ROS domain에서 컨트롤러를 실행하고 SIGINT를 보내 종료 코드 0을 확인했다.

검사 도중 준비 로그를 읽자마자 신호를 보내는 초기 종료 프로브는 생성자가 반환하기 전에 `KeyboardInterrupt`를 발생시켰다. 이 프로브는 정상 실행 중 종료 검사로 사용할 수 없어, 노드가 초기화된 후 신호를 보내도록 관측 절차를 수정했다.

## 4. 최종 실제 실행 검증

기본 Gazebo·RViz·FSM 옵션으로 재실행했으며, 두 패키지 빌드가 성공했다. 실행 중 별도 검증 노드가 ROS 토픽을 동시에 구독했다. 약 20.86초의 실제 관측 동안 시뮬레이션 시각 18.005초까지 확인했다.

| 검사항목 | 측정 결과 |
|---|---|
| `/clock` | 7,278개 수신 |
| `/scan` | 102개 수신, `lidar_link` |
| LiDAR 최신 거리값 | 360개 중 360개 유효, 약 1.494~4.859 m |
| `/imu/data_raw` | 1,027개 수신, `base_link` |
| `/figure_11_2/imu_pose` | 301개 수신, `odom` |
| `/odom` | 295개 수신 |
| `/joint_states` | 7,378개 수신, 메시지 내 관절 13개 |
| 몸체 위치 | 약 (−0.0219, 0, 0.2496) m |
| 기립 후 최대 roll/pitch 절댓값 | 약 1.131° (시뮬레이션 8초 이후 관측 샘플) |
| `odom → base_link` | 조회 성공, z≈0.2496 m |
| `odom → lidar_link` | 조회 성공, z≈0.3596 m |

회귀 검증 명령:

```bash
source /opt/ros/jazzy/setup.bash
python3 -m unittest discover -s Ch11/tests -v
bash -n Ch11/scripts/run_figure_11_2.sh Ch11/scripts/check_figure_11_2.sh
```

23개 테스트가 skip 없이 통과했고 Bash 문법 검사도 성공했다. ROS가 없는 환경에서는 실제 변환·기구학 검사가 일부 skip되므로, 동일한 검증을 위해 ROS 환경을 source해야 한다.

## 5. 경고 및 검증 범위

- `gz_frame_id`가 표준 SDF 요소가 아니라는 경고는 남는다. 변환기가 확장 요소를 보존했고, 실제 ROS 메시지에서 IMU=`base_link`, LiDAR=`lidar_link`를 확인했다.
- IMU 시각과 일치하는 TF를 기다리는 경고가 관찰 중에도 주기적으로 출력됐다. `/figure_11_2/imu_pose`가 계속 수신되는 것을 확인했으며, TF 지연을 대신할 가짜 자세는 추가하지 않았다.
- RViz가 시각 0.002초의 초기 스캔을 TF 캐시보다 오래된 메시지로 한 번 버렸다. 이후 센서와 TF 수신은 정상이다.
- TF 진단 프로세스가 시작 직후 `odom`을 아직 발견하지 못했다는 로그를 출력한 뒤 정상 변환을 출력했다. `tf2_echo`는 지속 실행 명령이라 진단 스크립트의 종료 코드 124는 정해진 관측 시간 종료를 뜻한다.
- Ctrl+C 시 Gazebo의 Ruby 실행 래퍼가 `exit code -2`로 기록됐다. 사용자 신호에 따른 종료였고, 최종 종료 후 Gazebo·RViz·ROS launch 잔여 프로세스는 없었다. 중간 실행 종료에서는 IMU 노드의 메시지 수신 중 RuntimeError가 한 번 있었으나 최종 전체 실행 종료에서는 재현되지 않았다.
- Gazebo와 RViz 프로세스 시작 및 RViz OpenGL 초기화는 로그로 확인했다. WSLg 창의 자동 캡처는 검은 화면으로 반환되어 실제 화면 구성의 육안 검증 및 출판용 PNG 제작은 완료로 간주하지 않았다.
- 이번 검증은 무속도 명령의 기립과 센서 시각화 데이터 경로를 대상으로 한다. 보행·외란 회복·실물 로봇 성능을 검증한 것은 아니다.

## 6. 변경 파일과 증거

- 모델 수정: `Ch11/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro`
- 기립 및 종료 수정: `Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_controllerFSM.py`
- 회귀 테스트: `Ch11/tests/test_figure_11_2.py`

증거 디렉터리: [`Ch11/evidence/figure_11_2_debug_20261017`](../evidence/figure_11_2_debug_20261017/)

- [최초 실행 오류](../evidence/figure_11_2_debug_20261017/initial_launch.log)
- [SDF 변환 회귀 테스트의 수정 전 실패](../evidence/figure_11_2_debug_20261017/sdf_regression_red.log)
- [기구학 회귀 테스트의 수정 전 실패](../evidence/figure_11_2_debug_20261017/kinematics_red.log)
- [최종 테스트 23개 통과](../evidence/figure_11_2_debug_20261017/regression_green.log)
- [최종 실행 및 종료 로그](../evidence/figure_11_2_debug_20261017/final_launch.log)
- [최종 토픽·TF 진단](../evidence/figure_11_2_debug_20261017/final_diagnostics.log)
- [실제 구독 검증 수치](../evidence/figure_11_2_debug_20261017/runtime.json)
- [수정 후 컨트롤러 SIGINT 종료](../evidence/figure_11_2_debug_20261017/controller_shutdown.log)

작업 시작 전부터 존재한 colcon build/install/log 및 pycache 변경은 보존했다. 커밋이나 브랜치 변경은 수행하지 않았다.
