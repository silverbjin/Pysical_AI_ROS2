# 9.6절 코드 수정 및 정적 테스트 보고서

- 기준 HEAD: `f9d6d05f752ecef6958615f2af87d266e30648f2`
- 기존 브랜치: `docs/ch09-section-9-6-review-lab`
- 수정 파일: `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/stand_up.py`
- 수행일: 2026-10-21 KST
- 검증: **STATIC_CHECK_PASS (6건)** / Python SYNTAX NOT_RUN / BUILD NOT_RUN / ROS RUNTIME NOT_RUN / TASK NOT_RUN

## 변경 이유·설계

기존 `stand_up.py`는 시작 직후 hip=0, thigh=-0.6, calf=+1.2 rad의 목표를 10Hz로 즉시 발행하고, 뒤 절의 `single_leg_mover`와 `fr_thigh` 제어권이 겹쳤다. 다음을 보완했다.

1. `ramp_seconds` 파라미터(기본 2.0초, 허용 0.1~30초): 목표 명령을 0에서 명목 각도까지 선형 증가시켜 시작 시 각도 지령 점프를 줄인다.
2. `exclude_joint` 문자열 파라미터(기본 빈 문자열): 다리 하나를 다른 제어 노드에 맡기려는 경우 해당 조인트의 퍼블리셔를 만들지 않는다. 오타 또는 존재하지 않는 관절은 명시적으로 거부한다.
3. `get_clock().now().nanoseconds`로 실제 ROS 시각 간격을 계산하고 시뮬레이터 시계가 역행하면 램프 시작 시각을 다시 설정한다.
4. 기존 기본 기립 목표, 관절 이름, 명령 토픽, 10Hz 전송 주기는 유지했다.

**안전 경계:** 완화 램프만으로 균형을 보장하지 않는다. 여러 명령자가 나머지 관절까지 공유하지 않는지 `ros2 topic info -v`에서 확인한다. 실물 로봇을 대상으로 하는 기능이 아니다.

## 실행한 정적 소스 계약 검사

1. PASS — ramp_seconds parameter bounded (0.1 .. 30 s)
2. PASS — timed smooth interpolation applied to all three joint kinds
3. PASS — sim-time reset guarded against stale start_ns
4. PASS — exclude_joint allows exactly one controlled joint to be released
5. PASS — existing nominal stand-up targets preserved
6. PASS — unchanged 10 Hz publisher cadence

이 검사들은 원격 코드의 패턴과 구성 불변식에 대한 JavaScript 어설션이다. **Python 컴파일·ROS rclpy 콜백 실행은 하지 않았으므로 성공이라고 주장하지 않는다.**

## 로컬 실행·회귀 명령(NOT_RUN)

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
python3 -m py_compile src/my_quadruped_bot/my_quadruped_bot/stand_up.py
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 launch my_quadruped_bot simulation.launch.py
# 별도 터미널에서 source 후:
ros2 run my_quadruped_bot stand_up --ros-args -p ramp_seconds:=2.0
ros2 topic info /model/my_quadruped/joint/fr_thigh_joint/cmd_pos -v
```

9.7절에 해당 관절을 넘겨주는 경우 기립 노드를 아래처럼 별도로 시작하고, 그 관절에만 `single_leg_mover`를 적용한다. 그러나 9.7절 개선안의 12관절 통합 publisher 버전과는 **동시 실행하지 않는다**.

```bash
ros2 run my_quadruped_bot stand_up --ros-args -p exclude_joint:=fr_thigh
```

실제 `/joint_states`로 ramp 전후의 과도 응답, 기립 시간·경사·진동 등을 측정하고 초기값과 동일 조건으로 비교해야 한다. `use_sim_time`은 9.5절 수정과 병합되어야 한다.

## 미해결

Gazebo 실제 기립 안정성, 컨트롤러 토크 포화 및 잡음·마찰 영향은 NOT_RUN이다. PR 병합 후 ROS2 Jazzy 환경에서 반드시 회귀 테스트가 필요하다.
