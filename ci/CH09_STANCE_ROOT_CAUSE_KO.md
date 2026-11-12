# Ch09 stand_up 후방 Pitch 약 40.7° — 원인 경계 진단 및 A/B

## 결론 (시뮬레이션 한정)

- [Issue #129](https://github.com/silverbjin/Pysical_AI_ROS2/issues/129)에 기록된 원본 기립 실패의 핵심은 옆으로 구르는 Roll이 아니라 **후방 Pitch**다.
- 진단 A는 **원본** `stand_up.py`를 수정하지 않고 실제 Gazebo와 12개 ROS 관절 명령/관절 상태 및 계측용 base odometry를 수집했다.
- 대조 B는 동일 월드·URDF·물리 충돌·위치 제어기와 동일 최종 12개 목표각에서 **명령만 6초 smoothstep 보간**했다. B의 보간 노드는 CI 전용이고 배포한 교재 패키지에 포함되지 않는다.
- 최종 판단: 원본의 즉시 step 명령이 후방 Pitch 기울기와 앞발 지면 이탈을 유발하는 주요 원인임을 한 번의 독립 A/B 비교에서 강하게 지지한다. **실제 접촉력 인과관계, 다른 초기 상태에서의 재현성은 별도 검수**다.

## 재현 증거

| 확인 항목 | A — 원본 즉시 명령 | B — 6초 보간 |
|---|---:|---:|
| ROS 목표 관절 | 힙 0 / Thigh −0.6 / Calf +1.2 | 동일 |
| 12개 명령 관측 | 각 138개 | 각 160개 |
| 최종 Pitch | −40.7017° | −0.4567° |
| 최종 Roll | 거의 0° | 거의 0° |
| 몸체 z | 0.41858m | 0.42330m |
| 전방 Thigh 실제 | −0.59076rad | 약 −0.6175rad |
| 후방 Thigh 실제 | −0.76575rad | 약 −0.6205rad |
| 전방 Calf 실제 | 1.20726rad | 약 1.1518rad |
| 후방 Calf 실제 | 1.08413rad | 약 1.1272rad |
| 앞발 충돌구 중심 월드 z (URDF FK) | 약 0.26382m | 약 0.020m |
| 뒷발 충돌구 중심 월드 z (URDF FK) | 약 0.020m | 약 0.020m |

원본에서 모든 네 발의 **목표** 위치는 몸체 대비 z 약 −0.412668m로 대칭이다. A는 실제 관절이 앞뒤로 불균형하게 반응하면서 몸체가 뒤로 기울고 앞발이 들렸다. B에서는 네 발이 지면 근처로 복귀했다. 발끝 월드 z는 *실제 몸체 odometry + 관절 측정값 + 원본 URDF FK*의 계산치이며 **접촉력 직접 계측은 아니다**.

- A [공개 CI #43241164843](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43241164843), [원본 Artifact](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43241164843/artifacts/13955190818)
- B [공개 CI #43242254718](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43242254718), [원본 Artifact](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43242254718/artifacts/13955796553)
- 검수기는 명확히 `DIAG_CAPTURED`만 출력한다. **기립 PASS가 아니다.**

## 후속 최소 수정 방향 (교재 별도 PR)

원본 `Ch09/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/stand_up.py`에만 현재 `/joint_states`에서 시작각을 얻고, 동일 목표각까지 6초 smoothstep 보간하는 기능을 최소 추가한다. 10Hz 발행 주기·목표각·토픽·제어기·URDF·마찰은 유지한다. 센서 미도착 시 임의 명령을 발행하지 않고 한 번 오류를 알려야 한다.

**완료 조건:** 수정된 원본 `ros2 run my_quadruped_bot stand_up`을 실제 Gazebo에서 실행해 이전과 동일한 기립 자세 계약(z ≥0.12m, Roll/Pitch ≤20°, 4초 높이 흔들림 ≤0.08m, 수평 이동 ≤0.2m)을 통과해야 한다. 12관절 메시지 PASS나 B의 보간 결과만으로 완료 처리하지 않는다. WSL2 GUI 및 실제 발 접촉력은 NOT_RUN.
