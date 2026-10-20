# Ch01: ROS 2 기초 실습

이 저장소의 소스 주석에서 명시적으로 확인된 절은 **1.6 및 1.7**이다. 1.1~1.5절의 절 번호가 붙은 코드가 없어 문서를 임의 생성하지 않았다.

| 절 | 실습 주제 | 리뷰 | 실습 가이드 |
|---|---|---|---|
| 1.6 | 노드, 타이머, 로거 및 보조 패키지 | [리뷰](docs/SECTION_1_6_REPORT_KO.md) | [실습](docs/LAB_1_6_GUIDE_KO.md) |
| 1.7 | Twist 토픽 발행 및 의존성 | [리뷰](docs/SECTION_1_7_REPORT_KO.md) | [실습](docs/LAB_1_7_GUIDE_KO.md) |

`ref/`: `my_first_package` (실제 ROS 패키지 루트). `robot_ws/src/my_robot_controller`: `test_node`, `robot_ws/src/robot_monitor`: `battery_node`. `robot_ws/src/examples`: ROS 2 공식 예제 모음이므로 입문 절의 필수 빌드 대상이 아니다. 선택 빌드 또는 별도 워크스페이스를 권장한다.

**검증 주의:** 2026-10-20 작성된 리뷰는 정적 코드 확인 기반이며 실제 ROS 2/colcon 실행 환경이 없어 빌드·그래프·DDS 성공은 미검증이다. Ch12에서 작성한 검증과 실습 가이드의 구분 방식을 참고하였다. 실제 실행 후 각 보고서의 NOT_RUN을 증거로 갱신해야 한다.
