# 13.4 종단 인수 해결 기록

시작 2026-10-21, 기준64f6c0ce91637e90ef44f1dc9c49c7d747adc91f, 깨끗한 작업트리.
사용자 지정 checkout과 새 feat/ch13-section-13-4-completion 브랜치를 사용한다.
원격 기존 절 브랜치는91c02156fdcb50eac1de58d412ac95e7f8d34149이며 새 이름은 없었다.
sources/와 Ch01~Ch12 및 외부 underlay는 읽기 전용이다. 단일 작업자, 자체 리뷰.

## 승인·완료 계약

이번 요청은 fusion 연속성, 실제 액션 terminal 수신, 엔진/runtime 정상 종료의
내부 재설계를 승인한다. 기존 EGL 소유권 구현을 재사용한다. 320×240/카메라15Hz,
추론10Hz(선택15Hz), 촬영·수신300ms, TF100ms, 팔5Hz 및 단일 소유권을 유지한다.
기존20회 matrix+양 엔진13.3 회귀를 최종 동결본에서 실행하며, 간헐 조건은
실패를 제외하지 않고 연속3회 통과해야 한다. 원격 non-force push와 SHA 일치가 마지막 단계다.
PPO/MoveIt/물리 파지/Nav2/13.5는 확장하지 않는다.

Ruling: 사용자 지정 checkout 재사용 — 경로와 기존 측정 자산 보존 요구 — 별도 파일시스템 격리는 없다.
Ruling: 설계·구현 세부 재승인 없이 진행 — 이번 사용자 명시 지시 — 판단 근거와 회귀를 이 기록에 공개한다.
Ruling: 독립 에이전트 리뷰 대신 자체 리뷰 — 네이티브 단일 작업자 지정 — 독립 검토의 이점은 없다.

## 진행 순서

- [x] 최소 재현으로 입력→후보→fusion 갱신 공백을 설명하고 수정한다.
- [x] 실제 controller 결과 요청/응답/클라이언트 수신과 취소 소유권을 수정·검증한다.
- [x] runtime과 Gazebo 종료 순서를 재현·수정한다.
- [x] 코드 동결, 소스·패키지·설치 감사,20+2 matrix와 간헐 조건 연속3회.
- [x] 한글 가이드·리뷰·REUSE·evidence와 non-force push/SHA 검증.

## 증거·다음 재현

새 작업 UUID f8c0bed5-cdac-43d8-81ff-84ab88360cdb.
evidence: Ch13/evidence/section_13_4/completion-f8c0bed5.
최초 가설은 RGB-D 후보 불완성/거부와 실제 수신 지연을 분리하는 것이다.
기존 trace의 부재만으로 callback 미실행을 단정하지 않는다.
현재 코드의 try_pending은 미완성 후보 사유를 남기지 않는다. 같은 촬영의 입력 수신,
캐시 상태, 제출·덮어쓰기·만료 및 worker 처리를 bounded metadata로 기록하고
기존 m10 tracking 한 회를 판별 실험으로 사용한다. 아직 제품 수정·성공 주장은 없다.

### 후보 진단과 첫 판별

candidate-red2: 실제 ROS 미제출 후보 기록 부재로1FAIL. candidate-green:4PASS.
candidate-red.log는 WSL 초기 실행 중 결과 미수집이며 행동 RED로 세지 않는다.
candidate-build:5패키지 빌드 PASS. candidate-m10 실제 MuJoCo는 추적 FAIL,
각도/속도/주기/정상 종료 PASS, owned 잔여 없음. 촬영18.464s의 depth와 detection은
도착했으나 RGB는 캐시에 없고 WAIT_RGB에 머물렀다. 이 구간 진단 순번1452~1456은
연속이며 그 시점 RGB 캐시의 최신 촬영은18.394s. 이전 시작 구간의 진단 유실은 별도다.
이로써 누락은 worker/TF 이전의 완성 후보 입력 경계다. 물리 네트워크 패킷 유실 원인까지
확정한 것은 아니다. fusion 입력을 유계 reliable로 요청하고 detection/CameraInfo 및
Gazebo bridge도 호환되게 맞춰 비교한다. 소스 capture/TTL은 변경하지 않는다.
reliable-red: 실제 RGB subscription이 BEST_EFFORT여서1FAIL/진단1PASS.

reliable-green8PASS,5패키지 재빌드 PASS. reliable-m10은4명령 후 target_fresh로 FAIL,
정상 종료/제한 검사는 PASS. 마지막 구간에는 RGB/depth가 모두 도착했다.
전체 수신 trace의 native_render p95 84.29ms, queue55.11ms, detector_queue74.86ms,
fusion_queue92.65ms(서로 다른 표본의 분위수이며 합산한 종단 지연이 아님).
따라서 reliable만으로 완료되지 않는다. 다음 판별은 동일 소스/추론10Hz에서
해당 실행 프로세스에만 LP_NUM_THREADS=2 적용(cpu2-m10). 카메라/해상도/기한은 동일.
이 초기 비교의 환경은 호출 명령에 보존한다. 이후 helper는 환경 JSON도 자동 기록한다.
액션 경계 진단은 별도 action_boundary.c로 실제 rcl_action 호출을 그대로 전달하며
client send/server take/server send/client take를 구분한다. 외부 파일 수정 없음.

### 재개 후 판별(2026-10-21)

cpu2-m10 FAIL: native render p95 128.33ms로 악화. LP_NUM_THREADS=2는 채택하지 않는다.
render-eye는 실제 eye_in_hand 카메라의 별도 EGL 비용 분리 실험이다(종단 인수 아님).
원래4096 shadow/4 samples p95 26.78ms, shadow512 9.22ms, no_msaa29.08ms.
제품 렌더 품질·해상도는 아직 변경하지 않았다. 전체 시스템에서 더 큰 지연이 발생하므로
이 단독 실험만으로 렌더 설정을 만능 원인/해결책이라고 판단하지 않는다.
일시적인 도구 승인 검토 사용량 제한 후 사용자 재개로 일반 권한 실행이 복구됐다.

action-m10 (b01e710c-963a-4370-b1c5-4616a9e09fea): 추적 FAIL, 정상 종료 PASS.
실제 controller의 seq2 결과 요청(client_send/server_take), status5 응답(server_send),
클라이언트 수신(client_take)을 모두 관찰했다. 취소 요청~응답 수신은 약113ms.
이번 성공을 과거 간헐 실패 해결로 선언하지 않는다. 촬영 age312ms에서 안전 정지했다.
action-g10 (4c41456a-e93a-4f34-b0c7-f540a51e6d1d): fresh_target 대기 FAIL,
정상 종료 PASS/잔여 없음. 홈 목표 status4 결과의 네 경계는 관찰했다.
카메라3개 bridge가 `Invalid QoS profile 'DEFAULT'`로 생성되지 않았다.
이는 이번 reliable 변경의 결함이며, 실제 파서/ROS publisher 생성 회귀부터 수정한다.
양 실행 모두 실패 원본과 returncode1을 보존한다. 연속 성공으로 계산하지 않는다.

bridge-red: 실제 브리지3개 publisher 부재1FAIL. qos_profile 생략(브리지 기본 reliable)
후 bridge-green1PASS,5패키지 빌드 PASS. bridge-g10 UUID
cd14811a-bc0d-4636-a504-963b491ba9a2는 추적5초/픽셀 감소/모든 motion 제한 PASS,
실제16번째 목표 status5 result의 네 경계 관찰. Gazebo 종료만 FAIL(SIGTERM 필요),
runtime 노드들은 정상 종료했고 최종 owned 잔여 없음. 성공 실행으로 세지 않는다.
일반 attach는 ptrace 제한으로 실패했으므로 부모 GDB 진단을 별도 시작했다.
부모 진단은 시간/PGID가 달라지므로 인수 성공으로 승격하지 않는다.

clock-load 별도 ROS도메인158:500Hz 합성 시계/idle MissionCommander/각5초.
SingleThreaded CPU1.723초, Multi(1)5.384초, Multi(4)5.295초.
멀티 실행 종료에서 Destroyable 예외도 기록됐다. 단독 비용 분리 실험으로,
실제 시스템의 유일한 지연 원인이라는 뜻은 아니다.
Ruling: 대기 없는 LocomotionNode만 single executor로 변경 — 측정된 Python pool
handoff 비용 제거 — 실제50Hz/기존13.3 회귀를 다시 확인해야 한다.
동기 service/action 대기가 있는 manipulation/mission은 아직 pool을 유지한다.
executor-red: 단일 모드가 callback을 worker에서 실행하여1FAIL/기존 종료1PASS.
executor-green5PASS,5패키지 재빌드 PASS. executor-m10
(b8066ebe-ae7c-4186-a02c-f8e2a82e0e2a)는 추적 FAIL/정상 종료 PASS/잔여 없음.
실행 중 locomotion CPU는 약33.8%였지만 단독 executor 수정은 시간 예산을 해결하지 못했다.
부모 GDB (3a522e70-de34-428f-9278-f1bacbdfed36)는 정상 exit0/추적 성공을 관찰했으나
타이밍을 바꾼 진단이므로 인수 결과에서 제외한다.

Ruling: Ch13 vision_fixture의 shadow map4096→512 비교 — 실제 eye_in_hand EGL
비용 분리에서 p95 26.78→9.22ms, 반복 native 추적 실패가 RED — 그림자 경계 품질이
변하므로 실제 고정 YOLO/기하/추적 재검증 전 채택 완료로 보지 않는다.
이는 카메라 RGB-D 출력320×240, intrinsics, physics,15Hz 및300ms를 변경하지 않는다.
외부 원본/드라이버/엔진 라이브러리는 수정하지 않는다.

shadow-m10(14b47018-ffff-49f8-bc39-055381f9a2e7): 추적 FAIL/정상 종료 PASS.
native queue p95 2.51ms/render40.23ms로 줄었지만 촬영21.818s 이후 약0.28s 동안
탐지가 갱신되지 않았다. fusion에는21.890/21.964/22.034s RGB가 도착했으나
탐지기의 QUEUED 기록은 없었다. trace 부재만으로 미수신을 확정하지 않는다.
탐지기 ingress는 여전히 best-effort였으므로 bounded reliable로 맞추고,
수신/제출 전 거부 사유를 촬영별로 기록한다. 아직 모든 누락의 원인 확정은 아니다.
detector-input-red2FAIL. 첫 green은 report 인자 reason 충돌1FAIL/8PASS였고 수정 중이다.

Gazebo quiesce-red3FAIL → quiesce-green3PASS. 이번 순서는 추적 취소 drain 이후
world pause RPC와 실제 stats.paused=true를 확인한 뒤 server stop을 요청한다.
공식 gz-sim8 Sensors의 PostUpdate/Stop 대기를 참고한 수명 경합 완화이며,
특정 upstream 교착의 근본 원인까지 입증했다고 주장하지 않는다.
quiesce-g10 UUID8881bb62-48b8-4f76-ad12-28bf8f68d196는 실제 tracking/모든 제한/
normal shutdown PASS, native exit0 및 잔여 없음. 연속3회/최종 동결 회귀는 미실행.
관련 공식 소스: https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/sensors/Sensors.cc

2026-10-21 20:46까지 자동 승인 검토 사용량 제한으로 detector RED 실행이 미실행이었다.
사용자 재개 후 일반 사용자 실행이 복구됐고 위 RED2FAIL을 실제 수집했다.

detector-input-green2:9PASS. detector-input-build:5패키지 PASS.
detector-m10(UUIDeaae54dd-f9db-4f85-bc49-6b34ad9fe0fe)는 실제 MuJoCo 추적5초/
픽셀 감소/모든 제한/실제 액션 terminal/정상 종료 PASS, owned 잔여 없음.
입력 reliable와 제출 전 진단을 추가한 고정 소스의 첫 성공이며 연속3회는 아직 아니다.
다음: 소스·패키지 suite/설치 감사 및 native 최종 matrix 준비. 새로운 런타임 변경 없이
인수 반복을 실행한다. package.xml에 실제 브리지 회귀의 test dependency를 명시했다.

source-suite:353PASS/1FAIL(143.17s). 실패는 fresh-install audit이며 실행 helper가
이전 EGL overlay와 source PYTHONPATH를 자식 interpreter에 넘긴 것이 원인이다.
제품 감사는 의도대로 stale Python module을 거부했다. test.sh를 현재 overlay만
사용하도록 수정하고 conftest의 소스 선택과 별도 자식 설치 감사를 유지한다.
검사 기준이나 실패 테스트를 제거하지 않는다.

fresh install 감사 회귀21PASS, 현재5패키지 빌드 PASS.
legacy-probe: MuJoCo PASS. Gazebo는 첫 정상 dry-run 수락 검사에서 FAIL했고
5개 runtime은 정상 종료했지만 엔진 SIGTERM이 필요했다. snapshot 없이 포괄 오류만
있어 최초 거부 원인은 미확정이다. accept_goal의 기존 판정 값을 구조화해 기록했다.
legacy-readiness: Gazebo13.3 기능/취소/겹침 거부 등 전체 기능은 PASS였고 runtime
정상 종료 PASS지만 엔진 SIGTERM 때문에 wrapper FAIL. 이때 idle=false 거부는
의도한 겹침 목표였으며, fresh pose/owner 자체는 정상으로 관찰됐다.

legacy-stop-red: 실제 소유 자식의 종료 정보를 반환하지 않아1FAIL.
legacy-stop-green: 기존 descendant 정리 회귀와 합쳐2PASS.
13.3 runner도 이미 검증한 소유 group 정리를 재사용하고 실제 forced/residual/exitcode를
결과에 남긴다. runtime을 먼저 끝낸 뒤 Gazebo section_13_2 세계를 pause/stat 확인하고
server stop을 요청한다. 엔진 정상 종료도 PASS 조건에 추가하여 검사를 강화했다.
legacy-quiesce: Gazebo13.3 전체 기능과 runtime/engine 정상 종료 PASS.
world paused 관찰/server stop ACK/native 종료/각 소유 group exit0·forced=false·잔여 없음을
기록했다. 최초 거부는 다음 두 기능 실행에서는 재현되지 않았으며 원인 미확정을 유지한다.
현재 소스 전체 회귀와 패키지 검사 이후 동결·최종 geometry부터 진행한다.

자체 리뷰:13.3 runner의 엔진 시작 전 실패가 원래 오류 대신 누락 runtime.log 예외로
덮이는 새 결함을 발견. legacy-launch-red1FAIL → legacy-launch-green2PASS.
없는 로그를 정상으로 세지 않고 cleanup/engine 존재를 요구한다.
source-suite-current:354PASS/1FAIL. 기존 shutdown 경계 시험이 서비스 discovery만
기다리고 action discovery를 확인하지 않아 action_ready=false로 최초 enable이 거부됐다.
300ms fixture를 생성하기 전에 실제 ActionClient.wait_for_server를 확인하도록 수정했다.
활성화 재시도·유효기간 완화는 하지 않는다. 해당 회귀와 전체 검사를 재실행한다.
최종 matrix는 아직 시작하지 않았으며 변경 없는 전체 엔진 반복은 하지 않았다.

tracking-discovery-green16PASS, source-final356PASS/140.43s.
package-suite188tests/0errors/0failures/0skipped, 설치본5패키지 byte/C++ manifest 감사 PASS.
자체 리뷰에서13.4 engine-first 종료 순서가 runtime 명령 ingress/worker보다 빠른 점을
보완했다. runtime-order-red1FAIL → runtime-order-green(기존 종료 회귀 포함)6PASS.
소유 launch group의 알려진 runtime/vision console만 SIGINT로 닫고 실제 종료를 확인한
뒤 engine stop을 요청한다. 일반 bridge/RSP/engine은 runtime drain 중 살아 있다.
최종 동결 후 해당 실제 엔진 시험을 실행하며, 최종 소스 suite는 추가 회귀까지 다시 확인한다.

동결 batch UUIDdea3ef6a-90ad-4e8e-9c2a-3789b5ec1d01,
final/frozen-source.json: source149files/installed342files, 기존 required_checks 감소 없음 확인.
첫 driver는 file_digest에 str을 넘겨 엔진 시작 전에 중단됐다. Path로 바꾼 뒤 동일 동결본의
최종 geometry→tracking→remaining→legacy 순서로 시작한다. 제품 소스 변경 없음.

final batch1은 static-off/static-on/delay-on3PASS 후 m10a에서 FAIL하고 중단했다.
m10a(a1108a55-1faa-4bb7-96dc-593b8fd57daa)는 추적5초/명령 및 측정 제한/
실제 terminal/정상 종료 PASS였으나 pixel_error_reduction만 FAIL(reduction=null).
원본30개 표본의 첫 측정은 첫 명령 이후였고, 제어 전 initial 표본은3개 미만이었다.
1초 pump를 표본 준비라고 가정하고 fresh_target 대기 전에 initial 리스트를 복사한
시험 준비 결함이다. 임계값을 바꾸거나 뒤의 표본을 초기값으로 소급하지 않는다.
baseline-red2FAIL 후 실제 고유 촬영3개/finite error/기존 median>1px를 확인하는
tracking_baseline barrier와 제어 전 capture/wall/command_count 기록을 추가했다.
먼저 관련 MuJoCo tracking만 검증한 뒤 새 final-v2 batch에 다시 동결한다.
기존 final/ 실패 결과와 진행 원본은 그대로 보존하며 성공 연속 횟수로 세지 않는다.
baseline-green34PASS(준비 회귀2건+기존 runner32건).
baseline-m10(b5e441b7-a1a2-400d-ab4c-8038837729e5) PASS: 제어 전3고유 촬영,
command_count0, initial6.0208px→final0.5px(91.7% 감소),5.200s 추적,
명령/측정 제한·terminal·정상 종료 PASS/잔여 없음.
source-final-v2 전체와 새로운 final-v2 동결/전체 인수를 시작한다.
패키지188건이 검증한 패키지 소스/설치 바이트는 변하지 않았고,
추가 수정은 Ch13 runner와 그 테스트에 한정되며 새 동결에서 다시 감사한다.

source-final-v2:359PASS/124.88s. final-v2 batch
5eed023d-23ac-485b-9b8d-385e9395e577, source150/installed342files,
frozen-source.json SHA2561c46ab332ab4a6d9a8afb56ff2eb46153ffa7670efc049e296c554a2dc5dee68.
현재 static-off/static-on/delay-on/m10a/m10b5건 PASS이며 m10c 진행 중이다.
각 실행 전후 source/install 해시와 다음 엔진 시작 전 소유 정리를 확인한다.
재개 시 final-v2/matrix-progress.jsonl과 활성 실행의 result.json/processes를 먼저 확인한다.
기존 PASS를 무조건 재실행하거나 RUNNING 결과를 성공으로 세지 않는다.

final-v2는 정적/지연3PASS,10Hz추적3연속PASS 뒤 m15a에서 중단됐다.
m15a(805c250a-8ade-47c1-b868-8b0053962ba9): pixel100% 감소/모든 제한/정상 종료 PASS,
five_second_tracking만 FAIL.13번째 목표가5718.432s에 제출됐고 서버는 곧 수락·성공했지만
클라이언트 owner의 accepted 이벤트는5720.789s로 약2.36초 늦었다.
그동안 소유권을 유지해 후속 명령은 없었고, 종료 취소 후 실제 terminal4를 수신했다.
취소500ms fault는 자동 해제하지 않았다. 최종 last-first 명령 구간이4.5초 미만이었다.
이는 기준 표본 문제와 다르다. 공유 callback 실행기에서 액션 응답/완료 전달이 지연되는
경계를 goal RPC·future 상태까지 계측한 뒤, 전용 액션 수신 실행 루프의 필요성을 판별한다.
기존 final-v2 실패를 보존하고 성공만 골라 연속 횟수를 다시 세지 않는다.

재개 확인: HEAD64f6c0c/동일 completion 브랜치, 기존 변경 보존.
acceptance-m15 진단은 PASS였지만 간헐 결함이 해결됐다는 증거로 세지 않는다.
실제 독립 ActionServer를 두고 부모의 네 worker를 모두 점유한 최소 재현에서,
서버 실행 후500ms가 지나도 acceptance_future_done=false/terminal=false(RED1FAIL)를 확인했다.
ArmActionTransport는 별도 저부하 ROS 노드/SingleThreadedExecutor 수신 스레드를 소유하고,
ArmActionOwner는 기존 단일 명령 소유권과 실제 result future 확인을 그대로 유지한다.
별도 노드는 전역 use_sim_time/__node 설정을 상속하지 않아 clock/영상/TF 작업을 받지 않는다.
부모 생성의 마지막에만 수신 스레드를 시작하고, 취소·실제 결과 drain 뒤 context보다 먼저 종료한다.
수신 스레드 실패는 자동 재시작하지 않고 action_ready를 차단한다.
isolation+기존 owner/tracking/cleanup 회귀23PASS. 새 설치 후 실제15Hz 시험으로 검증한다.

transport-m15(72a8e568-b0a8-42b5-86e4-979ee6edb2f9)은 목표 신선도 FAIL,
액션 실제 terminal/정상 종료 PASS/잔여 없음이었다. 10번째 목표 후 촬영26.054s가
ROS26.358s에서304ms가 되어 latch OFF했다. 후속26.122s 촬영도 수신·후보 제출·
worker·TF·발행이 있었으나 CPU/제어 lock 대기가 누적됐다. callback 부재가 아니다.
numeric-budget paired probe: OpenCV8threads fixture300회 CPU1.977s/p95 2.545ms,
1thread CPU0.388s/p95 1.668ms. BLAS/OMP 제한은 servo를 개선하지 않아 채택하지 않는다.
opencv-budget-red1FAIL 후 탐지 프로세스의 OpenCV만1thread로 제한한다.
초기 probe의 threadpoolctl 미설치 오류는 의존성 설치로 우회하지 않고, 새 프로세스의
실제 환경/스레드 수 비교로 대체했다. 빈 numeric-budget.json은 초기 오류 산출물이다.

opencv-budget-green10PASS. opencv-m15(a00fb936-8a5f-48b6-9b4d-e910b8d45ee1)은
1.836s/5명령 뒤 invalid/lost target FAIL, 실제 terminal/정상 종료 PASS였다.
작은 탐지 CPU 개선만으로 종단 계약을 충족하지 못했다. 원본 trace에서 서보 계산이
공유 node.lock을 약203ms 잡고 입력26989 촬영의 callback이 약149ms 기다린 구간을 확인했다.
servo-ingress-red는 계산 중 실제 on_target 안전 무효화가 잠금에 막힘을 재현했다(1FAIL).
제어 계산 입력을 독립 snapshot으로 복사한 뒤 잠금 밖에서 TF/math를 수행하도록 분리했다.
재진입 시 generation·모델·현재 모든 조건·실제 계산에 사용한 target/joint 촬영/수신 age를
다시 검사한다. 최신 입력만으로 오래된 계산을 합법화하지 않는다.
추적 trace도 계산 시작 촬영을 보존한다. 첫 회귀19PASS/1FAIL은 trace 키 중복 TypeError였고,
해당 오류를 수정한 servo-ingress-green2는20PASS였다. 계산 중 무효화는 즉시 처리되고
늦은 명령은0, 계산 만료 시 기존300ms 정지는 유지된다. 새 설치 실제15Hz를 진행한다.

servo-snapshot-m15(33385867-1115-4fe1-bf5f-1834d92822a4) PASS:
5.20175s/18명령,6.0208→0px, 최단 명령 간격245ms,
측정 최대 속도0.05586rad/s·각도0.02150rad, 실제 terminal/정상 종료/잔여 없음.
새 final-v3에서 source/package/install 전체 감사 후 동결하여 전 matrix와13.3 회귀를
실행한다. 재개 시 final-v3 progress와 활성 프로세스를 먼저 확인한다.

source-final-v3:364PASS/150.82s. package-final-v3:193tests/0errors/0failures/0skips,
5packages PASS, 독립 설치 감사 PASS. final-v3 batch UUID
ec6001a5-4341-4daa-9d7e-e46c153b2998, source152/installed343files에 동결했다.
동결 명세 SHA256:81b2b85d50db944e0eaf00a87c0ea992172c6c44d8e2707ae6e617bac08c4b80.
이후 런타임 변경 없이 geometry→10/15Hz추적각3회→semantic/safety/Gazebo→legacy 순차 실행 중이다.
실행 helper18개는 evidence/workflow에 바이트 동일 복사로 보존했다.

final-v3는 static-off/static-on/delay-on3PASS 후 m10a에서 FAIL하여 중단했다.
실패 UUID982e45ca-a718-48a0-a3b5-f5131e9fda56, 정상 종료/소유권 drain PASS.
새 목표는 계속 도착했다. 계산은 촬영27.242s를 사용했으나 계산 종료 시 ROS27.544s로
약302ms가 되어 거절됐다. 그때 최신27.378s 목표는166ms였다. 최신 입력으로 오래된
계산을 합법화하지 않은 올바른 안전 거절이며, 계산 비용 자체를 줄여야 한다.
기존 servo는 매번 정적 URDF origin/axis/limit를 재해석하고 유한차분 때문에5회 FK를 했다.
비영 자세의 독립 MuJoCo 카메라/Jacobian 회귀2FAIL 후, 정적 기구학을 모델 수명에
컴파일하고 한 번의 FK와 관절 screw로 동일한 투영 Jacobian을 계산하도록 바꾼다.
기존 수치·각도·속도·세대·신선도 제한은 바꾸지 않는다. 변경 후 새 설치/성능/실제 시험과
새 동결 batch가 필요하며 기존 final-v3 실패는 보존한다.

compiled-kinematics-green29PASS. numeric-budget-compiled은 servo300회 CPU0.0726s,
p95 0.326ms(기존8.705ms)로 개선됐다. compiled-m10(58367eda-7cdd-4930-8511-32ddde1d6c14)은
LOST(촬영22.326→ROS22.628s)로 FAIL했다. 계산만이 원인은 아니다.
single-protocol-red는 단일 입력 실행기에서 원래 blocking stow가 시계/입력을 막음을
실제 ROS service/controller로 재현했다. 기존500Hz clock 비용 비교의 단일 실행기 이점을
활용하기 위해 manipulation 입력 실행기를 단일화하고, 긴 stow/PickObject 프로토콜만
동시에1건인 worker로 위임/await한다. 큐/자동 재시도는 없다. 액션 수신 전용 실행기는 유지한다.
single-protocol-green21PASS, 새로운 설치·실제10Hz 확인을 진행한다.

single-protocol-lifetime-green2PASS(중복 거절/시동 중 종료 포함).
single-m10(ac04a23d-ff7a-41c8-9724-d595c83b102f)은 실제 result 미수신으로 FAIL.
single-rpc-m10(c45c8d26-397f-431a-8f78-d48a4413a1fa)은 추적5.2s/22명령/픽셀91.7%/
모든 측정 제한 PASS였으나 마지막 취소·종료 FAIL이었다. 마지막UUID04cd9dc6688e4dacbe0cd70bee066748의
result 요청은 서버 take(seq25)까지 확인됐지만 server_send는 없었다. goal reached와cancel이10ms
간격으로 발생했고 client handle은CANCELING3/result_future_done=false로 남았다.
이를 클라이언트 callback 부재로 단정하지 않는다.

설치된 realtime_tools3.13.0의 실제 C++ ROS action server/client 최소 재현:
RT setSucceeded→cancel ACCEPT→non-RT timer 순서에서 원본은 CANCELING에 남고 결과가500ms 내
수신되지 않았다(RED). 최초 진단 컴파일의 get_status API 오류는 행동 재현으로 세지 않았다.
rt-goal-original-confirm.log: cancel_ack0/terminal_resultfalse/server_cancelingtrue.
Ch13 전용 wrapper는 같은 조건에서 실제 CANCELED5 결과를 전달했다(rt-goal-patched.log PASS).

사용자 승인한 최소 외부 복사 범위로 integrated_robot_controller를 추가한다.
JTC4.42.1 cpp/hpp2개(커밋aacd842600a09d556b983ac3d53a0983e9ebcbb1/Apache-2.0),
realtime_tools3.13.0 header1개(459776c99f1f80606f7b9616496166ccaf207cf8/BSD-3-Clause)를
고정 출처·SHA256·라이선스와 함께 복사했다. 별도 namespace/plugin ID로 분리하며
기존 trajectory/parameter 구현은 설치본의 공개 API로 재사용한다. 외부 원본은 수정하지 않는다.
비전 경로만 파생 controller를 사용하고 vision=false13.2/13.3은 기존 controller 설정을 유지한다.
선택 회귀 RED2FAIL 후 구현했다. source/install 감사에도 새 패키지를 포함하며 새 최종 동결이 필요하다.

controller-selection-green2PASS, controller-mapping RED1FAIL→GREEN3PASS(선택 회귀 포함).
첫 controller-build는 CMake link signature 혼용으로 실패했고, plain signature로 통일한
controller-build2는6packages PASS였다(원본 API의 deprecated get_value 경고는 로그 보존).
controller-unit은2개의 C++ 경쟁 사례 PASS이며 colcon은 CTest 항목 포함3tests/0fail을 보고했다.
controller-rpc-m10(8908d643-79de-45da-9fc2-dd2121710d98) 실제 MuJoCo PASS:
5.2003s/22명령/6.0208→0px/최단간격212ms/측정속도0.05549rad/s/각도0.02130rad,
실제 terminal·정상 종료·잔여 없음. 엔진PID75203/PGID75184에 적재된 별도 controller.so
SHA2560078101fddf9d21f55dfa0f45a7664e02f943137dfdaed1ac86d4379aa539717을 확인했다.
final-v4는 interposer 없이 소스 전체→6패키지→설치 감사→새 동결/22native+2legacy를 실행한다.

2026-10-22 재개: source-final-v4는369PASS/2FAIL로 중단됐으며 엔진 batch는 시작되지 않았다.
실패는 Gazebo launch의 controller 이름 문자열 출현 횟수와 기존5패키지 기대값이었다.
Ruling: 이름 출현 횟수 대신 실제 spawner 선언을 평가해4개 제어기 각각1개와 manager를
검사하고, 설치 감사에는 새6번째 controller의 소스/라이브러리/라이선스도 확인한다.
기존 required_checks·물리 인수 기준은 변경하지 않는다. 새 로그는 기존 실패를 덮어쓰지 않는다.

외부 사례 검토: legubiao/quadruped_ros2_control main5434c5810d1a7fe223bcfd04550e9d3bfdd4b458의
제어 update/추론 worker 분리와 Gazebo executor cancel/join을 현재 수명 설계와 비교했다.
Unitree SDK2 DDS 어댑터로의 교체는 하지 않는다. 해당 RL worker의 무한 루프/명시 join 부재는
그대로 도입하지 않으며, 현재 owned worker·실제 terminal drain·정상 종료 순서를 유지한다.
이번 참고는 설계 비교뿐이며 외부 소스 복사는 없다. 서브에이전트 없이 직접 수행한다.

audit-alignment-green의1FAIL은 ROS launch cmd 요소가 substitution의 리스트라는 시험 코드
처리 오류였다. 정규화 API로 수정한 green2는24PASS다. 이후 자체 리뷰에서 계산 snapshot에
원래 target의 receipt wall 시간이 없음을 발견했다. 새 입력의 wall TTL로 예전 계산을
합법화할 수 있는 경계다. computation-wall-red는 최신 입력이 도착한 뒤에도 오래된 계산의
goal_count가1이 되는1FAIL을 재현했다(비물리 dispatch 경계 시험, 실제 엔진 성공으로 세지 않음).
원래 목표 수신 wall 시간을 snapshot에 보존하고 발행 직전 원래300ms 조건을 함께 검사한다.
verify-final-v4b 소유 드라이버PID1129만 TERM해 엔진 시작 전 중단했다. 실행 중이던 소스 시험의
불완전 로그는 보존하며 통과로 세지 않는다. 엔진/runtime 종료 성공 증거와 혼동하지 않는다.

computation-wall-green24PASS. wall-contract-build6packages PASS 뒤 source-final-v4c를 실행한다.
최종 준비 자체 리뷰는 사용자 지정 네이티브 단일 작업자로 수행했다(별도 리뷰 에이전트 없음).
수신기 thread 시작/실패/종료, protocol worker의 단일 작업과 context 이전 join, 목표 계산의
세대·촬영·수신 age, 별도 namespace controller의 실제 결과 전달, 원본 복사3파일의 라이선스,
vision=false 기존 제어기 유지, native 소유 PGID와 정상 종료 판정을 집중 검토했다.
권한 상승·외부 원본 변경·엔진 통신 방식 교체는 없으며 독립 리뷰보다 제한적인 자체 리뷰다.

source-final-v4c372PASS/184.72s. package-final-v4c는 description flake8 import 순서
I201/I1002건으로 실패하여 엔진 시작 전 중단했다. 원본 XML은 description-imports-red.xml에
복사 보존했다. Gazebo launch의 yaml import를 third-party 그룹의 올바른 순서로 옮긴다.
동작·기준 변경은 없다. 재설치 후 새 source-final-v4d/package-final-v4d 로그를 사용한다.

source-final-v4d372PASS/159.76s, package-final-v4d199tests/0errors/0failures/0skips,
6패키지 설치 감사 PASS. final-v4 UUID084026ad-ae1f-45c2-9536-1726011a86df는
소스167/설치380파일을 동결했다. frozen-source.json SHA256
40d24ecdb6eecb47452e6f8c5a9b95cb60af58fe009f13bfcedc2447d8b2a268.
LP/OMP/OPENBLAS/LD_PRELOAD는 모두 미설정, ROS domain157/MUJOCO_GL=egl이다.
workflow-final-v4d에 실제 실행 helper26개와 package-final-v4d-tests에 시험 XML을 보존했다.
현재 소유 검증 드라이버 세션52113이 geometry→tracking→remaining→legacy를 순차 수행한다.
재개 시 final-v4 진행·현재 result와 소유 프로세스를 먼저 확인하며 기존 실행을 중복하지 않는다.

final-v4 geometry3회(static-off/static-on/delay-on) 모두 PASS. 실제 controller.so hash는
0078101fddf9d21f55dfa0f45a7664e02f943137dfdaed1ac86d4379aa539717이며 소유 엔진 적재를 확인했다.
각 실행은 실제 runtime·엔진 정상 종료/잔여 없음. 이어10Hz와15Hz 추적 각3회를 수행한다.

final-v4 m10a/b/c3연속PASS. 추적5.20s,21/22/23명령,픽셀91.7% 감소,
각도·실측 속도·명령 주기·정상 종료/잔여 없음 모두 PASS였다. 원본 observations의
UUID별 실제 terminal 이벤트를 명령/취소와 대조해 미확정0을 확인했다(ACK/상태로 대체하지 않음).
15Hz 첫 실행m15a도 PASS이며 m15b/c를 이어 수행한다. 아직 최종 전체 완료가 아니다.

final-v4 m15a/b/c도3연속PASS: 추적5.20s,22/22/21명령,픽셀91.7/91.7/95.8% 감소.
원본 UUID별 실제 terminal과 취소 결과 미확정0, 정상 종료/잔여 없음, 동결 해시 유지.
이 batch는 현재9native PASS이며 실제 YOLO 컵/손실 대응/Gazebo/기존13.3을 이어 수행한다.

final-v4는 실제MuJoCo YOLO컵도PASS(113/113탐지) 뒤 mujoco-images에서FAIL해 중단했다.
영상 손실 정지·실제 취소 결과·엔진 정상 종료/잔여 없음은PASS였지만 launch가 manipulation
종료코드를255로 보고하여 clean_shutdown만FAIL했다. 원본 batch는10PASS/1FAIL로 보존한다.
system.log의 "exit status already read"는 설치Python3.12 PidfdChildWatcher 경로였다.
child_reaping_race.py에서 child정상exit0→좀비→다음send_signal의Popen.poll→pidfd callback
순서를 제어해 실제255와 동일 메시지를 재현했다. 런타임 자체 예외로 단정하지 않는다.
runtime-reaping-red는 부모가 아직 회수하지 않은 좀비를 stop완료로 선언함을1FAIL로 재현했다.
wait_owned_members_exit는 원래PID/start ticks가 /proc에서 사라질 때까지 기다리도록 강화한다.
기존8초 기한·소유권 검사·정상exit/로그 검사는 유지하며255를 무시하거나 성공으로 바꾸지 않는다.
최초green 명령은 파일명 오류로0tests였다. green2는38PASS/1FAIL이며 자신이 부모인Popen까지
회수를 남에게 기다린 회귀였다. 자기Popen만poll하고 나머지는 실제 launch부모의 회수를 기다린다.
수정 후 관련 실제 영상 손실을 우선 재검증한 뒤 새 final-v5에서 전체를 다시 동결한다.

runtime-reaping-green3는39PASS. reaped-images-a 실제MuJoCo PASS: 안전 정지/실제 취소/
정상 종료/잔여 없음. final-v4/source_archive에는 실패 당시167개 소스를 보존했으며,
추가 수정2파일을 되돌린 보존본이 기존 frozen-source의 모든SHA256과 일치함을 확인했다.
현재작업트리/기존 실패 결과는 되돌리지 않았다. 새 freeze는 모든 소스를 직접 보존하도록
evidence helper만 보완했다. reaped-images-b/c와 Gazebo images를 우선 확인한 뒤
source-final-v5/package-final-v5→final-v5 전체22native+2legacy를 수행한다.

reaped-images-a/b/c 실제MuJoCo3연속PASS와 reaped-gazebo-images 실제Gazebo PASS.
안전 정지/실제 취소/normal exit/부모 회수/잔여 없음 모두 확인했다. 현재 verify-final-v5.sh
(세션76893)가 source-final-v5→package-final-v5→새동결→전체matrix/legacy를 이어 수행한다.
패키지/모델/런타임 설치 바이트는 final-v4와 같으며 변경은 source runner의 종료 회수 경계와
관련 시험이다. 새 전체 인수의 결과만 최종 완료로 판정하고 이전 실패는 그대로 남긴다.

source-final-v5:373PASS/144.71s, package-final-v5:199tests/0errors/0failures/0skips,
6패키지 설치 감사 PASS. 구현·회귀·현재 문서는 중간 커밋
f2fa0eba4c042b00bb70f15b4066869ed370d84f로 보존했다(아직 원격게시/완료 선언 아님).
final-v5 batch4e8c9e6a-b53e-482a-a563-c09276ebfa84, 소스167/설치380파일과 소스 원본을
동결했다. frozen-source.json SHA256
6a94c7304319b2e49a3a7b6cd00c649b32fa8f8f850e1e20f05cf750f4537cb3.
현재세션76893이 전체22native+2legacy를 순차 수행한다. 소스 변경 없이 실행 중이며,
재개 시 final-v5/frozen-progress.jsonl과 활성 result/소유 프로세스를 먼저 확인한다.

final-v5 geometry3PASS. Ruling: remaining 단계는 미검증 긴 Gazebo 추적3회를 먼저 실행한 뒤
기존 컵/손실/기하 시험을 실행하도록 helper의 순서만 조정한다. 전체22개 label/required_checks와
고정 제품 소스/설치본은 같고, 이미 실행한 시험을 반복하지 않는다. 엔진별 소유 정리는 그대로다.
이후 실제 remaining/legacy helper는 workflow-final-v5-priority에 보존한다.

final-v5 geometry3회와MuJoCo10Hz/15Hz추적 각3회(합계9native) PASS.
각 추적은5.20s/픽셀91.7% 감소, 각도·실측 속도·주기/정상 종료/잔여 없음.
원본 observations의 모든 명령/취소UUID를 실제 terminal과 대조해 미확정0을 재확인했다.
현재 gazebo-tracking-a가 실행 중이며, 이어b/c→컵/손실/기하→legacy를 순차 수행한다.

gazebo-tracking-a/b/c도3연속PASS. 각각5.20s/픽셀100% 감소, 모든제한/실제 terminal/
정상runtime·native종료/관측pause/잔여 없음. 모든 명령·취소UUID의 실제 결과 미확정0을
원본관측에서 별도확인했다. final-v5는현재12native PASS이며 남은 컵/손실/기하/legacy를
동일동결본으로 이어 수행한다. 최종 전체 판정은 아직 아니다.

## 재개: final-v5의 22native 완료와 13.3 시험 입력 시계

final-v5의22native 모두PASS. legacy_mujoco는 실제READY 이후 probe120줄의 accepted
검사에서FAIL했다. runtime 로그는 입력이 서버 시계보다56ms 미래여서 기존50ms 한계를
초과했음을 보여준다. runtime/engine 정상종료는 모두PASS, 소유 잔여는 없다. 원본실패는
final-v5/legacy_mujoco와legacy-progress.jsonl에 보존하고 성공으로 덮어쓰지 않는다.

가설: 서로 별도 프로세스가 /clock을 받는 순서는 같지 않으며, 합성 목표를 만드는 즉시
전송하는13.3 probe가 아직 소비하지 않은 서버 clock보다 앞선다. 실제 ROS action과 원래
validate_target을 사용한 제어된60ms 시차 재현은 legacy-clock-red2에서1FAIL이었다.
첫red는 Jazzy에 없는QoS별칭의ImportError여서 결함 재현으로 세지 않는다.
제품 런타임은 수정하지 않는다. probe만 목표 생성/원래 header 보존→100ms pump→1회전송으로
바꾼다. 촬영시각 now교체·미래허용/300ms 연장·거절 후 재시도는 없다. 이는 인수 입력 준비
수정이므로 22native를 다시 돌리지 않고 영향받은 양엔진13.3를 새고정 supplement에서 검증한다.
소스 전체 변경분은 probe와 그 회귀 시험만 허용하고,167원본/380설치의 나머지 해시를 대조한다.

legacy-clock-green은1PASS. source-final-v5-probe는374PASS/193.29s.
legacy-clock-final batch76fb983c-7f3f-4249-b5fc-79d1da9dc71f에서MuJoCo
7b484898-7bc7-4bae-8665-801b725c54e5, Gazebo18dd0d53-8dd6-48ad-9da1-cd5994ea300b
모두PASS. 실제취소결과·미구현실패보존·5runtime노드/엔진exit0·강제정리없음·잔여없음.
before/after 감사에서제품/설치본 불변,168소스(시험추가1)/380설치 확인.

collect_final.py의 최종 교차 감사PASS:22native/양엔진legacy2, 원본artifact 크기/해시,
소스archive167+168해시,267명령 결과267,17취소요청 실제terminal17(16CANCELED5,
1SUCCEEDED4),최종pending없음. 기존legacy1FAIL은 summary에도 명시적으로 포함한다.
FINAL_POST_TRIAL_AUDIT도PASS: 일반UID1000, 소유runtime/엔진없음,
외부underlay c261f5552edf124d1000a23fb25b6c07cadeb807 clean. 이전장변경없음.
실제종단인수는PASS이며 문서·증거게시를 준비한다. 원격동명브랜치는2026-10-22조회에서없었다.
무권한네트워크조회1회는연결거절, 승인된네트워크읽기조회는성공했다. 시스템관리자권한은없다.
최종SHA는non-force push후 로컬/원격ref를 대조해 최종전달한다. main/PR/13.5는건드리지않는다.

## 게시 확인

구현 f2fa0eb와 최종증거/문서/13.3시험보완 fbea29f8b8c5bbcec7ccead0129918ada24d516e를
새 feat/ch13-section-13-4-completion에 non-force push했다. git ls-remote의 실제원격SHA와
로컬HEAD가 fbea29f8b8c5bbcec7ccead0129918ada24d516e로 일치했다. main병합/PR생성없음.
이 게시 확인 기록은 제품/시험을 바꾸지 않는 후속문서커밋이며, 그 최종HEAD/원격동일성도
별도로 확인해 최종응답에 남긴다. 원본실패/보존소스/새증거를 모두게시했다.

Windows 기본Git이 깊은 원본보존 경로2개를 Filename too long/삭제처럼 보고했으나
git -c core.longpaths=true status에서는깨끗하며 파일/해시는 존재했다. 사용자checkout의
로컬Git설정에만 core.longpaths=true를 적용했고 일반status도깨끗함을 확인했다.
시스템긴경로정책·전역Git설정·원본파일은변경하지 않았다. 향후Windows의 같은깊이
checkout에서도 해당Git로컬옵션이 필요할 수 있다.
