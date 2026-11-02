# 3장: 로봇 모델링과 시뮬레이션 환경

> 교재: 『Physical AI 실무 가이드』 Ch03 · Ubuntu 24.04 / ROS 2 Jazzy / Gazebo Harmonic  
> 검토 기준: `main@9aafa9538352cc01f5e0154ad621f1200a27b0ef` (2026-10-20 KST)

이 장은 **URDF → 2축 로봇 팔 → Xacro → Gazebo World → Visual/Collision/Inertial → ros_gz_bridge → Spawn → 관절 제어 → 텔레오퍼레이션** 순서로 학습한다. 첨부 원고의 3.1~3.9절을 기준으로 실제 GitHub 소스와 대조했다.

| 절 | 주제 | 따라하기 실습 | 코드 리뷰·검증 |
|---|---|---|---|
| 3.1 | URDF 링크·관절·관성 | [LAB 3.1](docs/LAB_3_1_GUIDE_KO.md) | [REPORT 3.1](docs/SECTION_3_1_REPORT_KO.md) |
| 3.2 | 2-DOF 팔과 RViz | [LAB 3.2](docs/LAB_3_2_GUIDE_KO.md) | [REPORT 3.2](docs/SECTION_3_2_REPORT_KO.md) |
| 3.3 | Xacro·관성 매크로 | [LAB 3.3](docs/LAB_3_3_GUIDE_KO.md) | [REPORT 3.3](docs/SECTION_3_3_REPORT_KO.md) |
| 3.4 | Gazebo Harmonic World | [LAB 3.4](docs/LAB_3_4_GUIDE_KO.md) | [REPORT 3.4](docs/SECTION_3_4_REPORT_KO.md) |
| 3.5 | Visual/Collision/Inertial | [LAB 3.5](docs/LAB_3_5_GUIDE_KO.md) | [REPORT 3.5](docs/SECTION_3_5_REPORT_KO.md) |
| 3.6 | ROS-Gazebo Bridge | [LAB 3.6](docs/LAB_3_6_GUIDE_KO.md) | [REPORT 3.6](docs/SECTION_3_6_REPORT_KO.md) |
| 3.7 | Spawn 통합 Launch | [LAB 3.7](docs/LAB_3_7_GUIDE_KO.md) | [REPORT 3.7](docs/SECTION_3_7_REPORT_KO.md) |
| 3.8 | Joint Position Controller | [LAB 3.8](docs/LAB_3_8_GUIDE_KO.md) | [REPORT 3.8](docs/SECTION_3_8_REPORT_KO.md) |
| 3.9 | 터미널 텔레오퍼레이션 | [LAB 3.9](docs/LAB_3_9_GUIDE_KO.md) | [REPORT 3.9](docs/SECTION_3_9_REPORT_KO.md) |

**중요:** 표의 링크는 9개 절별 PR을 모두 main에 병합한 이후에 정상적으로 연결된다. 각 절은 동일 main에서 생성한 독립 브랜치이며, 3.9 브랜치의 이 README는 **마지막에 병합하는 것이 좋다**. 작성자가 PR 생성·병합을 직접 담당한다.

## 전용 워크스페이스 / 실행

```bash
cd ~/Pysical_AI_ROS2/Ch03/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install --packages-select my_robot_description
source install/setup.bash
ros2 pkg prefix my_robot_description
# 시각화 (3.2 수정 반영 후):
ros2 launch my_robot_description display.launch.py model:=two_dof_arm.urdf
# 통합 Gazebo:
ros2 launch my_robot_description spawn_robot.launch.py
# 다른 상호작용 터미널:
ros2 run my_robot_description simple_arm_teleop
```

`~/ros2_ws`는 원고의 예시 경로일 뿐 본 저장소 내의 기준은 `Ch03/ros2_ws`다. 다른 장의 `install/setup.bash`를 중첩 source하지 않는다. `ros2 pkg prefix my_robot_description`으로 실제 설치물을 점검한다.

## 권장 PR 병합 순서

1. **3.1·3.2·3.3**: URDF의 시각/충돌 정렬, RViz 실행 파일 경로, 실행 의존성, Xacro 관성 중심·EE 수정.
2. **3.4·3.5**: 개념 검증/실습 문서. 특히 3.5는 3.2·3.3 수정에 의존한다.
3. **3.6·3.7**: 시간 브리지 방향·TF 중복 제거, 스폰 론치 설정.
4. **3.8·3.9**: 관절 상태 출력·위치 제어와 TTY 조작. 3.9를 최종 병합해 이 색인을 main에 제공한다.

`two_dof_arm.urdf.xacro`는 3.3과 3.8에서 **서로 다른 부분**을 변경한다. PR 순서에 따라 GitHub 충돌 또는 의미적 차이가 발생할 수 있으므로 3.3 병합 후 3.8 branch를 최신 main으로 재검증한다. **이 색인 작성 시점에는 main에 반영하거나 병합하지 않았다.**

## 검증 수준과 인수 기준

- **실시**: 저장소 소스·원고 대조, 코드의 위험 경로 점검, 문제별 수정 커밋, 절별 실행 명령·예상 결과·실패 진단 명시, GitHub 원격 Push.
- **미실시**: 이 작업 환경에 `ros2`, `colcon`, `xacro`, `gz sim`이 없어 실제 URDF/Xacro 파서, colcon 빌드, RViz/ Gazebo GUI, joint_states/ TF /clock, PID 안정성, TTY 입력 검증은 실행하지 못했다.
- **최종 승인 조건**: Ubuntu 24.04+ROS 2 Jazzy+Gazebo Harmonic에서 각 보고서의 재현 명령을 실제 실행한 뒤 종료 코드·로그·관절값·GUI 스크린샷을 증거로 보존한다. 이후 `PENDING_RUNTIME_VERIFICATION`을 PASS/FAIL로 갱신한다.
- GitHub PR은 저자가 생성하고 검토한 뒤 병합한다. 브랜치 Push는 **런타임 Acceptance를 의미하지 않는다**.

참고: [Ch12 문서 구조](../Ch12/README.md).
