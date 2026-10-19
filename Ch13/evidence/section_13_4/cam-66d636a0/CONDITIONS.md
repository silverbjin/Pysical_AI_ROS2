# 중복 자동 렌더 차단 후 실제 엔진 인수

실행 묶음 UUID: 66d636a0-ef69-466b-b16f-7b95ca1bd6ac.
2026-10-19, 전원 강제 종료 후 저장된 체크포인트와 일반 사용자 WSL을 확인하고 재개했다.
이 묶음은 `cam-edfdbd00`의 수정 전 시험과 별개다. 이전 원본은 보존한다.

snapshot + vision=true만 `auto_register_cameras=false`를 전달한다. 기존 upstream 및
vision=false 경로는 true 기본을 유지한다. 단일 소유권 검사에는 기존 네 센서 토픽뿐 아니라
자동 생성되는 overview/eye_in_hand의 color/depth/camera_info 여섯 토픽의 발행자 부재도 포함한다.
원인 증거: 이전 md/system.log의 원본 CameraPlugin 자동 등록·두 카메라 5Hz 렌더.

설치: `Ch13/ros2_ws/install13_4_snapshot_full_35954ef5`. 실제 소스 SHA, 설치 감사와
각 시험의 실행 UUID/실제 로드 라이브러리는 생성되는 JSON에 기록한다.
RGB-D320×240, 목표15Hz, 추론10Hz/명시적15Hz, 촬영/수신300ms, TF100ms,
팔5Hz·각도.04rad·속도.1rad/s를 유지한다. LP_NUM_THREADS/OMP_NUM_THREADS/
OPENBLAS_NUM_THREADS, 드라이버·해상도·안전 기한 변경 없음. 실제 렌더러는 로그로 확인한다.

성능 시험과 빌드/대량 시험은 병행하지 않는다. 매 시험은 독립 엔진과 새 output을 사용한다.
자체 소유 종료 기록·잔여 PID 확인 후에만 다음 시험으로 진행하며 정지한 trial은 재활성화하지 않는다.
관리자/ptrace 정책 변경과 외부 소스 수정은 하지 않는다. GUI/실로봇/PPO/MoveIt/물리 파지는
이번 카메라 소유권 인수 범위 밖이며 미검증이다. 전체13.4가 미달이면13.5는 보류한다.
