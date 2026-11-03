# 13.6 구현 중 확인한 설계 변경

이 문서는 최초 승인 설계와 실제 구현의 차이를 기록한다. 검증되지 않은 단계의 성공을 선언하지 않는다. 기존 13.5 자료와 외부 원본은 보존한다.

## 실행 인터페이스

설치된 MoveIt 2.12.4의 Python 인터페이스에 원고의 `arm.compute_cartesian_path()`와 `plan().execute()`가 그대로 존재한다고 가정하지 않는다. 원고가 허용한 Python 래퍼로 단일 계획 장면의 GetMotionPlan/GetCartesianPath/ApplyPlanningScene를 사용한다. OMPL RRTConnect와 TRAC-IK는 설치된 플러그인이다. MoveItPy의 NumPy2/Eigen 배열 setter는 이 환경에서 segfault가 발생했으므로 모델 검증은 joint_positions 사전과 get_pose를 사용했다.

실행은 MoveIt가 만든 궤적을 검증·시간 조정한 뒤 기존 엔진의 FollowJointTrajectory action으로 보낸다. ExecuteTrajectory와 병렬 실행하지 않는다. 설치 버전의 ExecuteTrajectory는 상호 배타 callback에서 실행 완료를 기다려 취소 응답이 막혔다. 대기 시간을 늘린 재시험에서도 실제 사용자 취소가 전달되지 않았고, 종료 때 TEM이 보낸 취소와 구분했다. [공식 2.12.4 구현](https://github.com/moveit/moveit2/blob/2.12.4/moveit_ros/move_group/src/default_capabilities/execute_trajectory_action_capability.cpp)의 executePathCallback/MutuallyExclusive 구조도 확인했다. 해당 capability는 최종 호스트에서 제외했다. 래퍼는 TEM 대신 시작 상태·장면 hash·원본 관측 수명·궤적 속도/가속도·실측 terminal을 검사한다.

## 제어 profile v2

원본 PD만 사용한 작은 팔 시험에서 joint2/3은 목표 0.02rad에 대해 실제 변화가 0.00011rad 미만이었다. action tolerance만 통과한 결과는 실제 6축 성공으로 인정하지 않았다. 중력 bias 약 2.94/-6.27Nm를 확인한 뒤, 계획 목표와 내부 servo reference를 분리하고 `qfrc_bias/Kp`를 0.5sim초에 걸쳐 적용하는 명시적 시뮬레이터 모델 보상 profile을 추가했다. Kp50/Kd4·원본 32/8Nm cap·보행 정책은 유지한다. 실기에서 같은 정확도가 보장되거나 원본 제어 법칙이 그대로라고 표현하지 않는다.

## 수명과 계산 시간

기본 move_group는 엔진 시계가 살아 있어도 SIGINT 종료가 완료되지 않았다. 작은 C++ 호스트가 공식 계획 capability를 실행하고 명시적 종료 서비스로 TEM·monitor·executor를 ROS shutdown 전에 회수한다. 초기 호스트의 destructor segfault는 GDB에서 TEM→Node→CallbackGroup 경로로 확인했다. controller 라이브러리 코드가 객체보다 먼저 해제되지 않도록 RTLD_NODELETE로 process 수명 동안 유지했을 때 정상 종료 시험이 통과했다. 이는 검증된 완화책이며 모든 upstream 원인의 확정을 뜻하지 않는다. 시스템 라이브러리나 전역 설정은 수정하지 않았다.

210점 궤적의 동기 검증과 반복 다항식 계산은 관측 만료를 유발했다. admission 계산은 시간 제한 있는 별도 worker에서 수행하고 엔진 잠금을 잡지 않는다. quintic 계수를 해석식으로 만들고 Horner 평가·Bernstein 경계 증명(필요시 정확한 근 계산)을 사용한다. 대표 실패 궤적의 시간 조정 39ms·검증 26ms를 확인했다. BLAS thread는 실행 프로세스에서만 1로 제한한다. 300ms 관측 수명과 100ms 과거 TF 조건은 변경하지 않았다. 별도로 접근 중 발생한 기존 VISION_EXPIRED 실패는 보존하며 완전 해결로 표현하지 않는다.

## 물리 파지 profile

13.5 gateway에는 실제 팔 각도가 ±0.1rad 이내여야 한다는 hold 전용 검사가 있었다. 13.6 opt-in 모드에서는 실제 통합 모델 한계와 물리 tolerance(팔 20mrad·finger 2mm)를 검사하며 기본 13.5 검사는 유지한다. gateway의 native receipt/GID가 있는 상태를 엔진 lease까지 전달해 fault·만료·비ARMED를 조작 fault로 연결한다. 후속 mission과 독립 verifier도 최종 gateway fault를 검사한다. 이 검사가 없던 `660ec362`의 summary PASS는 정상 전체 인수로 인정하지 않는다.

원본 정적 붉은 상자 대신 opt-in 장면에 반경 2cm·높이 8cm·질량 20g·마찰 0.8 원통 free body를 추가한다. 로봇 mass/inertia/equality/cap은 원본과 대조한다. 엔진 목표 freejoint는 평가 파일에만 기록하고 TF/비전 입력으로 발행하지 않는다. 알려진 upright 치수와 실제 RGB-D 표면으로 중심을 추정하며 일반 6D 인식·yaw 관측이 아니다.

손가락과 대상 접촉만 지정 단계에 허용한다. 기계적 blockage는 gripper stall이며 파지 성공이 아니다. 양 finger 실제 접촉 이후의 planning-scene attach는 충돌 계획 표현일 뿐 물리 weld가 아니다. 실제 대상 상승·접촉·상대 미끄러짐·유지 시간은 실행 종료 후 별도 평가한다. 팔 이동·base 지지·작업 후 정착을 구분하며 다리는 계속 정책으로 지지한다.
