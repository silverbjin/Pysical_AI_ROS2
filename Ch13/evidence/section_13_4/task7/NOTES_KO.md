# 13.4 실제 엔진 시험 기록

이 디렉터리의 RED 로그는 결함을 먼저 재현한 결과이며 삭제하거나 성공 로그로 덮어쓰지 않았다. `*-green.txt`도 해당 범위의 테스트만 증명한다. 전체 절 성공을 뜻하지 않는다.

## 결과를 읽는 방법

- 실행마다 새 UUID로 RUNNING을 먼저 기록한다. 필수 검사 누락·예외·기한 초과·부족한 표본·강제 종료는 FAIL이다.
- `geometry` 수치는 bbox 중앙 광선과 선언된 물체 전면 x=.98m의 교차점에 대한 RMS이다. 물체 중심 x=1m와 비교하지 않는다. 같은 촬영 시각 카메라 TF를 사용하는 물리 깊이 일관성 시험이며 모든 TF 자유도의 독립 위치 측정은 아니다. URDF/native 카메라 일치는 별도 단위 시험이다.
- fixture 인식은 명시적인 `color_fixture` 모드다. YOLO 성공으로 바꾸어 쓰지 않는다. YOLO의 실제 추론 시도와 신선한 결과 발행, 의미적 인식, 유효한 3D 목표는 서로 다른 단계다.
- 150ms는 추가 처리 지연이다. 총 지연을 뜻하지 않는다. 300ms 신선도 제한을 늘려 통과시키지 않는다.
- `clean_shutdown`은 런처 반환값뿐 아니라 자식 사망·내부 종료 승격·잔존 PID까지 검사한다. Gazebo stop ACK만으로 종료 성공을 선언하지 않는다.

## 초기 실행과 재현

| 실행 경로 (section_13_4 아래) | 관측 | 판정 |
|---|---|---|
| mujoco/static | 빈 `weights_path:=` 실행 인자 | FAIL, 인자 생략 회귀 추가 |
| mujoco/static-replay | Jazzy 메타데이터를 객체로 가정 | FAIL, 초기화 중 종료 승격 포함 |
| mujoco/static-jazzy-replay | 실제 Jazzy dict에 GID가 없음 | FAIL, 실제 메타데이터 확인 뒤 소유권 방법 명시 |
| mujoco/static-graph-contract | 30표본, RMS .003023941614m | PASS |
| mujoco/delay | 60초 안에 3표본뿐, EXPIRED_BEFORE_INFERENCE 216회 | FAIL, 이후 관절 상태 신선도 상실로 모션 중단 |
| gazebo/geometry/static | 30표본, RMS .002293021612m | PASS |
| gazebo/geometry/delay | 30표본, RMS .001842347533m; q1 범위 .0500971rad | 측정 통과, 종료 SIGTERM으로 전체 FAIL |
| gazebo/delay-native-stop-replay | native PID 식별이 Ruby setproctitle을 놓침 | FAIL |
| gazebo/delay-title-replay | 정확한 native/wrapper PID 대기 뒤에도 종료 승격 | FAIL, 외부 엔진 소스 미수정 |
| mujoco/tracking-five-second | 실제 목표 1회 뒤 invalid/lost target로 OFF | 5초 성능 FAIL; 종료는 정상 |
| mujoco/yolo-native | 실제 추론 7회가 모두 만료, 유효 결과 발행 0 | FAIL; 원본 스냅샷 미저장도 드러나 수집기 회귀 추가 |

최초 `static-replay`의 clean_shutdown=true는 잘못된 하위 라벨이었다. 전체 판정은 원래 FAIL이며 원본은 보존했다. 이후 판정기는 내부 SIGKILL도 거부한다.

## 소유권과 중단 시험 범위

Jazzy 설치본은 수신 메타데이터에 publisher GID를 제공하지 않았다. 동적 `/tf`의 정확한 두 발행자(native_pose_adapter, robot_state_publisher), 정적 TF의 한 발행자, 전체 URDF child→parent 계약 및 실제 관측 간선을 비교한다. 이는 그래프·모델·코드에 근거한 소유권 추론이며 패킷별 발행자 인증이 아니다. 알려진 발행자가 다른 발행자의 동일 간선을 악의적으로 송신하는 경우까지 구분하지 못한다.

입력 상실은 각 시험마다 새 엔진과 실제 팔 목표를 사용한다. `images`는 탐지 노드의 소비 입력 차단 서비스이며 카메라 전원을 끄지 않는다. `tf`는 해당 런처 그룹의 유일한 robot_state_publisher만 종료한다. `joints`는 joint_state_broadcaster만 비활성화하며 관절 TF도 함께 오래되어 간다. 어느 것도 가짜 센서/목표/이동 TF를 발행하지 않는다. 실패나 거부는 재시도·자동 재활성화하지 않는다.

현재 실행 결과의 최종 권위는 각 새 실행의 `result.json`, `observations.json`, `system.log` 및 소스 해시 파일이다. 이 문서의 초기 실행 표가 이후 재현의 결과를 대체하지 않는다. 5초 추적 성능과 입력 상실 중단은 독립 검사 집합이므로 안전 중단만으로 추적 성능 성공을 주장할 수 없다.

## 실행 환경과 남은 경계

ROS 2 Jazzy / Ubuntu 24.04 / MuJoCo 3.3.7 / Gazebo Harmonic, 전용 venv의 NumPy 1.26.4, PyTorch 2.5.1+cpu, Ultralytics 8.3.221, OpenCV 4.10.0.84를 사용했다. `build-fresh.txt`는 이전 Ch13 overlay 없이 네 패키지를 새 경로에 빌드한 결과다. 이후 launch 사전 검사 수정은 `build-preflight-update.txt`에 별도로 기록했다.

라이브 입력 중 SIGINT 및 생성자에서 작업 스레드 시작 직후 SIGINT를 실제 하위 프로세스로 시험했다. worker를 join한 뒤 ROS context를 닫는다. 팔은 취소 응답이 아니라 terminal action result까지 단일 소유권을 유지한다. 취소 확인 불가 시 fault를 유지하며 토크 해제나 물리적 정지가 입증됐다고 표현하지 않는다.

Nav2, PPO 적재 보행, 일반 비주얼 서보잉/충돌 회피, MoveIt, 물리 파지, 실로봇, GUI 영상 품질은 이 시험으로 검증하지 않았다. 고정 스탠스에서의 소각도 두 관절 제어이며 hard realtime을 보장하지 않는다.
