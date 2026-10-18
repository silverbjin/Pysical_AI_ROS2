# 13.3 설계 및 구현 계획

기반: 13.2 `8d7d7e0b6003845ad7e6ef77420cf35e16758202`.
브랜치: `feat/ch13-section-13-3` (13.2 위에 쌓는 절별 브랜치).

## 목표와 설계

`integrated_robot_interfaces`는 PickObject 액션과 SetMode 서비스를 생성한다.
`integrated_robot_runtime`은 별도 프로세스의 locomotion_node, manipulation_node,
vision_processor, state_manager, mission_commander를 설치한다.
기존 13.2 엔진 및 controller_manager가 관절을 소유하고 런타임은 해당 컨트롤러의
공개 명령 API만 사용한다. 다리 50Hz는 정지 자세 기준 생성이며 PPO 보행은 후속 과제다.

팔 lifecycle activate 후 state_manager가 stow 서비스를 호출한다. 팔 궤적 성공과
최신 JointState의 안전 자세를 확인한 경우에만 다리 lifecycle activate한다.
기동 중 실패하면 활성화를 중단하고 다리·팔을 deactivate한다.
Inactive는 소프트웨어 명령 차단을 뜻하며 하드웨어 Torque Off를 보장하지 않는다.

PickObject는 PoseStamped로 프레임과 촬영 시각을 보존한다. MoveIt·물리 파지가
없는 현재 단계에서는 dry_run=true만 받아 피드백·취소·단일 목표 잠금·시간 제한을
실습한다. 완료 결과도 success=false/NOT_IMPLEMENTED로 반환해 파지를 주장하지 않는다.
mission_commander는 이 결과를 정상 과제 성공으로 승격하지 않는다.

인지 노드는 Image/Odometry를 50ms 이내로 묶고 300ms 초과 데이터, 미래 시각,
프레임 누락을 거부한다. 유한 크기의 최신 1쌍 버퍼와 작업자 스레드로 느린 처리를
격리한다. 변환·보간·YOLO가 없는 이 단계의 출력은 동기화 진단 정보다.

## 구현 순서

1. 실패 테스트: 목표 검증, 시각 경계, 안전 자세 gate, 관절 입력 검증.
2. 인터페이스 및 순수 정책 모듈 구현. RED→GREEN 검증.
3. 실제 lifecycle 노드, 팔 궤적 서비스/액션, 기동 관리자, 임무 클라이언트 구현.
4. message_filters 동기화와 bounded worker, 런타임 launch 및 설치 구성.
5. 실제 ROS 실행 검증: 기동 순서, 50Hz 지연 분포, 동기화 허용/거부,
   목표 거부/피드백/취소/중복 거부, 비활성 출력 차단.
6. Gazebo·MuJoCo 실제 연동, 한국어 가이드·리뷰·evidence, 커밋과 push/SHA 대조.

## 검증의 경계

일반 Python/WSL 환경에서 hard realtime과 50Hz deadline 보장은 하지 않는다.
측정한 주기 분포와 최대 간격을 기록한다. 팔 기본 안전 자세는 13.2의 직립 영점
자세이며 접힌 운반 자세가 아니다. MoveIt, PPO, SLAM, YOLO, 물리적 grasp는
미구현이며, 실패/취소 시험은 실제 ROS API를 통해 수행한다.
