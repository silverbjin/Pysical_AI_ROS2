# 13.1 변경·리뷰 보고서

## 범위와 현재 결론

승인 계획 `71b3c441904e25b63e28188393356f48282698d6`에서 직접 구현했다. 13.2/13.3 브랜치를 덮어쓰거나 합치지 않았고, 13.1 전용 `feat/ch13-section-13-1`에 작업했다. Ch05~Ch12 원본 diff는 없어야 한다.

통합 패키지, 모델, 실제 두 엔진의 상태·명령 연결은 구현·실행됐다. MuJoCo 제한 파지는 성공했지만 Gazebo 파지는 실패했다. 따라서 전체 검증 상태는 PARTIAL이며, 두 엔진에서 모두 물리 파지를 완성했다는 보고가 아니다.

## 주요 변경

1. 순수 Python ch13_sim_core와 ROS ch13_robot_description/ch13_control의 독립 설치 경계를 만들었다. 20관절 YAML 계약, Xacro와 MJCF의 이름·축·한계·장착 변환 검사를 추가했다.
2. 다리·팔·그리퍼 생산자와 전체 중재 출력을 분리했다. 배열 순서가 바뀌어도 이름으로 정렬하며 잘못된 그룹/중복/누락/NaN/소유자 충돌/미래·역순·만료 명령을 거부한다.
3. 상태 검증 노드만 /joint_states를 발행하고, 엔진 어댑터가 clock/raw state/odom을 소유한다. Gazebo는 20개 개별 위치 제어기와 네이티브 router, GZ_TO_ROS 관측 브리지만 쓴다.
4. 실제 MuJoCo의 접촉·물체 위치·TCP 상대 변위를 사용한 파지 판정을 추가했다. 상태 snapshot은 복사본이며 joint/actuator/body/geom/site ID는 이름으로 조회한다. 붙이기/weld/물체 강제 이동을 성공 수단으로 쓰지 않았다.
5. 선택적 Ch12.8 정책 입력은 48D, 다리 출력은 12D로 격리했다. 기본 설치에 torch는 필요하지 않으며 실제 모델 ZIP이 없어서 정책 엔진 smoke는 미검증이다.
6. 실패 원시 결과, RED/GREEN 로그, 실제 엔진 결과, 프레임, build/test 로그를 보존하고 새 실행만 집계하는 검증기를 만들었다.

## 실제 발견한 결함과 수정 근거

- 초기 MuJoCo 파지 FAIL: 허벅지–몸통 약 7mm 초기 관통, 발/fixture 침투가 초기 충격과 약 10cm 이동을 만들었다. 침투 회귀 테스트를 먼저 실패시킨 뒤 초기 base z=.468m 및 구조적 몸통–허벅지 4쌍 제외로 수정했다. 팔/물체 충돌을 전역 제거하지 않았다. attempt1과 attempt2를 모두 보존했다.
- Ch11의 joint origin 1.2/-2.4 회전은 명시적 `[0,-.5,1]` nominal과 중복 적용될 수 있어 제거했다. 치수·축·한계는 유지하되 원본 정책의 물리 동등성을 주장하지 않는다.
- 설치된 Jazzy 콜백 metadata에는 publisher_gid가 없다. 실제 관측 후 sole graph endpoint로 소유자를 검사하도록 변경했다. 여러 endpoint면 fail closed한다. TF는 child-parent 유일성과 허용 그래프 발행자 경계를 확인하지만 패킷별 GID 식별은 미검증이다.
- Gazebo 초기 probe는 yaw를 전도 tilt로 오인했다. 별도 yaw/roll 회귀 테스트 후 roll/pitch tilt로 수정했다. XY 미끄러짐은 별개이며 위치 유지 성능은 검증하지 않았다.
- MuJoCo odometry에 실제 몸체 선속도·각속도를 넣고 IMU orientation/angular velocity를 발행한다. 측정하지 않은 가속도는 covariance=-1로 표시한다.
- colcon test가 직접 pytest와 달리 0개 테스트를 실행하며 exit 5를 반환했다. tests_require 및 testpaths를 등록한 뒤 실제 ROS 테스트 13개가 실행되고 0 failures/0 skipped임을 확인했다. 최초 실패 로그도 보존했다.
- 비편집 wheel을 별도 경로에 설치해 Ch13 소스가 아닌 설치본에서 계약 20개와 실제 mj_step을 확인했다. 배포 리소스 누락이 없었다. source hash 수집은 가상환경·build/install/log·evidence를 순회하지 않도록 제한했다.

## 실행 증거와 판정

정확한 최신 테스트 수·코드 SHA·시각·명령·소스 해시는 evidence/verification_summary.json을 기준으로 한다. 구현 중 전체 테스트 54개가 통과했으며 최종 리뷰 후 재실행 수가 바뀔 수 있다. Ch13 ROS 2개 패키지는 앞 장 overlay 없이 빌드했다.

| 검증 | 실제 실행 결과·경계 |
|---|---|
| Xacro/check_urdf/MJCF | 20개 가동 관절, 단일 루트, 양의 관성, 축·한계·mount parity 통과 |
| MuJoCo 물리 | 3.3.7 mj_step 실제 실행, 양 손가락 접촉·약 8.1cm 상승·약 5.12s 유지 통과 |
| MuJoCo ROS | complete states/clock/단일 발행자/기립 높이·tilt/정상 종료 통과 |
| Gazebo Harmonic | 실제 서버·spawn·20관절·TF·단일 ROS 및 네이티브 관절 명령 발행자·팔 반응·server_control 응답·정상 종료 통과 |
| Gazebo 물리 파지 | FAIL. 물체 약 4.8mm 상승에 그침, 양 손가락 접촉 관측 없음. MuJoCo 성공으로 대체하지 않음 |
| 선택적 PPO | manifest만 있음, weights ZIP 없음. 계약 회귀 테스트만 실행, 실제 추론·보행 미검증 |
| GUI/실제 로봇 | 미검증. Gazebo headless와 MuJoCo EGL 프레임만 실행 |

## 남은 한계

Gazebo의 fixture 정렬·미끄러짐·접촉 관측을 보정하고 실제 양측 접촉–들기–유지를 재검증해야 파지 완료로 주장할 수 있다. 두 엔진의 contact solver/PID 응답은 다르며 기구 계약 일치가 동역학 결과 일치를 뜻하지 않는다. MuJoCo에서도 하나의 고정 fixture 성공이며 임의 물체 집기나 로봇 이동 운반이 아니다.

MoveIt2, 하나의 ros2_control SystemInterface, lifecycle 시동 보장, realtime priority, whole-body control, YOLO/SLAM, 일반 IK, collision-aware planning, 안정 PPO와 실제 로봇 적용은 구현 완료 범위가 아니다. 기본 enabled=false도 Torque Off가 아닌 nominal 위치 hold다. KDL 루트 관성 경고와 Ch08/Ch11 라이선스 TODO는 남아 있다.

## 최종 리뷰 및 커밋·push

최종 fresh-context 리뷰의 지적과 수정은 별도 REVIEW_FINAL_KO.md에 기록한다. 검증기는 검증한 코드 commit과 당시 dirty paths를 기록한다. evidence 파일 자신의 최종 commit SHA를 자기 내용에 넣는 순환 참조를 피하기 위해 최종 원격 SHA 일치는 인계 응답에서 별도로 확인한다. push는 13.1 브랜치에만 하며 force push나 main merge를 하지 않는다.
