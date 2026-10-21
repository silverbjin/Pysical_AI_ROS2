> **사후 보완 (2026-10-21):** 이 문서는 최초 코드 리뷰 시점의 판단을 보존합니다. 이후 소스 수정과 정적 점검은 [SECTION_10_7_FIX_TEST_REPORT_KO.md](SECTION_10_7_FIX_TEST_REPORT_KO.md)를 참조하세요. 기존의 '코드 변경 없음' 기록은 최초 리뷰 당시 상태입니다.

# 10.7절 코드 리뷰 보고서 — ROS 2 통합 제어 노드

- 작성/정적 검토: 2026-10-21 KST
- 원고 범위: 첨부 『Physical AI 실무 가이드』 10.7절
- 소스 기준: `silverbjin/Pysical_AI_ROS2` main (작업 시작 `bab76f6ca7df0bda6efd8882c1a698561707e51d`)
- 파일: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/quadruped_controller_ros2.py`; `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/quadruped_controller.py`; `Ch10/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`; `Ch10/ros2_ws/src/my_quadruped_bot/package.xml`; `Ch10/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`
- 평가: **정적 리뷰 수행, 실제 ROS 2/Gazebo 빌드 및 물리 보행 성공 여부 미검증; 통합 판정 보류**

## 학습 목표와 실제 코드의 차이

50Hz 노드의 LPF·동적 파라미터·TF/odometry를 공부하는 절이다. 원고의 `/joint_commands`↔Gazebo 토픽 계약은 현재 YAML과 다르며, 현행 `quadruped_controller_ros2`는 실보행 통합 완료 코드가 아니다.

## 문제 목록 및 권고 조치

| 우선순위 | 코드 문제 | 근거·영향 | 권고 |
|---|---|---|---|
| CRITICAL | 통합 노드가 실제 보행 명령을 생성하지 않음 | `quadruped_controller_ros2.py`의 `compute_foot_trajectory()`는 고정 `[0.2,0.1,-0.3]`, `ik_angles=self.default_stance`로 대체되어 planner·IK가 실행되지 않는다. | 실제 GaitPlanner/TrajectoryGenerator/IK를 호출해 조인트별 목표를 계산하도록 구현. |
| CRITICAL | 관측 토픽을 명령 토픽으로 오용 | 해당 노드가 `/joint_states`에 목표 JointState를 publish한다. ROS/Gazebo 브리지에서 `/joint_states`는 관절 상태 피드백의 GZ_TO_ROS 방향으로 정의되어 있어 측정값과 목표값 혼재/충돌 위험이 있다. | 명령을 ROS_TO_GZ로 매핑된 12개 Float64 위치 제어 토픽으로 분리; `/joint_states`는 측정 전용. |
| HIGH | 파라미터 검증과 적용이 분리 | `step_freq`, `gait_type` 처리 구간의 planner 수정 코드가 주석이며, `alpha`는 다른 파라미터가 실패한 배치에서도 일부 갱신될 수 있다. | 전 항목 검증 성공 후 원자적으로 적용하고 gait planner 상태를 재검증. |
| HIGH | 추측 항법을 센서 측정 오도메트리처럼 해석할 위험 | `publish_odometry()`는 입력 `/cmd_vel`을 적분하여 pose/TF를 발행한다. 슬립·실제 자세·외란을 관측하지 않는다. | `odom`을 command-integrated dead reckoning으로 표시하고 실제 Gazebo world pose 대비 오차 측정; 동일 odom→base_link TF를 둘 이상 발행하지 않는다. |
| HIGH | 입력 명령 만료와 제어권 보호 부재 | 속도는 마지막 메시지를 무기한 유지하며, 동일 관절 명령 토픽에 다른 컨트롤러가 쓰면 경쟁한다. | watchdog, 속도 제한, 단독 publisher, clock/use_sim_time 및 리소스 검사. |

## 확인한 내용과 확인하지 못한 내용

- **확인:** 현재 main의 관련 Python, launch, XML/YAML 소스와 사용자 제공 원고를 대조했다. 결함 지적은 텍스트/실제 코드의 특정 표현을 근거로 한다.
- **확인 불가:** 해당 작업 환경에서 실제 WSL2 ROS 2 Jazzy·Gazebo Harmonic 실기동, colcon 컴파일, 센서·토픽 왕복, 지면 접촉·낙상 로그는 수집하지 않았다.
- **혼동 금지:** 명령/상태 메시지가 발행된 사실은 발의 실제 움직임 또는 물리적 전진 성공을 의미하지 않는다.
- **변경 범위:** 이 PR은 분석 문서와 실습 가이드만 추가한다. 실패 원인이 있는 소스 코드는 수정하지 않았다.

## 재현 권장 순서

```bash
source /opt/ros/jazzy/setup.bash
cd Ch10/ros2_ws
python3 -m compileall -q src/my_quadruped_bot/my_quadruped_bot
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
```

## 재현 및 승인 체크리스트

1. [ ] ROS 2 50 Hz 타이머와 수신·송신 토픽을 확인한다.
2. [ ] `/joint_states`의 발행자 수 및 실제 물리 상태와 목표 각의 구분을 기록한다.
3. [ ] 파라미터 성공 응답만이 아니라 planner/frequency와 발 궤적에 실제 반영됐는지 확인한다.
4. [ ] odom/TF가 측정치가 아닌 적분 예측임을 실측 pose와 비교해 설명한다.
5. [ ] 해당 실행 환경(WSL2, ROS/Gazebo 배포판, Git SHA, 의존성) 기록
6. [ ] 실패/수정 전후의 테스트 로그 및 시뮬레이션 증거 저장
7. [ ] 10.1~10.7 선행 위험의 해결 여부 확인

**최종 의견:** 안전성과 재현성을 입증하는 실제 테스트 이전에는 '동작 완료/성공'으로 판정하지 않는다. 자세한 교육 절차는 [LAB_10_7_GUIDE_KO.md](LAB_10_7_GUIDE_KO.md) 참조.
