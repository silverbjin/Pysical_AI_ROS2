# SECTION 11.1 코드 리뷰 — 위치 추정·추측 항법

- 기준: 11.1절 첨부 도서 원고와 2026-10-21 GitHub main.
- **판정: 정적 소스 리뷰 완료 / 실제 ROS 2·Gazebo 검증 미완료.**
- 이번 작업은 코드 변경이 아니라 소스·설정·기존 evidence 점검 및 문서화이다.

## 1. 점검 코드
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/command_odometry_demo.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/sim_odometry.py
- Ch11/ros2_ws/src/my_quadruped_bot/my_quadruped_bot/odometry_observation.py
- Ch11/ros2_ws/src/my_quadruped_bot/launch/localization.launch.py

## 2. 실제 실행 계약
교육 데모: /demo/cmd_vel (Twist) → command_odometry_demo → /demo/odom (Odometry). 실제 시뮬레이션 추정: /simulation/odom → sim_odometry → /odom/raw → EKF → /odom. TF는 EKF가 odom → base_footprint 단독 발행.

## 3. 점검 결과
교육용 명령 적분과 운영용 Gazebo 모델 관측 경로가 분리되어 있다. 구조 검토는 통과, WSL2/Gazebo 런타임 검증은 보류.

| 우선순위 | 소스와 원고의 사실 | 위험 | 권고 |
|---|---|---|---|
| HIGH | 원고의 속도 명령 적분은 로봇 실제 변위를 측정하지 않는다. | 미끄러짐·접촉 오류가 있어도 위치 추정치가 변화한다. | /demo/odom은 학습에만 사용; 기본 SLAM에는 /odom/raw 관측과 EKF를 사용. |
| MEDIUM | 기존 명령 데모는 0.033초 타이머, 0.2초 명령 timeout, 인위적 slip_factor 0.9를 사용한다. | 단절·시뮬레이션 시간 역행 시 궤적 불연속이 생길 수 있다. | Gazebo 시간 리셋 시 재시작하고 stamp와 위치 변화를 기록한다. |
| MEDIUM | 원고의 누적 오차 예시는 특정 방향으로 매 표본 오차가 지속된다는 가정이다. | 반올림 노이즈와 지속적인 보행 슬립을 동일 원인으로 설명하기 어렵다. | 오차 원인을 모델 편향, 적분 오차, 외부 관측 부재로 나누어 기술한다. |
| MEDIUM | 과거 장의 overlay나 Gazebo 파티션과 충돌할 수 있다. | 소스가 동일해도 다른 로봇 모델/월드가 보일 수 있다. | Ch11 패키지 prefix, ROS_DOMAIN_ID, GZ_PARTITION 확인. |

## 4. 검증 근거와 상태
- 기존 보존 증빙: Ch11/evidence/verification_summary.json: 과거 15개 단위 테스트 PASS, ROS 빌드 NOT_RUN
- 새 테스트 실행: **NOT_RUN** (이번 실행 환경에 ROS 2/Gazebo 미설치, 사용자 WSL2 접근 없음).
- 새 colcon 빌드: **NOT_RUN**. 새 Gazebo 센서/보행/TF 동작: **NOT_RUN**.
- 과거 evidence의 PASS는 재실행 판정이 아니며 시뮬레이션 실증으로 간주하지 않는다.

저장소 루트에서 다시 점검할 테스트:

~~~bash
python3 -m unittest discover -s Ch11/tests -p test_localization_contract.py -v
~~~

## 5. 실제 실행 승인 조건
1. ROS 2 Jazzy에서 Ch11 단독 colcon build 성공, ros2 pkg prefix my_quadruped_bot이 Ch11 install을 가리킴.
2. 기대 토픽 타입/QoS/stamp, 단일 TF 발행자, 오류 입력 처리 확인.
3. 아래 LAB 문서 실습을 WSL2에서 실행하고 토픽 로그·화면·실패 재현을 별도 evidence로 보존.
4. 미검증 항목을 PASS로 주장하지 않는다.

## 6. 참조
- 기존 상세 구현/실습: [CH11_LOCALIZATION_FIX_REPORT_KO.md](CH11_LOCALIZATION_FIX_REPORT_KO.md)
- 이번 절별 실습: [LAB_11_1_GUIDE_KO.md](LAB_11_1_GUIDE_KO.md)
