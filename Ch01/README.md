# 1장: ROS 2 시작하기 (Ubuntu 24.04 / ROS 2 Jazzy)

**원고 기준 절별 검토:** 2026-10-20. 1.1~1.7절의 실습 및 리뷰. 각 절의 문서는 서로 독립적인 `feat/ch01-section-1-N` 브랜치에서 작성했으며, 개별 PR을 병합해야 이 README의 **상대 링크**가 main에서 모두 동작한다.

| 절 | 원고에서 다루는 내용 | 실습 가이드 | 코드·원고 리뷰 |
|---|---|---|---|
| 1.1 | ROS 1/ROS 2, DDS, QoS | [1.1 실습](docs/LAB_1_1_GUIDE_KO.md) | [1.1 리뷰](docs/SECTION_1_1_REPORT_KO.md) |
| 1.2 | Jazzy 설치, Ubuntu 24.04, talker/listener | [1.2 실습](docs/LAB_1_2_GUIDE_KO.md) | [1.2 리뷰](docs/SECTION_1_2_REPORT_KO.md) |
| 1.3 | Node, Topic, Service, Action, Interface | [1.3 실습](docs/LAB_1_3_GUIDE_KO.md) | [1.3 리뷰](docs/SECTION_1_3_REPORT_KO.md) |
| 1.4 | Workspace, colcon, underlay/overlay | [1.4 실습](docs/LAB_1_4_GUIDE_KO.md) | [1.4 리뷰](docs/SECTION_1_4_REPORT_KO.md) |
| 1.5 | ament_python 패키지 생성·빌드 | [1.5 실습](docs/LAB_1_5_GUIDE_KO.md) | [1.5 리뷰](docs/SECTION_1_5_REPORT_KO.md) |
| 1.6 | SimpleController와 1Hz Heartbeat | [1.6 실습](docs/LAB_1_6_GUIDE_KO.md) | [1.6 리뷰](docs/SECTION_1_6_REPORT_KO.md) |
| 1.7 | package.xml, setup.py, rosdep | [1.7 실습](docs/LAB_1_7_GUIDE_KO.md) | [1.7 리뷰](docs/SECTION_1_7_REPORT_KO.md) |

## 기존 소스 대응

- `Ch01/robot_ws/src/examples`: 공식 ROS 2 예제 복제본, **1.4절**에서 최소 단일 패키지로 사용.
- `Ch01/robot_ws/src/my_robot_controller`: **1.5~1.7절의 주교재 패키지**. `ros2 run my_robot_controller test_node`이며, 실제 Node 이름은 `/my_robot_node`.
- `Ch01/robot_ws/src/robot_monitor`: 절 번호가 없는 가상 배터리 보조 실습. 1.6절의 응용 선택 과제.
- `Ch01/ref/my_first_package`: 별도 기초 ROS 2 패키지 예제. 파일 주석에 1.6·1.7이 언급되지만 **제공된 원고의 주교재 코드 경로는 아님**. `simple_node`와 `cmd_publisher`는 선택 확장 예제로만 다룬다.

## 중요 교정

- 1.4/1.5/1.6 원고 `source install/setup.` → `source install/setup.bash`.
- 1.5 원고 `--node_name` → Jazzy 공식 CLI `--node-name`.
- 1.5 최초 생성 패키지의 `simple_controller`와 1.6 완성본의 `test_node`를 구분한다.
- 1.7절은 **의존성 관리**이며 Twist 발행은 주 실습이 아니다.
- 실제 ROS 2/colcon 실행은 리뷰 환경에 없으므로 모든 문서의 정적 리뷰와 런타임 검증 상태를 분리한다.

**PR 권장 순서:** 1.1→1.2→1.3→1.4→1.5→1.6→1.7. 절별 브랜치는 main에서 독립적으로 출발했다. PR은 작성자가 직접 생성·검토한다.
