# 9.7절 코드 수정 및 정적 테스트 보고서

- 작업일: 2026-10-21 (KST)
- 기존 브랜치: `docs/ch09-section-9-7-review-lab`
- 기준 SHA: `18bc175ac7e4d971bac416a1a57c1dc2a8d19a5b`
- 상태: **STATIC_CHECK_PASS 8건** / **Python SYNTAX NOT_RUN / ROS RUNTIME NOT_RUN / Gazebo TASK NOT_RUN**

## 문제와 수정

원본 `single_leg_mover.py`는 `fr_thigh` 명령 토픽 하나만 발행했다. 다른 11관절을 담당하는 `stand_up.py`와 동시 실행하면 해당 관절을 두 노드가 동시에 제어했다. 또한 `self.time += timer_period`를 사용해 콜백 지연 시 파형의 실제 시간과 누적 시간이 어긋날 수 있었다. `trot_gait_preview.py`도 네 개 thigh만 발행해 동일한 제어권 경합 문제가 있었다.

- **단일 제어권:** `single_leg_mover`와 `trot_gait_preview`가 각각 전체 12관절 명목 자세를 발행하도록 했다. 두 노드는 **서로와 stand_up을 동시에 실행하지 않아야 한다**.
- **초기 완충:** `ramp_seconds` 기본 2초 동안 12관절 명령을 0에서 hip=0, thigh=-0.6, calf=+1.2 rad까지 선형 변화시킨 다음, 단일 thigh 사인파/대각 쌍 파형을 시작한다.
- **실제 시간 기반:** 현재 노드의 ROS clock으로 경과 시간을 계산하여 timer 실행 지연으로 인한 주파수 드리프트를 줄였으며 시계 역행 시 시작 시각을 재설정한다.
- **경계 검사:** `amplitude`, `frequency`, `ramp_seconds` 파라미터를 물리 실습에 맞는 유한 범위로 제한한다.
- **용어 정정:** 대각 쌍 위상 신호를 보냈다는 이유만으로 실제 `trot` 보행 안정성이나 발 접촉 성공을 주장하지 않는다.

## 코드 변경 파일

- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/single_leg_mover.py`
- `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py`

## 실제 실행한 정적 계약 검사

1. PASS — single-leg node owns all 12 joint command publishers
2. PASS — sine affects FR thigh only
3. PASS — clock-based phase avoids accumulated timer drift
4. PASS — nominal 11-joint stance ramps before motion
5. PASS — trot diagonal pair phase separation retained
6. PASS — trot also owns 12 joint command publishers
7. PASS — amplitude and frequency bounded in both nodes
8. PASS — both nodes cleanup via finally

원격 코드 변경본의 불변식과 명칭을 JavaScript 정적 계약 어설션으로 확인했다. Python `py_compile` 및 ROS 2 rclpy 콜백, 실제 시뮬레이터 메시지·움직임은 이 세션에서 수행하지 않았다.

## 현장 재현 절차(NOT_RUN)

```bash
source /opt/ros/jazzy/setup.bash
cd ~/Pysical_AI_book/Ch09/ros2_ws
python3 -m py_compile src/my_quadruped_bot/my_quadruped_bot/single_leg_mover.py
python3 -m py_compile src/my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py
colcon build --symlink-install --packages-select my_quadruped_bot
source install/setup.bash
ros2 launch my_quadruped_bot simulation.launch.py
# 별도 Ch09 terminal, stand_up을 종료한 뒤 단일 노드 실행:
ros2 run my_quadruped_bot single_leg_mover --ros-args -p use_sim_time:=true
ros2 topic info /model/my_quadruped/joint/fr_thigh_joint/cmd_pos -v
```

동일 명령 환경에서 `ros2 run my_quadruped_bot trot_gait_preview --ros-args -p use_sim_time:=true`를 **별도 세션으로** 시험한다. 총 12관절 명령 publisher 1개씩, 적절한 브리지 토픽과 `/joint_states` 추종을 확인한다.

**해당 런타임 검증은 NOT_RUN이다.** 다른 9.6 PR과 병합된 후에도 제어권 중복 회귀 검사가 필요하다. 실제 균형·보행 성공을 검증한 것으로 해석하지 않는다.
