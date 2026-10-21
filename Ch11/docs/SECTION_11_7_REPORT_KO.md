# 11.7절 코드 리뷰 보고서 — 자율 매핑·지도 저장 프로젝트

- 기준: 첨부 『Physical AI 실무 가이드』 11.7절 원고와 2026-10-21 GitHub main 소스.
- 범위: 정적 코드·런치/설정·기존 단위 테스트 evidence. 구현 파일 변경 없음.
- **종합: 문서상 연결 구조 검토 완료 / 이번 세션 실제 ROS 2·Gazebo 실행 NOT_RUN.**

## 1. 점검 코드 및 현재 데이터 계약
- Ch11/ros2_ws/src/my_quadruped_bot/launch/mapping_total.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/launch/SLAM_simulation.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/config/exploration.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/mission/autonomous_explorer.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/mission/exploration_core.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/mission/map_artifacts.py
- Ch11/ros2_ws/src/my_quadruped_bot/worlds/maze_room.sdf

mapping_total.launch.py: Gazebo maze_room + EKF + FSM + IMU + stabilizer + SLAM; start_explorer 기본 false. readiness 확인 후 autonomous_explorer가 /scan 및 /scan_stabilized·/map·TF를 감시하며 /cmd_vel 제어. 저장은 종료·운영자 요청·BLOCKED 시 시도되고 PGM/YAML 품질 검토는 별도.

## 2. 판정
통합 월드·준비 확인·시간 제한 탐사·정지 및 지도 저장 구조가 구현되어 있다. Nav2/frontier 기반 완전 탐사가 아니라 bounded reactive 탐사이며 지도 완성 보장은 없다.

## 3. 발견사항
| 우선순위 | 확인한 소스/원고 차이 | 실습·운영 리스크 | 제안 및 검증 |
|---|---|---|---|
| HIGH | 원고의 타이머 지연 5초/8초만으로 센서·TF·SLAM readiness를 보장하기 어렵다. | 맵 생성 전 명령 발행으로 충돌 위험. | 현재 explorer가 준비 조건을 검사하고 start_explorer=false를 기본으로 유지; 실제 실행에서 readiness를 확인. |
| HIGH | 전진→장애물→랜덤 회전 로직은 미로 탐사 보장 알고리즘이 아니다. | 구석 갇힘, 미완성 지도 또는 무한 루프 가능. | 현재 BLOCKED/시간 제한·회전 관측 및 저장 결과를 사용하고 완전 탐사로 표현하지 않는다. |
| HIGH | 원고의 /scan_stabilized만 사용한 장애물 판단은 필터링 중 오래된 값이 남을 수 있다. | 장애물 누락 시 제어 명령이 계속 나갈 수 있다. | 원본 /scan을 안전 인지에 사용하고 신선도·회전 간격·명령 watchdog, 수동 중지 절차 검증. |
| MEDIUM | PGM/YAML이 생성되었다는 사실만으로 지도가 정확하거나 전역 커버리지가 충분하다고 볼 수 없다. | 실습 보고에 가짜 완성율 도입 가능. | 파일 검증 JSON의 quality_verified=false와 부분 지도 여부를 함께 보관. |

## 4. 검증 매트릭스
| 항목 | 결과 | 증빙 및 한계 |
|---|---|---|
| 소스/설정 리뷰 | DONE | GitHub main의 실제 코드·경로·토픽과 첨부 원고 비교 |
| 기존 테스트 결과 확인 | EVIDENCE ONLY | Ch11/evidence/autonomous_mapping_validation.json: 과거 104건 중 97 PASS, 7 SKIP; 3D/실제 탐사/자동 저장 NOT_RUN |
| 새 단위 테스트 실행 | NOT_RUN | GitHub 기반 정적 검토 세션이며 실행 재현 불가 |
| colcon 빌드 | NOT_RUN | 사용자 WSL2/ROS 2 실행 환경 접근 없음 |
| Gazebo 시뮬레이션·GUI·물리 성능 | NOT_RUN | 기존 evidence의 PASS를 이 항목에 전용하지 않음 |

최소 재현 명령(저장소 루트):

~~~bash
python3 -m unittest discover -s Ch11/tests -p test_autonomous_mapping.py -v
~~~

## 5. 출판 전 수용 기준
1. Ubuntu 24.04/ROS 2 Jazzy에서 Ch11만의 install overlay로 패키지 빌드.
2. 원고와 ROS 토픽·메시지 타입, 시각·QoS·TF 트리가 일치하는지 런타임 확인.
3. LAB 문서의 정상 경로와 실패 시나리오 모두 수행 후 로그·지도·화면 등을 증빙.
4. 원고에서 구현 범위를 넘는 성능·안전·정확도 주장은 제한사항으로 수정.

## 6. 참조
- 기존 상세 실습: [AUTONOMOUS_MAPPING_11_7_GUIDE_KO.md](AUTONOMOUS_MAPPING_11_7_GUIDE_KO.md)
- 이번 절별 가이드: [LAB_11_7_GUIDE_KO.md](LAB_11_7_GUIDE_KO.md)
