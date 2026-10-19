# 13.4 EGL 전용 카메라·종단 지연 계측 설계

2026-10-20(Asia/Seoul). 기준 HEAD e580702391c959f1e3debb7bdff4caa4238c9389.
상태: **사용자 방향 확정 / 서면 설계 검토 대기 / 새 구현 미착수**.
사용자는 EGL 전용 카메라와 종단 계측을 첫 수정 단위로 확정했다.
이 설계서 검토 후 구현 계획을 작성하며 실행 방식은 기존 네이티브 단일 작업자를 유지한다.
기존 실험 브랜치·원본 실패 증거는 보존한다. 과거의 보존 전용 판정은 역사적 상태다.

## 1. 의도와 완료의 의미

첫 목표는 Ch13 snapshot 카메라의 명백한 GLFW 스레드 계약 위반을 제거하는 것이다.
두 번째는300ms 예산을 어느 경계가 소비하는지 실제 촬영 단위로 설명할 수 있게 하는 것이다.
EGL 전환 자체가 추적 성공·GPU 가속·hard realtime을 보장한다는 가정은 두지 않는다.

선행 분석: [실패 경과와 원인](../SECTION_13_4_ROOT_CAUSE_ANALYSIS_KO.md).
원래 snapshot의 두 버퍼·move-only lease·단일 producer/consumer 구조는 유지한다.
새 토픽은 진단용이며 모터 제어·목표 유효성 판단에 참여하지 않는다.

### 변하지 않는 계약

- Ch13만 수정한다. sources, Ch05~Ch12, 고정 외부 checkout/설치본을 변경하지 않는다.
- ROS2 Jazzy/MuJoCo3.3.7·고정 underlay/venv·320×240·카메라 목표15Hz를 유지한다.
- 추론 기본10Hz, 명시적 선택 최대15Hz. 촬영 ROS age·수신 후 wall age300ms,
  과거 TF timeout100ms, 팔 명령 최대5Hz와 기존 소각도/속도 제한을 유지한다.
- 촬영 header를 now로 바꾸거나 최신 TF로 대체하지 않는다. 자동 재시도/재활성화 금지.
- 관절·TF·액션의 단일 소유권과 terminal 결과 확인 규칙을 유지한다.
- 관리자 권한·ptrace/드라이버/해상도/렌더 스레드 환경 설정은 변경하지 않는다.
- snapshot 명시 선택과 upstream 기본값은 유지한다. 이번 범위에서 기본 승격하지 않는다.
- 실제 엔진은 순차 실행한다. 소유한 종료/잔여 검사 미확인 시 다음 엔진을 시작하지 않는다.

## 2. 선택한 접근과 대안

**선택: 기존 EGL 구현을 정리한 worker 전용 headless 카메라.**
현재 GLFW 우선 시도를 제거한다. EGL 준비가 실패하면 snapshot 초기화가 명시 실패한다.
GLFW, upstream 카메라, 가짜 영상으로 자동 대체하지 않는다.
다른 프로세스의 GUI나 외부 renderer 선택을 변경하지 않는다.

대안은 GLFW 창의 생성·파괴를 호스트 메인 스레드로 이동하고 context만 worker에
전달하는 것이다. 그러나 호스트의 메인 스레드·이벤트 처리·종료 인터페이스 변경과
외부 원본 수정 위험이 커 현재 범위에는 채택하지 않는다.

단순 MUJOCO_GL 환경변수 변경은 C++의 GLFW 우선 분기를 바꾸지 않으므로 해결책이 아니다.
렌더 thread 수·TTL 변경도 이번 API 결함의 해결책으로 사용하지 않는다.

## 3. EGL 수명과 스레드 소유권

Ch13 내부의 작은 EglRenderContext RAII 단위로 display 참조·context·surface 상태를 모은다.
테스트를 위한 공개 제품 제어 API나 임의 backend override는 추가하지 않는다.
실제 EGL API를 호출하며, 실패 경계는 시험 실행 파일의 심볼 interposition으로 검사한다.

1. 활성 카메라가 있을 때만 worker에서 surfaceless EGL display를 얻고 초기화한다.
2. OpenGL API를 bind하고 pbuffer-compatible config, private context와1×1 pbuffer를 만든다.
   실제320×240 출력은 기존 MuJoCo offscreen framebuffer에서 생성한다.
3. 같은 worker에서 make-current 성공 후 mjvScene/mjrContext를 만든다.
   renderer/vendor/version과 worker TID를 초기화 증거에 기록한다.
4. 같은 worker만 scene 갱신·render/readback·GL 정리를 수행한다.
5. 정상/부분 실패 모두 획득한 자원만 역순 정리한다. MuJoCo GL 자원을 current context에서
   해제한 뒤 unbind하고 소유 surface/context를 파괴하며 해당 worker의 EGL thread 자원을 정리한다.
6. stop→worker join을 완료한 뒤 node/camera buffer/model 참조를 해제한다.
   재초기화는 이전 worker 종료 후 시작하며 실패 후 cleanup 두 번도 안전해야 한다.
7. 전부 disabled면 EGL/context/렌더 worker를 생성하지 않는다. polled/streaming 정책은 그대로다.

### EGLDisplay는 per-camera 소유물로 간주하지 않는다

같은 native display를 요청하면 다른 사용자와 EGLDisplay를 공유할 수 있다.
따라서 카메라 cleanup이나 부분 실패에서 eglTerminate를 호출하지 않는다.
module 내부에서 고정 surfaceless display의 성공한 초기화를 직렬화·재사용하며,
최대 한 display 연결은 프로세스 수명으로 보존한다. 인스턴스별 context/surface는 모두 해제한다.
종료 시 전역 destructor가 다른 plugin의 display를 무효화하지 않도록 한다.
이 정책의 비용은 프로세스 종료 전까지 남는 한 display 연결이며 명시적으로 문서화한다.
외부 사용자가 display를 임의 종료하는 상황까지 안전하다고 보장하지 않는다.

성공한 초기화는 별도 context의 API binding을 바꾸지 않는다. 실패 후 같은 객체의 재시도는
명시적인 init 호출에서만 가능하며, 실행 중 자동 renderer 재시작은 하지 않는다.
드라이버 호출의 무한 정지를 스레드 detach/강제 자원 해제로 숨기지 않는다.
해당 native 시험이 정지하면 기존 소유 프로세스 정리 후 FAIL로 기록한다.

## 4. 계측 데이터 흐름과 시계 계약

계측은 선택 기능이다. launch/runner에 trace_enabled(default false)와 trace_run_id를
전달한다. enabled=true이면 유효한 실행 UUID가 필요하며, 시험 runner는 EvidenceRun의
UUID를 사용한다. 기존 토픽·이미지·Detection2DArray·TrackedTarget 정의는 변경하지 않는다.

공통 trace schema는 version1이며 다음 필드를 가진다.

| 필드 | 의미 |
|---|---|
| run_id, producer_id, pid, tid | 실행·노드 인스턴스와 발생 위치. 과거 PID로 신호를 보내지 않음 |
| clock_id, boot_id | linux CLOCK_MONOTONIC 및 동일 실행 호스트 식별 |
| stage, event_sequence | 발생 단계와 해당 producer의 단조 증가 사건 번호 |
| source_frame, capture_ns | 원래 이미지 frame과 촬영 ROS timestamp |
| local_epoch | 해당 producer의 reset 구간. 없는 단계는 null이며 다른 노드 epoch와 같다고 가정하지 않음 |
| native_sequence | 카메라 lease sequence. native 기록에만 직접 존재 |
| times_ns, outcome | 단계 발생 monotonic ns와 처리/폐기/실패 사유 |

C++은 CLOCK_MONOTONIC을 명시 사용한다. Python은 monotonic_ns의 clock 구현을
기록하고 같은 base임을 검증한다. 같은 boot/clock이 아니면 프로세스 간 차이를 계산하지 않는다.
ROS 시간과 steady 시간은 서로 빼지 않는다. ROS capture age는 각 단계의 당시 ROS now와
원 촬영 시각의 차이고, wall 구간은 monotonic끼리만 계산한다.

### 단계별 발생 시각

| 생산자 | 기록할 경계 |
|---|---|
| native camera | submit 시작/완료, lease 취득, scene/render 시작/완료, readback 완료, RGB/depth/Info publish 호출 구간 |
| detector | RGB callback 진입, slot 제출/worker 취득, 변환/추론 시작·완료, 탐지 publish 호출 구간 및 폐기 |
| fusion | RGB/depth/detection callback 진입, 완성 bundle 선택, worker 취득, depth 처리, TF 조회 시작/완료, target publish 호출 구간 및 실패 |
| manipulation | target callback 진입, 제어 판단, 명령 dispatch 또는 gate-lost 시각, 원 목표 촬영 시각 |
| observer | trace 메시지의 수신 시각. 발생 시각을 덮어쓰지 않음 |

native submit은 기존 pending slot에 고정 크기 timing metadata만 복사한다.
producer/control 경로에서 JSON 직렬화·디스크 기록·새 ROS trace publish를 하지 않는다.
frame/lease의 시각 metadata를 worker까지 함께 전달해 snapshot과 분리되지 않게 한다.
pending overwrite는 기존 정책을 유지하며 sequence 누락을 곧바로 전송 손실로 단정하지 않는다.

RGB/depth/Info와 trace의 도착 순서를 가정하지 않는다. join은 실행 UUID·source_frame·
정확한 capture_ns로 후보를 찾고 native_sequence/local epoch를 보존한다.
다른 노드의 local_epoch 숫자를 동일한 전역 epoch로 취급하지 않는다.
시계 rollback으로 같은 stamp의 후보가 둘 이상이면 ambiguous로 남기고 차이를 계산하지 않는다.
완전한 연결이 없는 프레임은 unmatched다. nearest stamp나 now로 임의 보충하지 않는다.
단조 증가 구간의 연결 가능한 샘플만 통계에 사용하며 전체 수와 누락 수를 함께 표시한다.

publish 호출 구간은 DDS 구독자 도착 시간이나 middleware 내부 전송 시간 자체가 아니다.
publish 이후 receiver까지의 잔여 구간에는 DDS·스케줄링·callback 대기가 함께 들어갈 수 있다.
이 한계를 명시하고 계측으로 분리하지 못한 원인을 특정 구성요소의 결함으로 단정하지 않는다.

## 5. 계측 부하·크기 제한

진단은 별도 /vision/camera_trace, /vision/detector_trace, /vision/fusion_trace,
/architecture/tracking_trace의 std_msgs/String JSON으로 내보낸다.
BEST_EFFORT/VOLATILE, depth32로 제한하며 제어 판단이 trace 전달을 기다리지 않는다.
노드당 프레임 요약 한 건으로 단계 시간을 묶고 평문 per-event 로그 폭주를 피한다.
최대 payload4096byte, 세션당20000건과 drop/oversize 카운터를 둔다.
limit에 도달하면 이후 상세 기록은 중단하고 불완전 계측임을 결과에 남긴다.
상태/사건 sequence로 누락을 식별하고, 알 수 없는 누락을0으로 가정하지 않는다.

observer는 제한된 metadata만 보관하고 기존 최종 dump 때 trace.jsonl과 trace_summary.json을
쓴다. 매 frame 파일 flush나 영상 복제를 추가하지 않는다. 원본 trace는 SHA artifact로 등록한다.
목표 callback의 trace도 현재 제어 lock 안에서 무거운 직렬화·파일 기록을 하지 않는다.
측정 metadata를 잠깐 복사한 뒤 lock 밖에서 직렬화하되 복사 당시 시각을 유지한다.

## 6. 분석 결과와 증거

trace_summary는 동일 capture의 연결된 구간별 count·p50·p95·max·최악 capture ID,
유효 target의 갱신 간격과 제어 정지 직전 촬영 age/receipt age를 출력한다.
동일 clock-domain 내 이전 결과 age와 다음 갱신 간격을 함께 보며300ms 여유를 설명한다.
관측기 wall 수신 간격을 native 렌더 주기나 원래 publish 주기로 대신하지 않는다.
검증한 clock/키 연결과 데이터가 부족하면 해당 분석은 UNVERIFIED로 남긴다.
계측 성공/제품 성공/정상 종료를 각기 별도 항목으로 판정한다.

새 evidence에는 고유 UUID, 소스/설치 manifest, 실제 camera/mailbox .so 경로·해시,
EGL renderer 증거, trace 원본/요약, 원래 observations/result/log/JUnit을 보존한다.
기존30회 실패나 GLFW 실측을 EGL 결과로 다시 명명하지 않는다.
기존 library probe는 로딩 증거일 뿐 EGL 초기화 성공으로 취급하지 않는다.

## 7. 시험과 합격 기준

구현 계획은 다음 시험을 RED→GREEN 순서로 구체화해야 한다.

- plugin 실행 중 GLFW 호출0, 모든 EGL context/surface/GL 생성·사용·해제의 worker TID 일치.
  실제 GL/EGL 시험과 호출 관측을 함께 사용하며 영상 mock으로 대체하지 않는다.
- EGL 단계별 실패 후 재초기화·이중 cleanup·렌더 busy 중 stop/join·전부 disabled.
  같은 display의 peer context는 카메라 cleanup 후에도 유효해야 한다.
- 기존 snapshot overwrite/rollback/header/depth/flip/polled/단일 loaded library 회귀 유지.
- native timing metadata가 실제 취득 lease와 일치하고 overwrite/reset/stop에서 혼합되지 않음.
- trace disabled이면 추가 계측 발행0. UUID 누락/잘못된 schema/negative duration/
  다른 clock/rollback 중복 stamp/누락/상한 도달은 허위 종단 지연으로 합산하지 않음.
- 실제 ROS 경계에서 detector/fusion/manipulation의 원 촬영 header 보존과 stage 시각 순서.
  trace 전달 실패가 목표 TTL·액션 소유권·제어 상태를 갱신하지 않음.
- 전체 소스·다섯 패키지·설치 일치 감사 통과. 테스트0건이나 skip을 PASS로 세지 않음.

### 실제 엔진 순서

1. 새 고정 설치본으로 EGL 초기화/부분 실패/정상 종료와 snapshot static30 고유 촬영
   RMS≤.03m, motion+150ms delay30 고유 촬영 RMS≤.05m를 확인한다.
2. 같은 소스/환경의 tracing OFF/ON 정적 실행을 비교해 출력 주기·지연·정리·기하 결과와
   실제 diagnostic 부하를 보존한다. 이 소수 비교를 통계적인 무부하 보장으로 표현하지 않는다.
3. tracing ON에서 clean10Hz3회와15Hz3회를 각각 별도 엔진으로 실행한다.
   기존5초·픽셀20% 감소·명령/각도/측정 속도·단일 소유권·정상 종료 기준은 불변이다.
4. trace가 실패해도 native acceptance 항목을 무시하지 않는다. 기존 images/tf/joints 손실,
   두 엔진의 기존 기능·컵 YOLO·종료 회귀를 새 소스로 확인하고 결과를 독립 기록한다.
   Gazebo renderer/bridge 구현은 바꾸지 않는다.

## 8. 경계와 다음 단계

이번 첫 수정은 EGL 계약·관측 가능성에 한정한다. 계측 후 원인이 확인되기 전에
제어 lock/executor 구조, 액션 재시도/timeout, Gazebo plugin/신호 정책을 함께 고치지 않는다.
액션 terminal 전달과 Gazebo 종료 원인은 후속 독립 조사·설계 대상이다.
PPO/MoveIt/물리 파지/Nav2/실로봇/GUI는 이번 범위의 성공 항목이 아니다.
카메라 계약 수정이 통과해도 연속 추적·취소·정상 종료가 미달이면 전체13.4 FAIL,
기본 backend의 upstream 유지와13.5 보류를 그대로 기록한다.

서면 설계 승인 후 테스트 우선 구현 계획을 작성한다. 계획 검토 후 네이티브 구현·
실제 엔진 검증·문서/evidence·절 브랜치 commit/push 및 원격 SHA 검증을 진행한다.
이번 문서 작성으로 새 구현이나 새 엔진 성공을 주장하지 않는다.

## 근거

- [GLFW 스레드 계약](https://www.glfw.org/docs/latest/intro.html#thread_safety)
- [MuJoCo3.3.7 Visualization](https://mujoco.readthedocs.io/en/3.3.7/programming/visualization.html)
- [Khronos eglTerminate 원문](https://github.com/KhronosGroup/EGL-Registry/blob/main/sdk/docs/man/html/eglTerminate.xhtml)
- [기존 snapshot 설계](2026-10-19-camera-snapshot-ownership-design.md)
- [보존한 헤더·호출 증거](../../evidence/section_13_4/cam-66d636a0/glfw-contract.log)
