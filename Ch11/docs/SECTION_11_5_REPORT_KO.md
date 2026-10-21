# 11.5절 코드 리뷰 보고서 — SLAM Toolbox 2D 지도 생성

- 기준: 첨부 『Physical AI 실무 가이드』 11.5절 원고와 2026-10-21 GitHub main 소스.
- 범위: 정적 코드·런치/설정·기존 단위 테스트 evidence. 구현 파일 변경 없음.
- **종합: 문서상 연결 구조 검토 완료 / 이번 세션 실제 ROS 2·Gazebo 실행 NOT_RUN.**

## 1. 점검 코드 및 현재 데이터 계약
- Ch11/ros2_ws/src/my_quadruped_bot/launch/slam.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/launch/SLAM_simulation.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/config/mapper_params_online_async.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/slam_scan_filter.py
- Ch11/ros2_ws/src/my_quadruped_bot/rviz/slam.rviz

시뮬레이션+단일 EKF → /odom, odom→base_footprint 및 /scan. slam_scan_filter → /scan/slam → slam_toolbox (lifecycle activated) → /map + map→odom TF. 지도 저장은 nav2_map_server map_saver_cli 경로.

## 2. 판정
단일 TF 소유자, SLAM lifecycle 실행 파일 포함, 센서 정합성을 고려한 스캔 필터 경로가 존재한다. 실제 지도 생성·저장과 loop closure 품질은 새 실험에서 미확인.

## 3. 발견사항
| 우선순위 | 확인한 소스/원고 차이 | 실습·운영 리스크 | 제안 및 검증 |
|---|---|---|---|
| HIGH | 원고는 slam_toolbox 노드를 직접 시작하지만 Jazzy lifecycle 활성화 단계가 필요하다. | 노드는 떠 있어도 /map이 활성화되지 않을 수 있다. | 현재 slam.launch.py가 upstream online_async_launch.py와 lifecycle 인자를 사용하므로 이를 따른다. |
| HIGH | 원고 base_frame=base_link, scan_topic=/scan 예시는 현재 코드와 다르다. | TF lookup 실패와 빈 지도 가능. | 현재 base_footprint 및 /scan/slam 사용, 지도 TF chain map→odom→base_footprint→base_link 점검. |
| MEDIUM | SLAM_simulation.launch.py가 이미 localization을 포함한다. | 별도 localization.launch.py 실행 시 /odom과 TF가 중복 발행된다. | 추가 EKF 실행 금지; SLAM 노드도 한 인스턴스만. |
| MEDIUM | /map 생성과 지도 파일 저장을 동일 성공으로 취급하기 어렵다. | 지도 재료가 부족하거나 필터 스캔이 없어 부분 지도만 저장할 수 있다. | map_saver_cli 후 PGM/YAML 실재·해상도·픽셀과 월드 구조를 검사. |

## 4. 검증 매트릭스
| 항목 | 결과 | 증빙 및 한계 |
|---|---|---|
| 소스/설정 리뷰 | DONE | GitHub main의 실제 코드·경로·토픽과 첨부 원고 비교 |
| 기존 테스트 결과 확인 | EVIDENCE ONLY | Ch11/evidence/slam_mapping_validation.json: 과거 73건 중 67 PASS, 6 SKIP; colcon·지도 저장 NOT_RUN |
| 새 단위 테스트 실행 | NOT_RUN | GitHub 기반 정적 검토 세션이며 실행 재현 불가 |
| colcon 빌드 | NOT_RUN | 사용자 WSL2/ROS 2 실행 환경 접근 없음 |
| Gazebo 시뮬레이션·GUI·물리 성능 | NOT_RUN | 기존 evidence의 PASS를 이 항목에 전용하지 않음 |

최소 재현 명령(저장소 루트):

~~~bash
python3 -m unittest discover -s Ch11/tests -p test_slam_mapping.py -v
~~~

## 5. 출판 전 수용 기준
1. Ubuntu 24.04/ROS 2 Jazzy에서 Ch11만의 install overlay로 패키지 빌드.
2. 원고와 ROS 토픽·메시지 타입, 시각·QoS·TF 트리가 일치하는지 런타임 확인.
3. LAB 문서의 정상 경로와 실패 시나리오 모두 수행 후 로그·지도·화면 등을 증빙.
4. 원고에서 구현 범위를 넘는 성능·안전·정확도 주장은 제한사항으로 수정.

## 6. 참조
- 기존 상세 실습: [SLAM_MAPPING_11_5_GUIDE_KO.md](SLAM_MAPPING_11_5_GUIDE_KO.md)
- 이번 절별 가이드: [LAB_11_5_GUIDE_KO.md](LAB_11_5_GUIDE_KO.md)
