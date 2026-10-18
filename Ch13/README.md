# Ch13 — 독립형 4족 + 6DoF 팔 실습 (13.1)

[한글 단계별 실습](docs/LAB_13_1_GUIDE_KO.md)부터 시작한다. 승인 설계는 [설계서](docs/SECTION_13_1_DESIGN_KO.md), 실행 계획은 [계획서](docs/IMPLEMENTATION_PLAN_KO.md)에 있다.

12개 다리 + 6개 팔 + 2개 손가락 = **20개 가동 관절**. 하나의 관절 계약과 중재기를 사용하고, Gazebo 또는 MuJoCo 중 하나만 실행한다. Ch05~Ch12를 빌드하거나 source하지 않는다.

검증 경계: 두 엔진의 모델·ROS 상태·명령 연결과 종료를 실제 실행했다. MuJoCo fixture 파지는 성공했지만 Gazebo fixture 파지는 실패했다. 이는 일반 집기·운반·배치, MoveIt 2, 통합 ros2_control 또는 안정 PPO 보행의 성공을 뜻하지 않는다.

- [변경·리뷰 보고서](docs/CHANGE_REPORT_KO.md)
- [재사용 출처·해시](docs/REUSE_MANIFEST.md)
- [기계 판독 검증 결과](evidence/verification_summary.json)
- [MuJoCo 물리 결과](evidence/mujoco/result.json), [Gazebo 결과](evidence/gazebo/result.json)

검증기는 `PARTIAL`을 실패 은폐 없이 기록한다. Gazebo 통합 검사가 PASS여도 `physical_grasp.status`는 별도 판정이다.
