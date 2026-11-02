# 13.5 공개 통합 플랫폼 설계

13.1~13.4의 로봇과 증거는 보존한다. 13.5부터 IIT-DLSLab의 Go2+Piper 공개 통합 플랫폼으로 전환한다. 학습 목표는 보행기 개발이 아니라 공개 이동 정책과 ROS2/Nav2를 연결해 작업 위치에 접근하고 실제로 정지시키는 것이다. 기존 자체 crawl Task8의 실패는 이 실습의 성공으로 변경하지 않는다.

## 채택 조합

고정 커밋은 `d010212c3f5c9e6e5542ada61cfdacc19b00f775`, 정책은 `tested_policies/arm_moving_clock/exported/policy.onnx`다. 94개 외부 파일의 경로·크기·SHA256은 [lock](../dependencies/section_13_5_reuse.lock.json)에 있다. MuJoCo3.13.0, Python3.12.3, ROS2 Jazzy, Nav2 1.3.13, CPU 추론을 사용한다. 정책은 300차원 관측으로 12개 다리 action을 출력하며, 팔 6축은 별도 원본 PD가 소유한다. 재학습·새 gait·새 WBC를 포함하지 않는다.

원본 재현에서 확인한 팔 목표 복사, native 팔 PD와 implicitfast, 이동 중 일관된 다리 gain의 세 보완은 [정착 조사](SECTION_13_5_REUSE_SETTLING_REVIEW_KO.md)에 근거한다. 원본 checkout을 고치지 않고 설치된 correction helper를 적용하며 hash를 검사한다. 추가 실행 보완은 프로세스 내부의 단조시계 pacing, ORT 단일 스레드·순차·busy-spin 해제와 Torch 단일 스레드다. 배우는 정책·2ms 물리 간격·50Hz 정책 주기·모터 cap을 바꾸지 않는다. 원본/제한 CPU 세션의 실제 actor 출력 일치 시험을 둔다.

## 소유권과 관측

속도 흐름은 `Nav2 controller → velocity smoother → navigation_boundary → command_gateway → platform_adapter → upstream policy`다. 전 구간 TwistStamped를 명시한다. ACTIVE 출력 시각은 controller와 smoother 원본 시각 중 오래된 값이며 반복 수신으로 최초 receipt를 갱신하지 않는다. IDLE의 생성 zero는 관측이나 명령의 원본 시각으로 위장하지 않는다. 단일 명령자와 실제 DDS GID를 C++ ingress에서 확인한다. 출발 준비 중에는 boundary가 controller 원본 stamp의 zero를 유지한다. 실제 controller/smoother가 신선해진 뒤 gateway 재무장→명시적 release 순서로 움직임을 허용한다. 도달 불가 terminal이 준비 중 발생하면 움직임을 해제하지 않는다.

engine의 실제 qpos/qvel에서 상태를 발행한다. `map→odom`은 알려진 장면의 ground-truth 교육 profile이다. `odom→nav_base`는 측정 xy/yaw, `nav_base→base`는 나머지 z/roll/pitch를 보존한다. 팔·카메라까지 이어진 TF는 같은 실제 상태에서 계산한다. edge마다 소유자 하나를 요구한다. odometry에 목표를 넣거나 root를 teleport하지 않는다. AMCL/SLAM 실증으로 표현하지 않는다.

지도는 장면을 알고 만든 5cm 격자 prior다. scan은 몸체 부착 위치에서 실제 `mj_ray`로 환경 group5에 쏜 결과다. 자기 몸체·바닥 필터를 명시하며, 지도는 장애물을 보수적으로 투영한다. scan 높이가 등반 능력을 증명하지 않는다. footprint는 기존 실제 자세 70개에서 collision AABB를 heading 평면에 투영하고 4cm 여유를 더했다. Spin/BackUp·역주행·측방 이동은 기본 시나리오에 넣지 않는다.

## 비전과 팔 작업영역

카메라는 실제 qpos의 불변 복사본에서 MuJoCo Renderer로 RGB와 축방향 depth를 만든다. 320×240, capture 상한15wallHz, 관측 처리 상한10wallHz(15 선택)를 구분해 기록한다. 별도 renderer 프로세스의 최신 단일 요청 슬롯·유계 결과 큐을 사용하고 촬영·TF의 원본 sim 시각과 capture wall을 보존한다. 장식용 고해상도 robot mesh(group2)는 제외하고 원본 collision 형상(group3), 바닥과 실제 환경(group5)을 촬영하는 **충돌 형상 기반 교육용 화면**이다. 로봇 가림은 이 근사 형상에 따른다. 물리·충돌 모델은 바뀌지 않는다. Mesa 렌더링 스레드 제한은 해당 프로세스 환경에만 적용한다. 촬영 프로세스 exit0와 수신 thread join을 별도로 검사한다.

붉은 작업물의 색 영역과 실제 depth를 기존13.4 `integrated_robot_vision` geometry/contracts로 역투영한다. YOLO·일반 물체 인식·물체 중심 정답 입력을 주장하지 않는다. 관측점은 보이는 표면이다. 큰 영상은 원본 native ROS 메시지로 직접 수신한다. C++는 실제 GID·최초 receipt·source timestamp와 전체 메시지 필드의 canonical SHA256만 보내고, Python이 같은 native 샘플과 정확히 결합한다. CDR의 미정 padding을 hash하지 않고 모든 camera header/pixel/encoding/calibration/ROI 필드를 명시한 little-endian canonical1 규약을 쓴다. 기존 속도·상태·Nav2 경로는 원본 CDR 전달을 유지한다. 기존 OpenSSL3.0.13을 사용하며 새 시스템 설치는 하지 않았다. RGB 원본 hash, calibration, 과거 TF 행렬, capture/최초 receipt를 증거에 남기며 저장 RGB/NPY에서 점을 독립 재계산한다. 기본 age는300ms, 과거TF는100ms다. 완전한 RGB-D·hash·calibration·과거TF의 카메라 생존 확인은 인식 cap과 분리한다. 물체 점의 승인·최종 READY에는 별도 신선한 검출이 필수다. 검출에서 물체를 잃으면 고장을 latch하고 카메라 health 갱신을 멈춘다. 고정 작업물 접근이며 동적 물체 추적을 주장하지 않는다.

팔 mount와 고정 관절 규약을 읽어 position-only IK, joint limit, 충돌, footprint와 실제 Nav2 ComputePathToPose 비용으로 후보를 평가한다. 체인 길이 약0.885m에서 여유를 뺀 거리와 방향 후보를 사용하며 보편적인0.4m를 복사하지 않는다. IK는 별도 scratch data에서만 계산한다. 최종 실제 root와 관절에서도 다시 확인한다. 팔 실행·파지·MoveIt·전신 동시 최적화는13.6 후속 범위다.

## 정지·고장·수명

NavigateToPose terminal 성공, 실제 root 오차0.10m/0.10rad 이내, [edu_stop_v2](../dependencies/section_13_5_edu_stop_v2.json) 정착, 신선한 실제 관측과 작업영역을 모두 확인한 뒤 READY_FOR_MANIPULATION을 발행한다. cancel ACK는 terminal CANCELED와 별도로 기록한다. 정상 종료 전에 READY를 회수한다.

만료·비유한 값·지원하지 않는 축·명령/TF 소유자 교체·시계 역행/정지는 fault latch로 zero를 지시한다. 살아 있는 이동 정책으로 실제 정착을 확인하며 torque0나 프로세스 소멸을 정지로 세지 않는다. 입력 복귀만으로 자동 재개하지 않는다. 리셋·새 zero·명시적 재무장이 필요하다. 엔진은 배타 lock으로 순차 실행하고 RX, renderer, 원본 thread, 자식과 부모를 정상 회수한 뒤 잔여 PID와 lock을 검사한다.

## 인수 해석

교육용 단일 실행 기준과3회 반복 강건성 확장은 분리한다. 원본 정착이 완전 정적 STAND라고 주장하지 않으며 실측 속도·변위·팔 안정성 창으로 판단한다. 본문 필수 엔진은 MuJoCo다. Gazebo 동등성, 실기 로봇 안전 인증, 동적 물체 추적, 일반 환경의 견고성은 이 결과로 입증하지 않는다. 최종 숫자와 시나리오는 실행 전에 고정하고 실패 evidence를 보존한다.
