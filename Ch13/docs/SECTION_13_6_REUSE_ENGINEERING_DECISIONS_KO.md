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

## 접촉 힘·시각 보정과 센서 가림 조사

20g 대상과 원본 position PD의 분리된 손가락 시험은 lift를 만들지 못했다. 동일 형상·질량·마찰·0.5N cap에서 양 finger normal force를 확인한 뒤 네이티브 PD의 내부 reference로 제한된 닫기 힘을 유지하는 profile을 추가했다. nominal close 목표와 내부 reference를 별도로 기록한다. force hold는 접촉을 얻기 전 활성화하지 않으며, 취소/fault로 이미 잡은 물체를 임의 개방하지 않는다. explicit open만 해제한다. 독립 손가락 rig의 81.6mm 상승은 Go2 전체 pick 성공 증거가 아니다. condim4 후보는 더 나빠 채택하지 않았고, 최종 대상은 원래 condim3·20g·마찰0.8을 유지한다.

기본 lift는 TCP 10cm 직선이다. 이후 새 RGB-D 관측으로 물체 상승 부족을 확인하면 최대 한 번, 3cm 이내의 추가 직선 보정만 허용한다. 보정은 실제 freejoint 정답을 입력으로 사용하지 않는다. 최종 판정은 사전 정의한 실제 물체 상승9cm·유지2sim초·상대 미끄러짐2cm·양 finger 접촉 비율을 그대로 사용한다.

원래 카메라와 15cm 측면 후보에서는 실제 팔이 원통 상단을 가렸다. 저장 RGB-D와 56개 자세의 오프라인 광선 가림 조사를 근거로 가상 카메라를 base 기준 [0.4,0.25,0.25]m, 안쪽 yaw -20도로 배치했다. 교육용 opt-in 센서 배치이며 실물 카메라 설치 검증이 아니다. 기존13.5 배치는 유지한다. 붉은 로봇 조각과 대상의 전역 mask 병합을 피하려고 연결 성분을 각각 원통으로 검증한다. 가까운 두 조각의 병합에도 동일 반경·잔차·75% 높이 조건을 적용하고 서로 다른 유효 물체는 거절한다.

## 최신 프레임 경로와 시각 판정 경쟁 조건

13.6의 renderer 결과·RGB-D subscription·채널별 native relay는 latest-only로 전달한다. 원본 capture/최초 receipt/GID는 바꾸지 않는다. 혼합 큐의 낡은 상태가 다른 채널의 최신 관측을 가리지 않도록 다섯 lease 채널과 비전용 clock/TF를 분리했다. 기존13.5 기본 큐 경로는 유지한다.

MuJoCo3.13.0의 동일 실제 렌더 버퍼에서 RGB와 depth를 한 번에 읽는 opt-in 경로를 추가했다. 공식 renderer와 같은 reverse-Z 변환을 사용한다. skybox를 끄지 않은 초기 비교는 far-depth 불일치로 기각했다. 최종 profile은 skybox를 끄고 두 실제 정적 장면에서 전체 depth 오차0·동일 RGB를 확인했다. 중앙 렌더 시간은 약9.7~9.9ms에서6.0~6.2ms로 줄었다. 이 두 장면의 일치는 모든 장면·버전의 동등성을 보증하지 않으며, 정확한3.13.0과 skybox 조건을 검사한다. 13.5 기본 두 번 렌더는 유지한다.

`675587d6`은 PRE_GRASP에서 LIVE_SUPPORT_OR_NAVIGATION_LOST로 실패했다. shared lock 획득 전에 판정 시각을 읽으면 대기 중 수신한 정상 navigation receipt가 미래로 보일 수 있음을 회귀 시험으로 재현했다. 판정 시각을 lock 안에서 읽도록 수정했다. 수명/지지 한계는 완화하지 않았다. 모든 실패 실행과 정상 회수 기록은 보존한다.

## 실제 들기 이후의 판정 보완

`39d706b8`은 실제 파지·직선 들기·시각 보정·2.2sim초 유지·12개 자식 정상 회수까지 완료했지만 유지 최소 상승88.304mm로90mm 기준에 실패했다. 양 finger 접촉100%, 상대 미끄러짐27μm로 물체 이탈은 관찰되지 않았다. 첫 lift 촬영의 비전 중심z와 같은 시각 실제z 차이는0.373mm였다. 기존 보정은 팔 끝의 목표 추종 지연을 반영하지 않아 작은 보정 목표에도 실제 endpoint가 뒤처졌다.

계약v6은 동일 한 번·3cm 상한 내에서 관측 부족량+3mm와 실측 robot TCP의 양의 목표 지연을 합해 보정한다. 큰 관측 부족(27mm 초과)은 거절하고, 합산 보정은3cm로 제한한다. HOLD 시작은 새 관측 상승95mm와 실제 팔 최대속도0.003rad/s·기존 base 정착의0.5sim초 연속 확인을 요구한다. 실제 물체 정답은 여전히 제어 입력이 아니며 독립90mm/2sim초 판정은 변경하지 않았다. action의 넓은 관절 tolerance 통과를 정밀 작업의 최종 정착과 구분한다.

파지한 상태의 취소는 별도 안전 시나리오로 분리한다. 직선 lift 중 실제 CANCELED terminal 뒤2sim초 유지·5mm 이내 낙하·양 finger 접촉·상대 이탈을 검사한다. 이 시나리오는9cm lift 성공으로 세지 않는다.

MoveIt 끝점이 2ms보다 가까운 TOTG 구간도 실제 입력에서 확인됐다(`4732687c`:0.532510ms). 최대3배 시간 배율만으로는 이를 실행할 수 없었다. 원본 경로점을 삭제하지 않고 전체 경로의 초기 배율을 `max(1,2.000002ms/최소구간)`로 정한 뒤 기존 속도·가속도·C2·120sim초 한계를 다시 검증한다. 이 수정의 실제 원본 궤적을 회귀 fixture로 보존한다. 기존 동결v1은 실패 기록으로 유지하고 변경 소스는 별도v2 동결을 사용한다.
