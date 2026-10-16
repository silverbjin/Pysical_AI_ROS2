# [Project Context] 제12장 강화학습 기반 4족 보행 코드 리뷰

작성 기준: 2026-10-17 KST. 대상 독자: 공학부 3학년 이상 및 ROS 2·로봇 제어 실습 경험자.

이 문서는 새 대화·코드 리뷰 세션에 그대로 전달할 수 있는 인계 컨텍스트다. **Ch12의 환경·모델·학습 코드는 아직 구현한 것으로 간주하지 않는다.** 아래에서 기존 산출물, 재사용 후보, 신규 구현 제안, 실제 검증 결과를 구분한다.

## 1. 프로젝트와 이번 장의 목표

도서: **Physical AI 실무 가이드: ROS2로 구현하는 지능형 로봇 시스템 프로젝트**.

11장까지 기하학적 보행 제어, 센서 처리, 위치 추정, SLAM, 제한된 반응형 탐사 코드를 구성했다. 12장에서는 MuJoCo 또는 Gazebo에 **물리적으로 움직이는 4족 로봇의 강화학습 환경**을 만들고, 보행 및 목표 이동·장애물 회피 태스크를 학습·평가한다.

리뷰의 중심 질문은 다음과 같다.

1. 정책이 실제 관절·물리 동역학을 제어하는가?
2. 학습·평가 환경의 시간, 상태, 액션, 보상, 종료 조건이 일관적인가?
3. 성능 주장이 실제 로그·다중 평가 에피소드·물리 관측으로 뒷받침되는가?
4. 학습 모델이 Ch11의 FSM·ROS 통신·TF와 충돌 없이 연결되는가?
5. 독자가 환경 생성→검사→짧은 학습→저장→별도 평가를 재현할 수 있는가?

**명령 속도 적분으로 위치를 바꾸거나 로봇 몸체를 매 step 텔레포트하는 코드를 보행 학습으로 인정하지 않는다.** 장애물 회피 정책이 기존 FSM에 /cmd_vel만 주는 경우에는 ‘상위 이동 정책 학습’으로 표시하고, 관절 수준 보행 학습과 구분한다.

## 2. 페르소나와 리뷰 역할

### 2.1 주 리뷰어 — Senior Physical AI / Robotics Systems Engineer

20년 경력의 로봇 개발자·시스템 아키텍트·강사 관점으로 리뷰한다. ROS 2 Jazzy, Gazebo Harmonic, MuJoCo, Gymnasium, Stable Baselines3, 접촉 동역학과 정책 배포를 함께 검토한다.

- 단순 실행 성공보다 좌표계·단위·관절 매핑·제어권·시간 정합성을 우선한다.
- 학습 곡선 상승을 물리적으로 유효한 보행의 증거로 단정하지 않는다.
- 발 접촉·슬립·넘어짐·보상 편법을 코드와 에피소드 기록으로 확인한다.
- 원고의 교육적 단순화와 실제 구현의 한계를 함께 설명한다.
- 발견 항목은 파일·함수·재현 조건·영향·수정 방향으로 제시한다.

### 2.2 보조 검토 관점 — RL 실험·물리 모델·교육 재현성

별도 에이전트 사용을 지시하는 항목이 아니라, 한 리뷰에서도 적용할 관점이다.

| 관점 | 확인할 내용 |
|---|---|
| RL 실험 설계 | MDP/POMDP, 관측 누락·특권 정보, 보상 편법, 학습/평가 분리 |
| 물리·제어 | floating base, 관성, 접촉, actuator 의미, 관절 원점·한계, 시뮬레이터 차이 |
| 시스템 통합 | ROS clock, QoS, TF 소유권, 정책/FSM 제어권, watchdog, reset 동기화 |
| 강의·원고 | 독립 설치·실행, 코드와 설명의 일치, 실패 사례와 실제 증거 |

### 2.3 리뷰 대상 개발자

10~11장의 FSM 보행, Gazebo 물리 연동, IMU/LiDAR·SLAM 실습을 수행한 주니어 로봇 개발자다. 8장의 로봇 팔 RL 경험은 있으나, floating-base 접촉 시스템과 보행 정책의 일반화 검증은 새 학습 영역이다. 수식·코드·실험 결과의 연결을 이해할 수 있게 설명한다.

## 3. 저장소와 기준 커밋

저장소: https://github.com/silverbjin/Pysical_AI_ROS2

**실제 패키지명은 `my_quadruped_bot`이다.** 요청·메모에 등장하는 `my_quardruped_bot`, `quadruped_system`은 현재 패키지의 정확한 이름이 아니다.

| 대상 | 확인한 기준 | 의미 |
|---|---|---|
| Ch11 최신 구현 | `5c15411a533abba57d23b809f80b48a16dc813b8` | 11.7 프로젝트까지 포함 |
| 해당 브랜치 | `feat/ch11-autonomous-mapping` | 11.5·11.6 변경을 부모 이력으로 포함 |
| 확인 시점 main | `01b89caadb7385df1bb5072c6c09e17899645b0b` | 11.6 병합 상태. 당시 11.7과 동일하지 않음 |
| Ch08 소스 조회 | 위 main SHA로 고정 | 파일 내용·재사용 후보 확인 기준 |

다음 세션에서는 현재 원격 상태를 다시 조회한다. main이 11.7을 포함한다고 추정하지 않는다. Ch12 기준 브랜치에는 선택한 Ch11 기준이 포함되어야 한다. 이미 병합되었다면 최신 main을 쓰되 재사용 manifest에 실제 SHA를 기록한다. 원격을 강제 덮어쓰거나 과거 장을 재작성하지 않는다.

## 4. 개발·실행 환경

### 4.1 책의 기준

- Windows 11의 WSL2 / Ubuntu 24.04.
- ROS 2 Jazzy Jalisco / Gazebo Harmonic.
- Python 3.12 계열을 우선 기준으로 사용한다.
- MuJoCo 3.3.0, Gymnasium, Stable Baselines3, PyTorch.

‘Python 3.12+’를 임의의 최신 Python 전체에 대한 호환 보장으로 읽지 않는다. 실제 선택 버전과 설치·실행 증거를 남긴다.

### 4.2 Ch08의 환경 스냅샷

`Ch08/requirements-local-snapshot.txt`에는 mujoco=3.3.0, gymnasium=1.3.0, stable_baselines3=2.9.0, torch=2.12.1 등의 **기록값**이 있다. 이는 검증된 Ch12 잠금 파일이 아니다.

이 파일에는 ROS 패키지, CUDA 의존성, 과거 Ch07/08/11 build 경로를 가리키는 editable 설치 항목도 섞여 있다. 그대로 pip install -r 하거나 새 환경의 권장 목록으로 복사하지 않는다. Ch12에 필요한 최소 의존성으로 분리하고 실제 호환성을 확인한 뒤 버전을 고정한다.

### 4.3 Python 환경 분리

- 학습 전용 MuJoCo/Gymnasium 코어는 ROS 실행 없이도 동작하게 설계하는 것을 권장한다.
- ROS 노드는 apt로 설치한 rclpy의 Python 3.12 ABI와 맞춘다.
- rl_env를 활성화한 채 colcon·Gazebo를 실행해도 된다고 가정하지 않는다.
- ROS 추론 프로세스에 RL 의존성을 넣을 경우 system-site-packages venv 또는 명시적 프로세스 분리 중 하나를 선택하고 문서화한다.
- CUDA·GPU 사용 가능 여부는 실제 장치 조회로 확인한다. PPO의 작은 MLP에 GPU가 항상 유리하다고 단정하지 않는다.
- 학습은 headless를 기본으로 하고 viewer는 평가·디버깅 경로에서 켠다. WSLg GUI 성공과 headless 렌더링 성공은 별도 검증이다.

## 5. Ch11 인계 패키지의 실제 구성

위치: `Ch11/ros2_ws/src/my_quadruped_bot/`. 사용자 정의 인터페이스 패키지 `my_robot_interfaces`도 src에 있으며, 복사할 패키지의 package.xml 의존성을 함께 확인해야 한다.

### 5.1 모델과 보행 제어

| 구성 | 실제 경로/특징 |
|---|---|
| 로봇 모델 | urdf/robot.urdf.xacro |
| 기구·질량 파라미터 | urdf/common/robot_properties.xacro |
| 다리 체인 | urdf/parts/leg.xacro |
| Gazebo 센서·모델 관측 | urdf/common/gazebo_control.xacro |
| 보행 FSM | my_quadruped_bot/trot_controllerFSM.py |
| 위상·보행 모드 | generalized_gait_planner.py, gait_planner.py |
| 발 궤적·IK | trajectory_generator.py, inverse_kinematics.py |

현재 모델의 주요 값:

- 몸체: 0.60×0.30×0.15m, 몸체 질량 6.0kg. 로봇 전체 질량이 6kg이라는 뜻은 아니다.
- 다리당 hip/thigh/calf의 3개 회전 관절, 총 12개 구동 관절.
- thigh/calf 길이 각각 0.25m, hip_length=0.08m.
- hip 축 X, thigh/calf 축 Y.
- thigh 관절 원점 rpy=(0, 1.2, 0), calf 원점 rpy=(0, -2.4, 0).
- hip 한계 -0.8~0.8rad, thigh -1.0~4.0rad, calf -2.8~2.8rad.
- URDF effort 한계 hip=20, thigh/calf=30, velocity=10rad/s. MuJoCo actuator 힘 제한에 자동 적용된다고 가정하지 않는다.

URDF 관절각 0과 기하학적 ‘다리가 곧은 상태’는 다르다. 기존 FSM의 IK는 thigh/calf 원점 회전을 보정한다. MJCF 이식 시 이 오프셋을 누락하거나 두 번 더하지 않는다.

기존 플래너의 순서는 FL, FR, RL, RR이지만 URDF 인스턴스 선언 순서는 fr, fl, rr, rl이다. 배열 순서를 추정하지 말고 이름 기반 매핑을 고정한다. 예시 정책 관절 순서 제안:

```text
fl_hip_joint, fl_thigh_joint, fl_calf_joint,
fr_hip_joint, fr_thigh_joint, fr_calf_joint,
rl_hip_joint, rl_thigh_joint, rl_calf_joint,
rr_hip_joint, rr_thigh_joint, rr_calf_joint
```

이 순서는 Ch12가 채택·검증할 **제안 계약**이며 기존 모델 배열이 이미 이 순서라는 주장이 아니다.

11.7에서 FSM에 기본 0.5초 command watchdog을 연결했다. /cmd_vel 명령 단절 시 목표 속도를 0으로 하고 보행 주기 종료로 정지한다. 이는 관절 RL 정책의 힘 차단·안정 정지 기능을 대신하지 않는다.

### 5.2 센서·위치 추정·토픽

| 토픽 | 타입/역할 | 리뷰 시 주의 |
|---|---|---|
| /clock | rosgraph_msgs/Clock | 시뮬레이션 시간 |
| /joint_states | sensor_msgs/JointState | 관절 이름으로 정렬 |
| /imu/data_raw | sensor_msgs/Imu, base_link | Gazebo IMU, 기본 100Hz |
| /imu/rpy_filtered | std_msgs/Float32MultiArray | 11.2 디버그 자세 배열, Imu 메시지가 아님 |
| /scan | sensor_msgs/LaserScan, lidar_link | 원본 2D 스캔, 기본 10Hz |
| /scan/slam | LaserScan | 11.5 TF 기반 게이트 출력 |
| /scan_stabilized | LaserScan | 11.6 IMU 시각 매칭 게이트 출력 |
| /simulation/odom | nav_msgs/Odometry | Gazebo 모델의 물리 상태 관측 |
| /odom/raw | Odometry | sim_odometry가 검증·변환한 관측 |
| /odom | Odometry | 기존 robot_localization EKF 출력 |
| /map | OccupancyGrid | SLAM의 추정 지도 |
| /cmd_vel | geometry_msgs/Twist | 기존 FSM의 목표 속도 명령 |
| /model/my_quadruped/joint/<joint>/cmd_pos | std_msgs/Float64 | Gazebo 관절 위치 명령 |
| /lidar/points | PointCloud2 | 선택형 3D LiDAR 모드 |
| /scan/projected | LaserScan, scan_ground | 3D 점군의 높이 구간 투영 |

기본 위치 추정은 **관절 접촉 기반 다리 오도메트리가 아니라 Gazebo 모델 관측 + IMU**다. 이를 실물 localization 성능이나 순수 proprioception 기반 추정으로 소개하면 안 된다.

11.4의 leg_odometry는 별도 `/ekf_lab/*` 교육 실험이다. 명령 적분 결과를 관측 센서로 착각하거나 RL의 이동 성과 측정에 사용하지 않는다. IMU만으로 지속적인 슬립·속도 편향을 완전히 식별할 수도 없다.

### 5.3 TF 소유권

- SLAM Toolbox: map→odom.
- robot_localization: odom→base_footprint.
- robot_state_publisher: base_footprint→base_link→lidar_link 및 다리 링크.
- 선택형 projection_frame: odom→scan_ground.

현재 base_footprint는 base_link와 같은 원점·자세의 고정 루트이며, 몸체와 함께 기울어진다. 지면의 수평 프레임으로 가정하지 않는다. scan_ground는 별도의 가상 수평 프레임이며 고정 ground_height 가정을 사용한다. 경사 지면 자동 추정은 없다.

MuJoCo ROS 어댑터가 TF를 추가한다면 기존 EKF와 같은 TF를 중복 발행하지 않는다. truth 시각화가 필요하면 별도 프레임·토픽으로 구분한다.

### 5.4 실행·통합·탐사

| 런치 | 기능 |
|---|---|
| SLAM_simulation.launch.py | Gazebo + FSM + 기본 위치 추정 + 센서 시각화 선택 |
| localization.launch.py | sim_odometry + EKF |
| slam.launch.py | 11.5 SLAM |
| slam_optimized.launch.py | IMU/TF 게이트 + balanced/wide_search 튜닝 |
| slam_3d.launch.py | 선택형 3D 점군 높이 투영 + SLAM |
| mapping_total.launch.py | maze_room + 센서·EKF·SLAM + 선택적 탐사 |
| ekf_lab.launch.py | 11.4 격리 비교 실험 |

`figure_11_2.launch.py`는 **SLAM_simulation.launch.py로 변경되었다**. 이전 이름을 다시 생성하거나 원고 명령에 복원하지 않는다.

11.7의 mission/autonomous_explorer.py는 WAITING/FORWARD/TURN/BLOCKED/FINISHED 및 PAUSED 상태를 관리한다. /exploration/enable, /exploration/save_map 서비스와 /exploration/status를 제공한다. 시간 종료·BLOCKED·운영자 요청 시 부분 지도 저장을 지원한다.

이는 Nav2·frontier 탐사나 RL 정책이 아니다. 전체 공간 탐사·완전 지도·학습 기반 보행 성공을 증명하는 자료로 사용하지 않는다. Ch12에서는 상위 명령 제공 baseline 또는 비교 대상으로 활용할 수 있다.

## 6. Ch11 검증 상태 — 사실과 한계

최신 11.7 오프라인 검사 기록은 **104개 실행, 97개 통과, ROS/Gazebo 의존 검사 7개 건너뜀**이다. 증거는 `Ch11/evidence/autonomous_mapping_validation.json`과 관련 로그에 있다.

새로 추가된 11.4~11.7의 실제 WSL2·Gazebo EKF/SLAM/3D 투영/자율 탐사/자동 지도 저장은 이 작업 환경에서 실행하지 못한 항목이 있다. 최신 증거에 NOT_RUN이 명시되어 있다. 과거 figure 센서 시각화의 WSL2 디버깅 성공 기록을 이 통합 프로젝트의 성공으로 전용하지 않는다.

12장 리뷰에서는 선행 장의 모든 실험을 무조건 다시 수행하지 않는다. 재사용한 부분의 실제 의존성과 변경 영향을 확인하여 필요한 검사만 수행한다. 실행 미검증 항목은 유지하고, Ch12에서 실제 확인한 범위만 갱신한다.

## 7. Ch08 강화학습 코드의 재사용 후보와 주의점

실제 조회한 경로는 다음과 같다.

| 소스 | 활용할 수 있는 구조 | Ch12에 그대로 옮기면 안 되는 부분 |
|---|---|---|
| Ch08/ros2_ws/rl_env.py: ReachEnv | MuJoCo 모델 로딩, Gymnasium API, PPO 입력 구조 | 로봇 팔의 EE·목표물·보상·관측 구성 |
| Ch08/ros2_ws/train_reach.py | PPO, Monitor, DummyVecEnv, checkpoint 흐름 | 팔용 하이퍼파라미터·고정 출력 경로·기존 Env 인스턴스 재사용 |
| Ch08/ros2_ws/evaluate_robot.py | 별도 평가, deterministic predict, 통계 집계 | terminated를 성공으로 간주하는 로직·팔의 mm 오차 지표 |
| Ch08/ros2_ws/test_reach_env.py | 사람이 관찰하는 random-action 점검 흐름 | 관측 슬라이스·무음 default distance·외부에서만 설정하는 timeout |
| Ch08/ros2_ws/my_robot_env.py | 초기 Gymnasium 예제 참고 | train_reach.py가 사용하는 환경은 이 파일이 아니라 rl_env.py |
| Ch08/ros2_ws/src/my_robot_description/assets/simple_arm_6dof.xml | actuator·MJCF 작성 방식 참고 | 4족 모델 자체로 사용할 수 없음 |

실제 소스에서 확인한 재사용 시 수정 대상:

1. `ReachEnv` 설명 일부는 3DOF지만 실제 로딩 모델은 simple_arm_6dof.xml이다. 주석·관측·행동의 차원을 새 모델에서 다시 계산한다.
2. reset이 qpos/qvel 등을 복사하지만 전체 mjData를 재초기화하는 구조는 아니다. Ch12에서는 time, ctrl, actuator 상태, 외력, 접촉 캐시, 이전 액션, 누적 보상을 포함해 reset 계약을 설계한다.
3. 모든 qpos에 균일 잡음을 더하는 코드는 floating-base quaternion을 깨뜨릴 수 있다. base 자세와 hinge 초기화를 분리한다.
4. ReachEnv는 내부 step에서 truncated=False를 반환하며 학습용 TimeLimit도 현재 train_reach.py에 없다. Ch12에서는 환경 또는 wrapper에 시간 한계를 명시한다.
5. evaluator의 `terminated and not truncated`를 성공으로 세는 fallback은 넘어짐·충돌 종료를 성공으로 오분류한다. `is_success`와 종료 사유를 사용한다.
6. 보상이 모든 data.ncon을 벌점으로 사용한다. 4족 로봇의 발-지면 접촉은 정상 행동이다. geom 쌍으로 발 접촉과 몸체/장애물 충돌을 구분한다.
7. 관측은 ee_site를 포함하지만 보상은 link_ee body 위치를 사용한다. 팔의 좌표 불일치 위험을 보행 태스크에 전파하지 않는다.
8. my_robot_env.py는 np.random 전역 난수로 목표를 샘플링한다. Ch12는 self.np_random과 명시적 seed를 사용한다.
9. train_reach.py의 lambda는 이미 생성된 raw_env를 감싼다. 병렬 환경에는 각각 새로운 model/data/env 인스턴스를 생성해야 한다.
10. rgb_array가 metadata에 선언되어 있어도 ReachEnv의 실제 render는 human viewer 중심이다. 영상 저장이 필요하면 별도 renderer 구현·검증이 필요하다.
11. 기존 checkpoint ZIP은 팔 정책이다. 보행 정책 초기값·완성 모델로 무조건 로드하지 않는다.
12. 기존 성공률·평균 보상·‘Action Jerk’ 문구를 그대로 사용하지 않는다. 액션 차이는 물리적 jerk나 실제 소비전력과 동일하지 않다.

원본 Ch08을 이번 장을 위해 고치지 않는다. 필요한 파일을 Ch12로 복사한 뒤 수정하고 원본 파일 SHA와 변경 이유를 기록한다.

## 8. Ch12 독립 구성 원칙

**사용자 지시:** 12장 실습 패키지는 Ch12에 별도로 구성한다. Ch11·Ch08의 필요한 소스는 복사 가능하며, 이 재사용을 위해 다시 승인을 요청할 필요는 없다.

다음은 권장 구조이며 아직 생성된 실행 패키지 목록이 아니다.

| 제안 경로 | 책임 |
|---|---|
| Ch12/ros2_ws/src/my_quadruped_bot/ | 필요한 Ch11 ROS 모델·기존 제어·브리지의 장별 복사본 |
| Ch12/ros2_ws/src/my_robot_interfaces/ | 복사한 패키지가 실제로 의존할 때 포함 |
| Ch12/ros2_ws/src/quadruped_rl_ros/ | 정책 추론·관측 어댑터·제어권·ROS 런치 |
| Ch12/rl/pyproject.toml | ROS에 독립적인 학습 Python 프로젝트 설치 정의 |
| Ch12/rl/src/quadruped_rl/ | MuJoCo 환경·reward·관측·액션 매핑·학습·평가 |
| Ch12/rl/assets/ | floating-base MJCF, 지형·장애물 모델 |
| Ch12/config/ | task·PPO·policy IO·joint order 설정 |
| Ch12/tests/ | 수학·모델·환경·rollout·추론 회귀 검사 |
| Ch12/scripts/ | 환경 확인·검증·학습·평가 진입점 |
| Ch12/docs/ | 설치·실행·리뷰·재사용 manifest |
| Ch12/evidence/ | 재현 가능한 소규모 검증 로그·메타데이터 |

- Ch08/Ch11의 build, install, log, venv, __pycache__, TensorBoard 대형 로그, 기존 모델 ZIP을 일괄 복사하지 않는다.
- `.draft`, `.1st`, `copy.py` 등을 동작 기준 파일로 선택하지 않는다. setup.py의 파일 수집 규칙도 확인한다.
- Ch12 설치·실행 경로가 Ch08/Ch11 파일의 런타임 상대 참조나 절대 경로에 의존하지 않게 한다.
- 같은 이름 my_quadruped_bot의 장별 복사본은 가능하다. 단, 새 터미널에서 `/opt/ros/jazzy`와 Ch12 overlay만 적용하며 `ros2 pkg prefix`로 확인한다.
- 새 RL 코드는 quadruped_rl / quadruped_rl_ros처럼 역할을 드러내는 별도 이름으로 구분하는 것을 권장한다.
- 모델·설정 파일은 설치 후에도 찾을 수 있도록 package data/resource 설치 경로를 정의한다. 현재 작업 디렉터리에만 의존하는 경로를 남기지 않는다.
- 다른 프로세스·장과 토픽이 섞이면 별도 ROS_DOMAIN_ID 또는 namespace로 격리한다. root 절대 토픽이 namespace를 우회하는지 확인한다.
- 체크포인트·대용량 영상은 별도 artifact 경로를 사용하고 경로·해시만 기록한다. 가상환경과 GPU 라이브러리를 git에 넣지 않는다.

재사용 manifest 필드: source_commit, source_path, source_blob_sha, destination_path, copy_or_adapt, changes, required_dependencies, license_notes, validation_status.

## 9. 권장 구현·리뷰 순서

MuJoCo 학습 코어를 우선 구성하고 ROS/Gazebo 추론 검증을 뒤에 연결하는 경로를 권장한다. Gazebo 직접 학습도 허용하되 step/reset 제어와 비동기 센서 동기화를 먼저 증명한다. 두 백엔드를 처음부터 같은 깊이로 동시에 구현하는 것을 필수로 삼지 않는다.

1. **모델:** Ch11의 기구 구조를 반영한 floating-base 12관절 MJCF와 관절/actuator 매핑 검증.
2. **환경:** reset/step/종료/시간 한계가 있는 Gymnasium 환경, 안정 기립·짧은 rollout.
3. **저수준 보행:** 속도 명령을 받아 12관절 액션을 출력하는 정책을 학습·평가.
4. **목표·회피:** 목표 상대 위치·거리 센서를 포함하는 태스크. 목표 도달 또는 장애물 회피 중 본문 범위에 맞는 최소 하나를 검증하고 둘의 구현 여부를 명시.
5. **독립 평가:** 별도 seed·초기 상태·장애물 배치와 고정 평가 프로토콜.
6. **ROS 연결:** Ch12 관측 어댑터·정책 노드·watchdog·FSM과의 배타적 제어.
7. **필요 시 Gazebo 전이:** 실제 모델·actuator·센서·주기 차이를 확인하고 별도 결과로 보고.

상위 정책이 속도 명령을 출력하고 고정된 RL 보행 정책이 관절을 제어하는 계층형 구성도 가능하다. 이 경우 두 정책의 학습 여부·주기·관측·책임을 구분한다.

## 10. 모델·시뮬레이션 리뷰 계약

- 로봇 몸체에 free joint가 있어야 한다. 몸체를 world에 고정한 모델의 발 움직임만으로 보행을 평가하지 않는다.
- 단순 모델이 free joint 1개 + hinge 12개라면 nq=19, nv=18, nu=12가 예상된다. 다른 자유 물체·actuator가 있으면 달라지므로 숫자를 무조건 하드코딩하지 않는다.
- MuJoCo quaternion WXYZ와 ROS quaternion XYZW 변환을 명시한다.
- joint name, jnt_qposadr, jnt_dofadr, actuator joint 매핑을 조회하고 -1 ID·중복·누락을 거부한다.
- URDF 원점 회전, 좌우 hip 부호, 관성, collision 크기, foot geom, 질량·접촉 마찰을 확인한다.
- URDF→MJCF 변환 성공만으로 동역학 일치를 선언하지 않는다. 링크 FK·발 위치·기립 높이·접촉·낙하·제어 응답을 비교한다.
- 정책 주기와 물리 주기를 구분한다. 예: 물리 dt=0.002초, decimation=10이면 정책 50Hz다. 이 값은 초기 제안이며 실제 설정·로그로 확정한다.
- position target이면 명목 자세+스케일·PD/servo·포화·관절 한계를 명시한다. torque이면 gear/ctrlrange/forcerange와 실제 토크 단위를 명시한다.
- Ch08의 motor gear와 action*50을 중복 적용하지 않는다. Ch11 Gazebo cmd_pos는 토크 명령이 아니다.
- render/sleep 호출로 물리 dt를 정의하지 않는다. 리셋 시 관절과 몸체를 놓는 것은 허용하지만 step마다 원하는 위치로 옮기는 방식은 금지한다.

## 11. 관측·행동·보상·종료 리뷰 계약

### 관측

body/world/sensor 프레임과 단위를 각 feature에 명시한다. 저수준 정책의 초기 후보는 body 각속도(3), 투영 중력(3), 명목 자세 대비 관절 위치(12), 관절 속도(12), 이전 액션(12), 속도 명령(3)으로 45차원이다. 이는 구현 제안이며 확정된 checkpoint 규격이 아니다.

base 선속도를 더하면 48차원이지만, 배포에서 그 값을 어떻게 추정할지 함께 정해야 한다. 목표 상대 벡터·LiDAR sector·접촉 등을 추가하면 새 차원과 순서를 manifest에 기록한다. 관측 space.shape, 실제 dtype/범위, 정책 입력과 정규화 통계를 대조한다.

보상·종료 평가에 truth 위치를 쓰는 것과 정책 관측에 truth를 넣는 것은 다르다. 실물에서 얻을 수 없는 값은 privileged observation으로 표시하고 배포 가능한 actor의 입력과 구분한다. actor가 전체 장애물 정답 좌표를 몰래 받는 경우 센서 기반 회피라고 설명하지 않는다.

### 행동

액션 차원·단위·정렬·clip·변화율 제한·명목 자세·low-level gain을 고정한다. NaN/Inf, 잘못된 shape, 오래된 관측 또는 추론 지연에는 동작을 계속하지 않는 정책을 둔다. 별도 배포 watchdog이 필요하다.

### 보상

속도 추종/목표 거리 감소, 자세 안정, 몸체 높이, 충돌·넘어짐, 과도한 액션 변화, 제어 비용 등을 분리 로그로 남긴다. 생존 보상만으로 제자리 서기가 최적이 되거나, 충돌 후에도 목표 성공 보너스를 받는 편법을 점검한다.

발 접촉은 정상 지지일 수 있다. body-ground·self collision·obstacle collision과 구분한다. 액션 L2를 실제 소비전력으로 부르지 않는다. 에너지 지표가 필요하면 물리 토크·각속도·시간과 계산 규약을 기록한다. 보상 항의 dt 스케일도 확인한다.

### 종료·reset

- Gymnasium reset은 (obs, info), step은 (obs, reward, terminated, truncated, info)를 반환한다.
- 목표 성공·넘어짐·심각한 충돌은 각각 종료 사유를 기록한다. 시간 한계는 truncated로 구분한다.
- is_success는 독립적인 목표 조건으로 계산한다. terminated 자체를 성공으로 세지 않는다.
- 성공 반경·유지 시간, 넘어짐 기준·충돌 허용 범위·에피소드 시간을 사전에 고정한다.
- reset 시 시뮬레이터·목표·장애물·이전 액션·필터·외력·누적 상태를 초기화하고 mj_forward 등 필요한 파생 상태 갱신을 수행한다.
- seed 재현성을 검증하되 서로 다른 seed의 평가를 하나의 성공 사례로 대체하지 않는다.

## 12. 학습·평가·배포 리뷰 계약

- check_env 성공은 API 정합성 검사이며 학습 성공이나 물리 모델 검증이 아니다.
- 각 vector env는 독립적인 model/data/RNG를 가진다. 전역 mutable gait 설정이나 Ch11 GAIT_LIBRARY 인스턴스 공유도 확인한다.
- PPO 총 step·n_envs·n_steps·batch_size·실제 update 수와 wall 시간을 기록한다. 팔의 200만 step 설정을 보행의 충분 학습량으로 보장하지 않는다.
- 학습·평가 환경·seed를 분리하고 학습 중 평가 결과로 고른 모델을 다시 독립 평가한다.
- VecNormalize를 쓰면 정책과 통계를 함께 저장하고 평가에서 통계 갱신을 끈다. 사용하지 않았다면 존재한다고 기록하지 않는다.
- 종료 시점·중간 checkpoint·실패 복구를 구분한다. 같은 이름으로 기존 모델을 조용히 덮어쓰지 않는다.
- 성공률, 넘어짐률, 충돌률, timeout, 목표 최종 거리, 이동 진전, 속도 추종 오차, 추론 지연을 태스크에 맞춰 보고한다.
- 단일 seed의 짧은 smoke 학습과 정식 성능 평가를 구분한다. 정식 비교는 예를 들어 학습 seed 3개×별도 평가 20회 이상을 출발점으로 삼되, 실제 예산·본문에 맞춘 protocol을 사전에 확정한다.
- 성공률 목표치는 코드 리뷰 도중 임의로 낮추지 않는다. 달성하지 못한 실제 수치는 그대로 보고한다.
- 도메인 랜덤화는 마찰·질량·지연 등 범위와 seed를 기록한다. 범위를 무작정 넓히면 현실성이 높아진다고 단정하지 않는다.

checkpoint 묶음에 필요한 메타데이터: source SHA, model/config 해시, 패키지 버전, joint order, observation/action schema, 정규화 여부·통계 파일, physics dt/decimation, actuator 의미, seed·training steps, 평가 protocol/결과.

MuJoCo에서 학습한 정책이 Gazebo에서 바로 동작한다고 가정하지 않는다. 관절 부호·원점·액추에이터·접촉·센서 지연·주기·스케일을 검증한 결과가 있을 때만 해당 전이 범위의 성공을 주장한다.

## 13. ROS 제어권과 초기화 점검

Ch12 launch는 다음 모드를 구분하는 것을 권장한다.

- classical: 기존 FSM만 관절을 구동.
- rl: 정책 추론 노드만 관절을 구동.
- evaluation: 정책을 평가하되 외부 탐사/teleop 명령원을 명시적으로 선택.

정책이 12관절 명령을 발행하면 기존 trot_controllerFSM의 관절 발행을 함께 켜지 않는다. 상위 정책이 /cmd_vel을 발행하는 구성이라면 하위 보행 제어기 하나를 명확히 지정한다. Ch11 탐사·teleop와 정책이 같은 토픽을 경쟁 발행하지 않게 한다.

Gazebo backend를 채택하면 reset 요청 후 시뮬레이션 시각·센서 stamp·TF·localization reset 완료를 확인해야 한다. sleep(1) 뒤 이전 에피소드 센서 큐를 사용하는 패턴은 피한다. 학습용 step은 의도한 물리 시간만 진행하는지 검증한다.

## 14. 리뷰 산출물과 완료 기준

### 단계별 검증

| 단계 | 필요한 근거 | 이 근거만으로 주장할 수 없는 것 |
|---|---|---|
| 정적 검사 | 구문·설정·의존성·경로 검사 | 실제 물리 실행 |
| 모델 검사 | 로딩, joint/actuator 매핑, FK, 접촉·기립 | 학습 성공 |
| 환경 검사 | reset/step·seed·종료·수치 유효성·check_env | 목표 성능 |
| 학습 smoke | 짧은 PPO 실행, 저장·재로드·추론 | 안정 보행·일반화 |
| 태스크 평가 | 고정 protocol의 episode별 CSV/JSON·영상·집계 | 실물 전이 |
| ROS/Gazebo 통합 | 실제 토픽·TF·제어권·관절 응답·지연 | MuJoCo와 동역학 동일성 |

각 검사는 PASS/FAIL/NOT_RUN/SKIP을 구분하고 실제 명령·exit code·환경·seed를 기록한다. 실행할 수 없었던 항목을 추정으로 통과시키지 않는다. 테스트 수가 많다는 이유로 학습 성능을 인정하지 않는다.

리뷰 보고서는 Critical/High/Medium/Low로 구분하고, 파일·함수·트리거·실제 영향·재현/검증 근거·수정안을 제공한다. 취향 수준 리팩터링을 기능 오류보다 우선하지 않는다. 수정한 부분에 맞는 회귀 검사를 수행하고 원고 설명도 동기화한다.

이번 장의 구현 완료와 성능 목표 달성은 별도 판정한다. 최소한 독립 Ch12 설치, 모델·환경 검사, 관절 수준 보행 학습 경로, 선택한 목표/회피 태스크, checkpoint 재평가, 실제 실행 방법·한계를 갖추어야 한다. 미달 성능은 미달로 남긴다.

## 15. 다음 리뷰 세션의 첫 작업 지시

1. 이 문서를 읽고 실제 원격 SHA와 Ch12 작업 상태부터 확인한다.
2. Ch12 코드가 이미 있다면 새로 덮어쓰지 말고 구현·실행 진입점·의존성을 파악한다.
3. Ch11·Ch08의 위 경로를 확인하고 필요한 소스만 Ch12로 복사·적응한다. 복사 승인은 이미 있다.
4. 본문/코드가 정한 backend, 저수준/상위 정책의 역할, 관측·행동·태스크 범위를 우선 정리한다. 아직 비어 있는 구현 선택만 합리적으로 제안한다.
5. 모델·환경·학습·평가·ROS 통합 순으로 리뷰하고 중대한 계약 불일치를 먼저 해결한다.
6. 변경과 검증 결과를 Ch12/docs 및 Ch12/evidence에 남긴다. Ch08·Ch11의 코드·증거는 보존한다.
7. 기존 모델 ZIP이나 과거 테스트 로그를 Ch12 성능 증거로 재사용하지 않는다.

## 16. 참조 문서

### 저장소 인계 문서

- ../../Ch11/docs/AUTONOMOUS_MAPPING_11_7_GUIDE_KO.md
- ../../Ch11/docs/SLAM_OPTIMIZATION_11_6_GUIDE_KO.md
- ../../Ch11/docs/SLAM_MAPPING_11_5_GUIDE_KO.md
- ../../Ch11/docs/EKF_11_4_GUIDE_KO.md
- ../../Ch11/evidence/autonomous_mapping_validation.json
- ../../Ch08/ros2_ws/rl_env.py
- ../../Ch08/ros2_ws/train_reach.py
- ../../Ch08/ros2_ws/evaluate_robot.py
- ../../Ch08/requirements-local-snapshot.txt

위 목록은 저장소 내 참조 경로이며, Ch12에서 이미 구현한 파일 목록이 아니다.

### 공식 API 근거

- MuJoCo 3.3.0 simulation functions: https://mujoco.readthedocs.io/en/3.3.0/APIreference/APIfunctions.html
- MuJoCo Python: https://mujoco.readthedocs.io/en/stable/python.html
- Gymnasium Env: https://gymnasium.farama.org/api/env/
- SB3 vector environments / normalization: https://stable-baselines3.readthedocs.io/en/master/guide/vec_envs.html

공식 문서의 latest/master는 변경될 수 있다. 실제 구현에서 선택한 설치 버전의 API와 다시 대조한다.
