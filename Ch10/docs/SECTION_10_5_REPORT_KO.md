# 10.5절 코드 리뷰 보고서 — 트롯 보행과 FSM 통합

- 작성/정적 검토: 2026-10-21 KST
- 원고 범위: 첨부 『Physical AI 실무 가이드』 10.5절
- 소스 기준: `silverbjin/Pysical_AI_ROS2` main (작업 시작 `bab76f6ca7df0bda6efd8882c1a698561707e51d`)
- 파일: `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_controllerFSM.py`; `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trajectory_generator.py`; `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/inverse_kinematics.py`; `Ch10/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/trot_gait_preview.py`; `Ch10/ros2_ws/test_gait_fsm.py`
- 평가: **정적 리뷰 수행, 실제 ROS 2/Gazebo 빌드 및 물리 보행 성공 여부 미검증; 통합 판정 보류**

## 학습 목표와 실제 코드의 차이

FL/RR과 FR/RL의 대각선 대칭 궤적, 기립→정지→보행→감속/복구 FSM, 선속도/요속도의 발끝 변환을 연결한다. 현행 `trot_controllerFSM` 엔트리포인트는 존재하지만 움직임 성공은 검증되지 않았다.

## 문제 목록 및 권고 조치

| 우선순위 | 코드 문제 | 근거·영향 | 권고 |
|---|---|---|---|
| CRITICAL | 실제 URDF와 IK 제원의 불일치가 통합 보행에도 전파 | FSM의 기준점 y=±0.19m, hip 오프셋 y=±0.15m는 Xacro `hip_offset_y=0.10m`, thigh joint 원점 y_reflect×0.05m 및 0.25m 링크 모델과 별도 기준을 사용한다. | 시뮬레이터의 정확한 joint FK를 기준으로 오프셋과 leg-local 타깃을 재설계. |
| HIGH | 정지 명령 이후의 안전 보장 없음 | FSM은 이전 속도를 마지막 주기 완료까지 유지하지만 `/cmd_vel` 수신 만료 watchdog이 없고, 장시간 입력 중단 시 원격 명령 유실을 구분하지 않는다. | 마지막 수신 시각·명령 만료·감속·네 다리 착지 확인을 정의. |
| HIGH | crawl에서 잘못된 stance 시간 | `TrotController.run_step()`의 `stance_time=1/(2*current_freq)`는 duty=0.5 가정으로, crawl duty=0.75와 어긋난다. | `T_stance=duty_factor/frequency`를 사용하고 전환 시 궤적 연속성 검증. |
| MEDIUM | 원고 실행 패키지명과 실제 패키지명 불일치 | 원고 `ros2 launch my_quadruped_robot ...`, `ros2 run my_quadruped_control trot_controller`는 저장소의 `my_quadruped_bot`과 `trot_controllerFSM` 엔트리포인트와 다르다. | Ch10 빌드·source 후 실제 명령으로 교체. |
| MEDIUM | 테스트의 독립적 물리 검증 없음 | `test_gait_fsm.py`는 assert 부족, 불가능한 조건문, mock 의존성 주입 순서 등의 문제가 있어 전진·회전·복구 성공을 입증하지 않는다. | 독립 단위테스트와 Gazebo 실제 접지·몸체 pose 증거 필요. |

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

1. [ ] 기립 중 발 위치·관절 목표가 불연속적으로 점프하지 않는지 기록한다.
2. [ ] FL/RR와 FR/RL 쌍의 위상을 로그와 관절 목표로 교차 확인한다.
3. [ ] 짧은 이동·정지 후 네 발이 지면에 붙는지, 이동량은 실제 Gazebo 모델에서 계측한다.
4. [ ] 해당 실행 환경(WSL2, ROS/Gazebo 배포판, Git SHA, 의존성) 기록
5. [ ] 실패/수정 전후의 테스트 로그 및 시뮬레이션 증거 저장
6. [ ] 10.1~10.7 선행 위험의 해결 여부 확인

**최종 의견:** 안전성과 재현성을 입증하는 실제 테스트 이전에는 '동작 완료/성공'으로 판정하지 않는다. 자세한 교육 절차는 [LAB_10_5_GUIDE_KO.md](LAB_10_5_GUIDE_KO.md) 참조.
