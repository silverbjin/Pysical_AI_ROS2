# 11.3절 코드 리뷰 보고서 — LiDAR 거리·장애물 감지

- 기준: 첨부 『Physical AI 실무 가이드』 11.3절 원고와 2026-10-21 GitHub main 소스.
- 범위: 정적 코드·런치/설정·기존 단위 테스트 evidence. 구현 파일 변경 없음.
- **종합: 문서상 연결 구조 검토 완료 / 이번 세션 실제 ROS 2·Gazebo 실행 NOT_RUN.**

## 1. 점검 코드 및 현재 데이터 계약
- Ch11/ros2_ws/src/my_quadruped_bot/config/ros_gz_bridge.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/lidar_safety.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/lidar_processing.py
- Ch11/ros2_ws/src/my_quadruped_bot/launch/lidar_safety.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/urdf/robot.urdf.xacro

/scan (LaserScan, lidar_link, BEST_EFFORT) → lidar_safety → /lidar_safety/status (String 안의 JSON). status=OBSTACLE/CLEAR/UNKNOWN/STALE. 경고 노드는 /cmd_vel을 발행하지 않음.

## 2. 판정
동적 angle_min/angle_increment를 통한 전방 ±30° 계산, NaN/Inf·측정 영역·수신 시간 검사가 구현되어 있다. 경고 동작과 실제 자동 정지는 구별해야 한다.

## 3. 발견사항
| 우선순위 | 확인한 소스/원고 차이 | 실습·운영 리스크 | 제안 및 검증 |
|---|---|---|---|
| HIGH | 원고 11.3.3에는 AEB(긴급 제동) 확장 가능이라고 표현되어 있다. | 현재 lidar_safety는 로그와 status만 발행하며 /cmd_vel 자동 정지가 없다. | 책에서는 위험 경고 노드로 명명하고 실물/자율 정지의 안전 인증과 분리한다. |
| HIGH | 전방을 배열 절반으로 정하는 예제는 각도 범위가 달라지면 틀리다. | 0~2π, 역방향 스캔 및 부분 FoV의 전방 인덱스를 오판할 수 있다. | 실제 lidar_processing.py의 각도 정규화·시야 검증을 설명한다. |
| MEDIUM | 유효 반사점 없이 Inf만 있는 구간과 결손 입력은 안전이 아님. | 무조건 CLEAR로 처리하면 근거리 장애물을 놓칠 수 있다. | UNKNOWN 및 STALE 상태를 관찰하고 데이터가 없을 때 로봇을 전진시키지 않는다. |
| MEDIUM | 프레임과 시뮬레이션 타임의 일관성이 필요하다. | 잘못된 lidar_link 방향 또는 Gazebo 일시정지는 잘못된 판단을 만든다. | frame_id, scan 시각, timeout=0.5초, TF를 확인한다. |

## 4. 검증 매트릭스
| 항목 | 결과 | 증빙 및 한계 |
|---|---|---|
| 소스/설정 리뷰 | DONE | GitHub main의 실제 코드·경로·토픽과 첨부 원고 비교 |
| 기존 테스트 결과 확인 | EVIDENCE ONLY | Ch11/evidence/lidar_processing_validation.json: 과거 50건 중 44 PASS, 6 SKIP, Gazebo NOT_RUN |
| 새 단위 테스트 실행 | NOT_RUN | GitHub 기반 정적 검토 세션이며 실행 재현 불가 |
| colcon 빌드 | NOT_RUN | 사용자 WSL2/ROS 2 실행 환경 접근 없음 |
| Gazebo 시뮬레이션·GUI·물리 성능 | NOT_RUN | 기존 evidence의 PASS를 이 항목에 전용하지 않음 |

최소 재현 명령(저장소 루트):

~~~bash
python3 -m unittest discover -s Ch11/tests -p test_lidar_processing.py -v
~~~

## 5. 출판 전 수용 기준
1. Ubuntu 24.04/ROS 2 Jazzy에서 Ch11만의 install overlay로 패키지 빌드.
2. 원고와 ROS 토픽·메시지 타입, 시각·QoS·TF 트리가 일치하는지 런타임 확인.
3. LAB 문서의 정상 경로와 실패 시나리오 모두 수행 후 로그·지도·화면 등을 증빙.
4. 원고에서 구현 범위를 넘는 성능·안전·정확도 주장은 제한사항으로 수정.

## 6. 참조
- 기존 상세 실습: [LIDAR_SAFETY_11_3_4_GUIDE_KO.md](LIDAR_SAFETY_11_3_4_GUIDE_KO.md)
- 이번 절별 가이드: [LAB_11_3_GUIDE_KO.md](LAB_11_3_GUIDE_KO.md)
