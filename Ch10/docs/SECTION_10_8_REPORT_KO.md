# 10.8절 코드 리뷰 보고서 — Gazebo 보행·안정성 통합 검증

- 작성/정적 검토: 2026-10-21 KST
- 원고 범위: 첨부 『Physical AI 실무 가이드』 10.8절
- 소스 기준: `silverbjin/Pysical_AI_ROS2` main (작업 시작 `bab76f6ca7df0bda6efd8882c1a698561707e51d`)
- 파일: `Ch10/ros2_ws/src/my_quadruped_bot/launch/simulation.launch.py`; `Ch10/ros2_ws/src/my_quadruped_bot/launch/9-5_simulation.launch.py`; `Ch10/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml`; `Ch10/ros2_ws/src/my_quadruped_bot/urdf/parts/leg.xacro`; `Ch10/ros2_ws/src/my_quadruped_bot/urdf/common/robot_properties.xacro`; `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_controllerFSM.py`
- 평가: **정적 리뷰 수행, 실제 ROS 2/Gazebo 빌드 및 물리 보행 성공 여부 미검증; 통합 판정 보류**

## 학습 목표와 실제 코드의 차이

원고 10.8의 네 가지 단계(기립, 제자리 스텝, 속도/회전, 10N·50N 외란)를 '실패를 분석하는 실험'으로 운영한다. 안정적 보행 성공을 가정하지 말고 실제 pose·각도·토픽·명령자 수로 판정해야 한다.

## 문제 목록 및 권고 조치

| 우선순위 | 코드 문제 | 근거·영향 | 권고 |
|---|---|---|---|
| CRITICAL | 원고 예시 bridge 메시지 계약과 저장소가 다름 | 원고 10.8의 `/joint_commands` JointState→`gz.msgs.Model` 제어 예시는 실제 `ros_gz_bridge.yaml`의 ROS_TO_GZ 12개 Float64→gz.msgs.Double position command와 다르다. | 문서 실행은 저장소 YAML의 실제 12개 위치 제어 경로를 기준으로 한다. |
| HIGH | 기립·보행 성능 합격 증거 없음 | 현재 저장소에는 이 절에 대한 Gazebo 10/50N 외란 재현 로그, ground truth 위치·roll/pitch, 접촉 성공률·낙상 판정 등의 입증 자료가 확인되지 않는다. | 4개 시나리오의 사전/사후 상태·샘플 수·수치·로그·스크린샷·환경 버전을 확보. |
| HIGH | 동일 로봇 명령 토픽의 다중 발행과 TF 충돌 위험 | `stand_up`, `single_leg_mover`, `trot_gait_preview`, `quadruped_controller`, `trot_controllerFSM`이 겹치는 위치 명령을 발행할 수 있고 별도 노드가 odom→base_link TF를 중복 발행할 수 있다. | 단일 컨트롤러·단일 TF 권한으로 시나리오를 수행. |
| HIGH | 모델 제원·PID·접지 조건 검증 전 외란 실험 위험 | 현재 URDF 실제 링크와 IK 가정 불일치 상태에서 토크/주파수/속도를 높이면 불안정 원인을 분리할 수 없다. | 최소 속도·기립부터 시작하고 10/50N은 GUI 환경에서 실제 재현 가능한 힘 단위/적용 지속 시간 확인 후 순차 적용. |
| MEDIUM | 시뮬레이션 시간 구성 차이 | `9-5_simulation.launch.py`는 `use_sim_time` 인자를 선언하지만 `simulation.launch.py`의 `robot_state_publisher`는 이 파라미터가 명시되지 않는다. | `/clock`, use_sim_time 및 header timestamps 일관성 확인. |

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

1. [ ] 기립 10초 동안 roll·pitch·높이·관절명령 및 낙상 여부를 기록한다.
2. [ ] 제자리 스텝은 실제 발 높이·접지 이벤트·대각선 동기화로 평가한다.
3. [ ] 저속 전진/회전은 commanded vs ground-truth displacement/yaw 및 미끄럼을 비교한다.
4. [ ] 외란은 적용 힘(N), 방향, 지속시간, 모델 위치, 복귀 시간, 낙상 여부를 증거로 남긴다.
5. [ ] 해당 실행 환경(WSL2, ROS/Gazebo 배포판, Git SHA, 의존성) 기록
6. [ ] 실패/수정 전후의 테스트 로그 및 시뮬레이션 증거 저장
7. [ ] 10.1~10.7 선행 위험의 해결 여부 확인

**최종 의견:** 안전성과 재현성을 입증하는 실제 테스트 이전에는 '동작 완료/성공'으로 판정하지 않는다. 자세한 교육 절차는 [LAB_10_8_GUIDE_KO.md](LAB_10_8_GUIDE_KO.md) 참조.
