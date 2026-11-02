# 11.4절 코드 리뷰 보고서 — EKF 오도메트리 보정

- 기준: 첨부 『Physical AI 실무 가이드』 11.4절 원고와 2026-10-21 GitHub main 소스.
- 범위: 정적 코드·런치/설정·기존 단위 테스트 evidence. 구현 파일 변경 없음.
- **종합: 문서상 연결 구조 검토 완료 / 이번 세션 실제 ROS 2·Gazebo 실행 NOT_RUN.**

## 1. 점검 코드 및 현재 데이터 계약
- Ch11/ros2_ws/src/my_quadruped_bot/config/ekf.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/config/ekf_command_lab.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/config/ekf_command_lab_accel.yaml
- Ch11/ros2_ws/src/my_quadruped_bot/launch/localization.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/launch/ekf_lab.launch.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/leg_odometry.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/ekf_lab_imu.py

운영: /simulation/odom → /odom/raw + /imu/data_raw → ekf_filter_node → /odom, TF odom→base_footprint. 분리된 교육: /cmd_vel → leg_odometry → /ekf_lab/raw + /ekf_lab/imu → ekf_lab_filter → /ekf_lab/filtered; 교육 필터 publish_tf=false.

## 2. 판정
운영 EKF와 명령 적분 교육용 EKF가 분리되어 중복 TF를 피한다. 운영 입력은 시뮬레이터 관측 기반이므로 실물 보행 슬립 오차 보정 검증이라고 해석할 수 없다.

## 3. 발견사항
| 우선순위 | 확인한 소스/원고 차이 | 실습·운영 리스크 | 제안 및 검증 |
|---|---|---|---|
| HIGH | 원고의 다리 오도메트리는 실제 관절·발 접촉을 사용하지 않고 cmd_vel 적분에 기반한다. | 이름만 보고 leg odometry 센서의 실측 개선으로 오해할 수 있다. | 교육 실습 /ekf_lab/raw와 시뮬레이터 기반 기본 /odom/raw를 구분한다. |
| HIGH | 운영 /odom/raw는 Gazebo 모델 자체 관측을 사용한다. | 원시값에 참값 유사 정보가 포함되므로 EKF 출력 정확도를 독립 검증할 수 없다. | 진짜 독립 평가에는 별도 ground truth 및 접촉/다리 운동학 관측 필요. |
| MEDIUM | 과거 원고 imu0=/imu/data, base_link 기준 설명과 현재 설정이 불일치한다. | 토픽 타입 오류 또는 TF 중복 발행 가능. | 현재 imu0=/imu/data_raw, base_link_frame=base_footprint 및 단일 EKF TF 발행만 허용. |
| MEDIUM | imu0_config의 가속도 on/off·공분산은 상황에 따라 다르다. | 정속 슬립이나 bias가 있는 경우 IMU만으로 이동 거리 보정이 보장되지 않는다. | with/without acceleration 사례를 정량 비교하되 무조건 정확도 향상이라 기술하지 않는다. |

## 4. 검증 매트릭스
| 항목 | 결과 | 증빙 및 한계 |
|---|---|---|
| 소스/설정 리뷰 | DONE | GitHub main의 실제 코드·경로·토픽과 첨부 원고 비교 |
| 기존 테스트 결과 확인 | EVIDENCE ONLY | Ch11/evidence/ekf_lab_validation.json: 과거 61건 중 55 PASS, 6 SKIP; 그래프 스모크는 합성 CSV, WSL2 Gazebo NOT_RUN |
| 새 단위 테스트 실행 | NOT_RUN | GitHub 기반 정적 검토 세션이며 실행 재현 불가 |
| colcon 빌드 | NOT_RUN | 사용자 WSL2/ROS 2 실행 환경 접근 없음 |
| Gazebo 시뮬레이션·GUI·물리 성능 | NOT_RUN | 기존 evidence의 PASS를 이 항목에 전용하지 않음 |

최소 재현 명령(저장소 루트):

~~~bash
python3 -m unittest discover -s Ch11/tests -p test_ekf_lab.py -v
~~~

## 5. 출판 전 수용 기준
1. Ubuntu 24.04/ROS 2 Jazzy에서 Ch11만의 install overlay로 패키지 빌드.
2. 원고와 ROS 토픽·메시지 타입, 시각·QoS·TF 트리가 일치하는지 런타임 확인.
3. LAB 문서의 정상 경로와 실패 시나리오 모두 수행 후 로그·지도·화면 등을 증빙.
4. 원고에서 구현 범위를 넘는 성능·안전·정확도 주장은 제한사항으로 수정.

## 6. 참조
- 기존 상세 실습: [EKF_11_4_GUIDE_KO.md](EKF_11_4_GUIDE_KO.md)
- 이번 절별 가이드: [LAB_11_4_GUIDE_KO.md](LAB_11_4_GUIDE_KO.md)
