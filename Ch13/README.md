# Ch13 복합 로봇 실습

- [13.2 모델링 실습](docs/LAB_13_2_GUIDE_KO.md)
- [13.2 변경·검증 보고서](docs/SECTION_13_2_REPORT_KO.md)
- [13.3 아키텍처 실습](docs/LAB_13_3_GUIDE_KO.md)
- [13.3 변경·검증 보고서](docs/SECTION_13_3_REPORT_KO.md)
- [13.4 시각 처리 실습](docs/LAB_13_4_GUIDE_KO.md)
- [13.4 변경·실제 검증 보고서](docs/SECTION_13_4_REPORT_KO.md)
- [13.4 네이티브 자체 리뷰](docs/SECTION_13_4_REVIEW_KO.md)
- [출처 명세](docs/REUSE_MANIFEST.md)

실행 패키지는 ros2_ws에 모여 있고 기존 장을 빌드하지 않아도 된다.
Gazebo/MuJoCo 실제 결과는 evidence/section_13_2와 evidence/section_13_3에 있다.
13.4 실행은 `evidence/section_13_4`에 성공·실패를 함께 보존한다. fixture 기하,
YOLO 인식, 국소 추적, 입력 상실 안전, 실제 파지의 성공을 서로 혼동하지 않는다.
시선 추적은 기본 OFF이며 Nav2·MoveIt·PPO 적재 보행·물리 파지는 포함하지 않는다.
