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

# Ch13 — 독립형 4족 + 6DoF 팔 실습 (13.1)

[한글 단계별 실습](docs/LAB_13_1_GUIDE_KO.md)부터 시작한다. 승인 설계는 [설계서](docs/SECTION_13_1_DESIGN_KO.md), 실행 계획은 [계획서](docs/IMPLEMENTATION_PLAN_KO.md)에 있다.

12개 다리 + 6개 팔 + 2개 손가락 = **20개 가동 관절**. 하나의 관절 계약과 중재기를 사용하고, Gazebo 또는 MuJoCo 중 하나만 실행한다. Ch05~Ch12를 빌드하거나 source하지 않는다.

검증 경계: 두 엔진의 모델·ROS 상태·명령 연결과 종료를 실제 실행했다. MuJoCo fixture 파지는 성공했지만 Gazebo fixture 파지는 실패했다. 이는 일반 집기·운반·배치, MoveIt 2, 통합 ros2_control 또는 안정 PPO 보행의 성공을 뜻하지 않는다.

- [변경·리뷰 보고서](docs/CHANGE_REPORT_KO.md)
- [재사용 출처·해시](docs/REUSE_MANIFEST.md)
- [기계 판독 검증 결과](evidence/verification_summary.json)
- [MuJoCo 물리 결과](evidence/mujoco/result.json), [Gazebo 결과](evidence/gazebo/result.json)

검증기는 `PARTIAL`을 실패 은폐 없이 기록한다. Gazebo 통합 검사가 PASS여도 `physical_grasp.status`는 별도 판정이다.
