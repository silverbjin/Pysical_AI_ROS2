# 2장: ROS 2 통신 시스템

노드 → CLI → 토픽 → 서비스 → 커스텀 인터페이스 → 액션 → 론치 → QoS 순서로 학습한다. 첨부 원고의 **2.1~2.8절**에 대응하는 구현·코드 리뷰·실습 가이드 모음이다.

| 절 | 주제 | 실습 가이드 | 코드 리뷰·수정 보고서 |
|---|---|---|---|
| 2.1 | Node·객체지향 설계 | [LAB 2.1](docs/LAB_2_1_GUIDE_KO.md) | [REPORT 2.1](docs/SECTION_2_1_REPORT_KO.md) |
| 2.2 | CLI·turtlesim | [LAB 2.2](docs/LAB_2_2_GUIDE_KO.md) | [REPORT 2.2](docs/SECTION_2_2_REPORT_KO.md) |
| 2.3 | Topic | [LAB 2.3](docs/LAB_2_3_GUIDE_KO.md) | [REPORT 2.3](docs/SECTION_2_3_REPORT_KO.md) |
| 2.4 | Service | [LAB 2.4](docs/LAB_2_4_GUIDE_KO.md) | [REPORT 2.4](docs/SECTION_2_4_REPORT_KO.md) |
| 2.5 | Custom Interface | [LAB 2.5](docs/LAB_2_5_GUIDE_KO.md) | [REPORT 2.5](docs/SECTION_2_5_REPORT_KO.md) |
| 2.6 | Action | [LAB 2.6](docs/LAB_2_6_GUIDE_KO.md) | [REPORT 2.6](docs/SECTION_2_6_REPORT_KO.md) |
| 2.7 | Launch | [LAB 2.7](docs/LAB_2_7_GUIDE_KO.md) | [REPORT 2.7](docs/SECTION_2_7_REPORT_KO.md) |
| 2.8 | QoS | [LAB 2.8](docs/LAB_2_8_GUIDE_KO.md) | [REPORT 2.8](docs/SECTION_2_8_REPORT_KO.md) |

## 기본 실행

```bash
cd ~/Pysical_AI_ROS2/Ch02/ros2_ws
source /opt/ros/jazzy/setup.bash
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
source install/setup.bash
ros2 pkg prefix my_robot_system
ros2 pkg prefix my_robot_interfaces
```

원고의 `~/ros2_ws`가 아니라 저장소 안의 `Ch02/ros2_ws`를 권장한다. CLI/GUI 실습에는 `ros-jazzy-turtlesim`, 필요 시 `ros-jazzy-rqt-graph` 설치. ROS Humble은 `jazzy`를 적절히 교체한다.

### PR 검토 및 선행 병합

각 절은 **동일한 main 커밋 `94264bee`**에서 독립적으로 시작한 `feat/ch02-section-2-{1..8}` 브랜치에 있다. PR은 작성자가 직접 연다. 변경 파일 범위는 절별로 구분되어 있고 원본 main에는 쓰지 않았다.

**중요: 순서** — 이미 인터페이스 패키지에 액션이 등록되어 있지만 `action_msgs` 의존성이 없으므로 **2.5절 PR을 먼저 병합**한다. 다음으로 2.3절의 ROS 메시지·론치 의존성 선언을 병합한다. 이후 2.1·2.2·2.4절과 2.6~2.8절을 순차 검토한다. 2.6절은 2.5절에, 2.7·2.8절은 2.3절에 의존한다. PR 기준 브랜치를 `main`으로 유지하되 앞선 PR 병합 후 나머지 PR의 빌드 검증을 다시 수행한다.

## 검증 수준
- **완료**: GitHub 원본·첨부 원고 대조, 정적 위험 분석, 소스 패치, 절별 가이드/보고서 생성, 8개 원격 브랜치 Push 및 변경 파일 비교.
- **미완료**: Ubuntu/WSL ROS 2 통합 빌드, 실제 turtlesim GUI, rosidl 생성, 서비스·액션 취소, QoS 연결 테스트. 이 실행 환경에는 ROS 2/colcon이 없어 이를 PASS로 기재하지 않는다.
- **Acceptance**: `PENDING_RUNTIME_VERIFICATION`. 해당 절 보고서의 실행 명령과 예상 관찰값을 실제 환경에서 수행하고 stdout/stderr, exit code, 스크린샷을 보관한 뒤 최종 PASS 결정.

Ch12 문서 체계([Ch12 README](../Ch12/README.md))를 참고해 **도서 학습 목표 → 실행 절차 → 예상 관찰 → 실패 진단 → 검증 근거**로 구성했다.
