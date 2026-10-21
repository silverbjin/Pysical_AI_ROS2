# 10장 — 보행 패턴 생성 및 제어

『Physical AI 실무 가이드』 10장의 원고(10.1~10.8절)와 저장소의 ROS 2 / Gazebo Harmonic 코드를 대조하여 작성한 **절별 실습 문서 허브**입니다.

## 절별 문서

| 절 | 학습 내용 | 코드 리뷰 | 따라하기 실습 |
|---|---|---|---|
| 10.1 | 보행 제어의 개요와 노드 구조 | [보고서](docs/SECTION_10_1_REPORT_KO.md) | [실습](docs/LAB_10_1_GUIDE_KO.md) |
| 10.2 | 보행 위상·접지 스케줄러 | [보고서](docs/SECTION_10_2_REPORT_KO.md) | [실습](docs/LAB_10_2_GUIDE_KO.md) |
| 10.3 | 발끝 스윙·스탠스 궤적 | [보고서](docs/SECTION_10_3_REPORT_KO.md) | [실습](docs/LAB_10_3_GUIDE_KO.md) |
| 10.4 | 해석적 IK·FK 교차 검사 | [보고서](docs/SECTION_10_4_REPORT_KO.md) | [실습](docs/LAB_10_4_GUIDE_KO.md) |
| 10.5 | 대각선 트롯·FSM | [보고서](docs/SECTION_10_5_REPORT_KO.md) | [실습](docs/LAB_10_5_GUIDE_KO.md) |
| 10.6 | 페이싱·바운딩·크롤 | [보고서](docs/SECTION_10_6_REPORT_KO.md) | [실습](docs/LAB_10_6_GUIDE_KO.md) |
| 10.7 | ROS 2 통합 제어 노드 | [보고서](docs/SECTION_10_7_REPORT_KO.md) | [실습](docs/LAB_10_7_GUIDE_KO.md) |
| 10.8 | Gazebo 보행 시나리오 검증 | [보고서](docs/SECTION_10_8_REPORT_KO.md) | [실습](docs/LAB_10_8_GUIDE_KO.md) |

각 절을 **별도의 브랜치·PR**로 제출했습니다. 이 README는 10.8절 PR에 포함되었으므로 다른 절 PR이 병합되기 전에는 일부 링크의 파일이 main에 없을 수 있습니다.

## 환경과 시작 명령

- 권장: Ubuntu 24.04/ROS 2 Jazzy/Gazebo Harmonic, Python 3와 NumPy, colcon.
- 모든 명령은 저장소 루트를 기준으로 설명합니다.
- Ch09/Ch11 등 다른 장의 install을 동시에 source하지 않고, 새 셸에서 Ch10 환경만 source합니다.

```bash
source /opt/ros/jazzy/setup.bash
cd Ch10/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_quadruped_bot
ros2 launch my_quadruped_bot simulation.launch.py
```

새 터미널에서 노드를 실행할 때도 동일하게 ROS 2와 `Ch10/ros2_ws/install/setup.bash`를 source합니다. Gazebo 기동만으로 로봇이 자동 보행하지는 않으며, 각 절의 실습 가이드를 참고해 **제어기를 하나씩** 실행해야 합니다.

## 먼저 읽을 위험 사항

1. **URDF와 IK 제원 불일치:** 실제 Xacro의 허벅지·종아리 길이 각 0.25m와 IK 코드의 각 0.20m 등 차이가 있습니다. URDF·FK 기준 조정 없이는 관절 명령을 검증 완료로 간주하지 않습니다.
2. **명령 토픽 구분:** 현행 브리지는 12개의 `std_msgs/msg/Float64`를 Gazebo joint position command에 매핑합니다. `/joint_states`는 관측 상태용이며 원고의 `/joint_commands` 예시를 그대로 사용하지 않습니다.
3. **통합 미완성:** `quadruped_controller_ros2.py`에는 정적 IK 더미값과 고정 발끝 위치가 남아 있고 `step_freq`/gait 파라미터 적용도 미완성입니다.
4. **실행 증거 구분:** 본 문서 세트는 GitHub 소스 기반 코드 리뷰이며, 이 문서 작성 작업으로 Gazebo 실제 보행 성공을 확인한 것은 아닙니다. 항목마다 PASS/FAIL/NOT RUN을 명시해 검증해야 합니다.

## 권장 학습 순서

- 10.1~10.3: 좌표계·명령 계약, 위상, 궤적의 수치 검증
- 10.4: IK와 **실제 URDF**의 독립 FK 비교·관절 한계 검증
- 10.5~10.7: 단일 제어권, FSM, 전이 및 ROS 2 토픽 계약 검증
- 10.8: 기립 → 제자리 보행 → 저속 주행/회전 → 외란 순으로 물리 실험과 Evidence 확보

> 본 README 및 16개 절별 문서는 **소스코드 수정 PR이 아닙니다**. 심각도가 높은 문제를 해결한 후 실제 실행 로그와 함께 재검증해야 합니다.
