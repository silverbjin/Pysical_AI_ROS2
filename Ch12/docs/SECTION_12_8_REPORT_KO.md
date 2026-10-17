# 12.8 구현·검증 보고서

## 구현 결과

ROS 2 Jazzy용 `quadruped_rl_ros` ament_python 패키지와 `rl_controller`, `mujoco_bridge`, 공통 launch를 추가했다. ROS 없이도 시험 가능한 `ros_core.py`에서 학습 환경의 계약을 읽고, 이름에 따른 12관절 매핑, 48차원 관측, 좌표 변환, 위치 잔차 후처리를 공유한다. 원고에서 생략된 선속도는 Odometry로 보완했다. 위치 명령을 effort 명령으로 전송하는 오류를 제거하고 Gazebo 기존 개별 Float64 cmd_pos와 MuJoCo named JointState 인터페이스로 분리했다.

기존 Ch11 파일은 수정하지 않았다. launch가 xacro 결과를 메모리에서 변환해 12개 위치 제어기의 PD/토크 한계와 초기 자세를 맞춘다. FR/FL/RR/RL 관절 순서와 관절 원점 회전(1.2/-2.4 rad), 축, 한계는 실제 URDF와 MuJoCo 모델을 비교하는 테스트로 확인했다. Gazebo의 추가 센서 관절은 정책 입력에서 이름으로 제외한다.

모니터링이 기본이며 enabled=true로 제어를 켠다. 초기 기립 램프, 속도·관절 한계, 실제 발행 타깃 이력, 센서 시각/프레임/유효성 검사, 명령 만료, 벽시계 watchdog, 추론 deadline, 중복 publisher 차단, 재무장 서비스를 구현했다. MuJoCo bridge는 clock·IMU·joint·odom을 같은 시각에 발행하고 오래되거나 역순인 위치 타깃을 거부한다. Rviz 명령 화살표도 제공한다.

## 실제 실행에서 발견하고 수정한 문제

1. NumPy 2 환경에서 Ubuntu cv2의 NumPy 1 ABI와 충돌했다. `[ros]`를 NumPy 1.26.4로 고정하고 ROS 전용 가상환경에서 학습·추론했다.
2. NumPy 2에서 저장한 과거 PPO ZIP을 NumPy 1에서 읽을 수 없었다. manifest에 NumPy 버전을 기록하고 불일치를 명확히 거부하도록 했다. ROS 환경에서 2,048 transition을 새로 학습해 두 시뮬레이터에 같은 번들을 사용했다.
3. Gazebo의 초기 관절값 0과 학습 nominal이 달라 추론 노드 로딩 중 몸통 높이가 0.120934m까지 떨어져 검증에 실패했다. 12개 JointPositionController의 initial_position을 [0,-0.5,1]×4로 맞췄고, 재실행 최저 높이는 0.375797m였다. 검증 기준을 낮추지 않았다.
4. 독립 리뷰가 찾은 동명 publisher 중복 감지, 기립 완료 시 발행하지 않은 명령을 이력에 넣던 문제, 센서 역순 시각과 bridge 타깃 시각 검증을 수정하고 회귀 테스트를 추가했다. 12.7의 mj_setConst가 실제 reset 상태를 바꾸던 문제도 별도 임시 MjData 사용으로 해결했다.

실패 기록은 `evidence/section12_8/*_before_*_fix/`에 보존했다. 최종 판정은 `mujoco/result.json`, `gazebo/result.json`을 사용한다.

## 실제 통합 검증

환경: Ubuntu-24.04 WSL, ROS 2 Jazzy, Gazebo Sim 8.11.0, MuJoCo 3.3.7, Gymnasium 1.2.1, SB3 2.7.1, PyTorch 2.5.1 CPU, NumPy 1.26.4. 서로 다른 ROS domain과 Gazebo partition을 사용했다.

| 항목 | MuJoCo | Gazebo |
|---|---:|---:|
| 정책 active 샘플 | 401 | 334 |
| 시뮬레이션 시간 기준 정책 주기 | 50Hz | 50Hz |
| 관측 차원 / 정책 관절 수 | 48 / 12 | 48 / 12 |
| 몸통 높이 최소~최대 | 0.378530~0.497873m | 0.375797~0.507642m |
| 명령 전달 및 만료 | PASS | PASS |
| pause 시 벽시계 감시·재개 | PASS | 해당 pause 기능 없음 |
| 강제 종료 없이 정상 종료 | PASS | PASS, server stop 응답 확인 |

Gazebo 8초 벽시계 구간에서 334개(약 41.75Hz)가 실행됐다. 시뮬레이션 시간이 벽시계보다 느리므로 50Hz 시뮬레이션 제어와 구분해야 한다. MuJoCo 최대 추론 1.48ms, Gazebo 최대 추론 13.04ms로 해당 실행에서는 20ms 예산 안이었다. 이는 하드 실시간 보장이 아니다.

독립 리뷰의 ROS 코어·실제 DDS·bridge·robust 검사 37개와 초기 자세 추가 검사 1개가 통과했다. 최종 전체 테스트·wheel 검증 결과는 `verification_summary_12_6_12_8.json` 및 각 로그에 기록한다.

## 범위와 한계

본 실행은 실제 물리 엔진과 ROS 토픽을 연결한 검증이며 mock으로 대체하지 않았다. 다만 짧은 PPO 모델로 검증했으므로 안정적인 전진 보행, 목표 도착, 장애물 회피 성능을 달성했다고 주장하지 않는다. Gazebo·MuJoCo는 위치 제어 이득과 접촉 동역학이 완전히 같지 않다. 실제 로봇·ONNX·LiDAR/goal 정책의 ROS 배포는 구현·실행 범위에 포함하지 않았다. 하드웨어 배포에는 별도의 인터페이스·제어 지연·비상 정지·충분한 성능 검증이 필요하다.
## 최종 패키지 확인

전체 테스트 147개가 34.23초에 통과했다(`green_final.log`). 0.8.0 wheel 빌드 후 `/tmp/ch12-final-wheel`에 별도 설치하고 해당 경로의 패키지를 실제 사용함을 검사했다. human viewer 100 step, 정상 close 및 별도 프로세스 Ctrl+C exit 130이 통과했다(`wheel/wheel_human.json`). locomotion에는 경로 마커가 없으므로 검증 도구의 마커 검사는 goal/avoidance 과제에만 적용하도록 수정했다. 수정 전 잘못된 마커 기대값 실패는 `wheel_viewer_before_profile_fix.log`에 보존했다. ROS 패키지도 최종 colcon 빌드를 수행했다.