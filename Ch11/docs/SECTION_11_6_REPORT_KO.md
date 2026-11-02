# 11.6절 코드 리뷰 보고서 — 4족 SLAM 최적화·스캔 안정화

- 기준: 첨부 『Physical AI 실무 가이드』 11.6절 원고와 2026-10-21 GitHub main 소스.
- 범위: 정적 코드·런치/설정·기존 단위 테스트 evidence. 구현 파일 변경 없음.
- **종합: 문서상 연결 구조 검토 완료 / 이번 세션 실제 ROS 2·Gazebo 실행 NOT_RUN.**

## 1. 점검 코드 및 현재 데이터 계약
- Ch11/ros2_ws/src/my_quadruped_bot/launch/slam_optimized.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/launch/slam_3d.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/config/mapper_params_balanced.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/config/mapper_params_wide_search.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/scan_stabilizer.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sensors/scan_gate.py

기본 2D: /imu/data_raw + /scan → scan_stabilizer → /scan_stabilized → slam_toolbox. 대안 stabilizer:=tf는 EKF-TF 게이트. 3D 실습은 lidar_3d:=true+slam_3d.launch.py로 분리한다.

## 2. 판정
IMU-스캔 시간 매칭·기울기 게이트와 balanced/wide_search 튜닝 프로필이 있다. 넓은 검색이 실제 정합성을 높인다는 실험 수치는 없어 비교 과제로만 제시해야 한다.

## 3. 발견사항
| 우선순위 | 확인한 소스/원고 차이 | 실습·운영 리스크 | 제안 및 검증 |
|---|---|---|---|
| HIGH | 원고는 가장 최근 IMU 상태로 스캔을 버리는 간단한 필터를 제시한다. | 스캔 획득 시각과 IMU 시각이 다르면 동작 위상을 오판. | 현재 노드는 timestamp 최근접 매칭·IMU-LiDAR 장착 TF·최대 0.03초 시각 차이를 사용. |
| HIGH | IMU 방향의 유효성/중력 기준이 충족되지 않으면 스캔을 버린다. | 유효 스캔이 0Hz로 떨어져 SLAM 지도가 멈출 수 있다. | scan_stabilized 주기와 IMU orientation covariance, frame, time gap 진단. |
| MEDIUM | balanced/wide_search는 정량 최적값이 아니라 실습 시작 프로필. | 검색 범위를 키우면 CPU 부하·오매칭도 증가할 수 있다. | 같은 탐사 경로·동일 지표로 성능/처리율 비교 후 채택. |
| MEDIUM | 3D LiDAR→2D 투영은 수평 높이 가정을 사용한다. | 경사로·기복 지형에서는 바닥/장애물 투영 오판. | 별도 3D 투영 실습과 2D 기본 SLAM을 동시에 띄우지 않고 미검증 범위를 기재. |

## 4. 검증 매트릭스
| 항목 | 결과 | 증빙 및 한계 |
|---|---|---|
| 소스/설정 리뷰 | DONE | GitHub main의 실제 코드·경로·토픽과 첨부 원고 비교 |
| 기존 테스트 결과 확인 | EVIDENCE ONLY | Ch11/evidence/slam_optimization_validation.json: 과거 85건 중 79 PASS, 6 SKIP; 실측 튜닝 개선 NOT_VERIFIED |
| 새 단위 테스트 실행 | NOT_RUN | GitHub 기반 정적 검토 세션이며 실행 재현 불가 |
| colcon 빌드 | NOT_RUN | 사용자 WSL2/ROS 2 실행 환경 접근 없음 |
| Gazebo 시뮬레이션·GUI·물리 성능 | NOT_RUN | 기존 evidence의 PASS를 이 항목에 전용하지 않음 |

최소 재현 명령(저장소 루트):

~~~bash
python3 -m unittest discover -s Ch11/tests -p test_slam_optimization.py -v
~~~

## 5. 출판 전 수용 기준
1. Ubuntu 24.04/ROS 2 Jazzy에서 Ch11만의 install overlay로 패키지 빌드.
2. 원고와 ROS 토픽·메시지 타입, 시각·QoS·TF 트리가 일치하는지 런타임 확인.
3. LAB 문서의 정상 경로와 실패 시나리오 모두 수행 후 로그·지도·화면 등을 증빙.
4. 원고에서 구현 범위를 넘는 성능·안전·정확도 주장은 제한사항으로 수정.

## 6. 참조
- 기존 상세 실습: [SLAM_OPTIMIZATION_11_6_GUIDE_KO.md](SLAM_OPTIMIZATION_11_6_GUIDE_KO.md)
- 이번 절별 가이드: [LAB_11_6_GUIDE_KO.md](LAB_11_6_GUIDE_KO.md)
