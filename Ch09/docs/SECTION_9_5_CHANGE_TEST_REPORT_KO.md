# 9.5절 코드 수정 및 정적 테스트 보고서

- 기준 HEAD: `b3ad4ec3a8625d6599543b0ac2f4af780dcfba65` · 기존 브랜치: `docs/ch09-section-9-5-review-lab`
- 수행일: 2026-10-21 KST
- 상태: **STATIC_CHECK_PASS (6건)** / SYNTAX NOT_RUN / BUILD NOT_RUN / RUNTIME NOT_RUN

## 주요 문제 / 수정

1. `launch/simulation.launch.py`: `/clock` 브리지를 실행하면서 `robot_state_publisher`가 `use_sim_time`을 사용하지 않아 TF와 센서 시간축이 달라질 수 있었다. `use_sim_time` 인자를 선언하고 기본값 true를 RSP에 전달하도록 수정했다.
2. `launch/9-5_simulation.launch.py`: `Command(['xacro ',...])` 실행 결과를 `ParameterValue(..., value_type=str)`로 전달해 XML 문자열을 파라미터 문자열로 취급하도록 명시했다.
3. `package.xml`: ament_python buildtool 및 RSP·Gazebo·브리지·런치·GUI·Python 노드의 실행 의존성을 선언했다.

## 변경 파일

- `Ch09/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/launch/9-5_simulation.launch.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/package.xml`

## 실행한 소스 기반 정적 계약 검사

1. PASS — simulation.launch declares use_sim_time with default true
2. PASS — simulation robot_state_publisher consumes simulation time
3. PASS — alternate 9-5 simulation launch ensures robot_description string
4. PASS — both Gazebo launches still spawn a single entity
5. PASS — manifest declares Gazebo, bridge, RSP and ROS node dependencies
6. PASS — Python ament buildtool is declared

이번 검사는 원격 실제 코드의 소스 불변식만 검사한 JavaScript 정적 어설션이다. **파이썬 컴파일, package.xml ROS 유효성 검사, colcon, Gazebo 런타임은 미실행**이므로 빌드/실기동 성공을 주장하지 않는다.

## 로컬 재현·회귀 기준 (NOT_RUN)

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
python3 -m compileall -q src/my_quadruped_bot/launch
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 launch my_quadruped_bot simulation.launch.py
# 새 터미널에서 source 후:
ros2 param get /robot_state_publisher use_sim_time
ros2 topic echo /clock --once
ros2 topic echo /joint_states --once
```

기대: RSP의 `use_sim_time`이 true, 시뮬레이션 시간 데이터 수신 및 Gazebo 스폰 성공. `9-5_simulation.launch.py`도 별도 세션으로 실행해 XML 파라미터 오류 부재를 확인한다. 다른 장 동일 패키지 overlay를 사용하지 않는다.

## 남은 위험

launch 노드가 동시에 시작하므로 서비스/토픽 준비 지연을 만날 수 있다. 이 변경은 스폰 성공을 보장하거나 실물 보행을 검증하지 않는다.
