# 13.4 실패 수정 기록

기준: `cbd967e26d7d47223a6f5adb965e323eb7aee1ff`,
브랜치 `feat/ch13-section-13-4`. 네이티브 단일 작업자 실행.
이 문서는 진행 기록이며, 아래 미완료 항목을 성공으로 해석하지 않는다.
후속 검증 갱신일: 2026-10-19 (Asia/Seoul).

## 승인된 수정 범위

사용자가 승인한 순서에 따라 기존 13.4 구조 안에서 원인을 재현하고 수정한다.
300ms ROS/steady-time 신선도, 원 촬영 시각, 과거 TF 조회, 단일 팔 명령 소유권,
명시적 활성화와 자동 재시도 금지를 유지한다. Ch05–Ch12 및 `sources/`는 수정하지 않는다.
외부 고정 MuJoCo 플러그인 수정/재빌드와 시스템 변경은 별도 승인 대상이다.

## 진단 체크리스트

- [x] 실패 로그와 실제 관측 타임라인 대조: 9 FAIL은 9개의 독립 결함이 아니다.
- [x] 진단 회귀 RED: detector capture/latency 필드 누락 2건, observer 타임라인 누락 1건.
- [x] 위 회귀 GREEN: 3 passed. 촬영→수신 지연, 큐 대기, 변환, 인위 지연,
  추론 시간, 완료 시 ROS/steady age를 기록한다. TF 예외 문자열/시각/프레임도 보존한다.
- [x] 검증 단계 회귀 RED→GREEN: 2건. timeout에 단계 이름과 마지막 상태를 남기고,
  이미 충족된 조건은 추가 callback으로 소모하지 않는다. 합계 관련 3 passed.
- [x] 새 독립 `build13_4_debug` / `install13_4_debug`: 4 packages 빌드 완료.
- [x] MuJoCo 150ms 실제 재현과 단계별 지연 분석.
- [ ] 활성화 ACK/명령 UUID로 시험 시작 확인 개선 및 실제 안전 고장 주입 재검증.
- [ ] 의미 인식용 물체를 기하 검증용 빨간 박스와 분리.
- [ ] Gazebo 종료 대기 시 소유 프로세스 스택 수집 및 원인 기반 수정.
- [ ] 전체 소스/패키지/엔진 재검증, 변경 보고서와 커밋·push SHA 확인.

## 주의할 원인 구분

MuJoCo 지연 시험은 추론 전 만료 331회, 3/30 관측으로 실패했다. YOLO는 추론 후
만료 93회/신선한 결과 4개였다. 개별 지연 구간을 계측하기 전에는 GPU나 ROS를
단일 원인으로 단정하지 않는다. 이전 evidence는 수정/덮어쓰기하지 않는다.

Gazebo 추적은 LOST 후 안전 정지했으며 관절·속도 제한 위반은 관측되지 않았다.
MuJoCo TF/관절 고장 시험은 한 명령 실행 후 enabled 상태 메시지를 관측하지 못해
고장 주입 전에 종료했다. 이는 해당 안전 경로의 미검증이지 안전 위반의 증명이 아니다.

외부 플러그인 `c261f5552edf124d1000a23fb25b6c07cadeb807`의 카메라 렌더링은
snapshot 복사와 같은 데이터에 접근하면서 렌더 중 잠금을 유지하지 않는다.
동시 접근 가능성은 소스에서 확인했지만 이번 실패와의 인과관계는 아직 미검증이다.

## 지연 비교 실측

`debug-20261018/mujoco-delay-instrumented`는 GUI 뷰어를 유지한 실행이다.
예: capture 3.338s → RGB 수신 시 ROS age .230s, queue .0022s,
conversion .0010s, 인위 지연 .150s → 검사 시 ROS age .386s.
추론 전 만료가 발생했으며, 별도 액션 결과 확인 timeout 때문에 시험이 조기 종료됐다.

`debug-20261018/mujoco-delay-headless`는 외부 소스 수정 없이 기존 하드웨어
`headless` 옵션만 전달해 큰 시뮬레이터 뷰어를 끈 실행이다. 센서 카메라는 GLFW
렌더링을 유지했다. 30 unique captures / RMS .0025284m / 실측 수집 10.46s,
실제 q1 카메라 움직임 및 150ms 지연, 단일 TF/명령 소유권과 정상 종료 검사 PASS.
QUEUED 233개의 수신 ROS age 중앙값 .072s (최소 .048 / 최대 .188s).
이는 이 환경에서 뷰어 제거가 지연 개선에 유효하다는 실측이며 보편적 실시간 보장은 아니다.

후속 `mujoco-tracking-headless`는 target_fresh 상실 뒤 정지했고, 컨트롤러 status는
해당 UUID의 SUCCEEDED를 관측했지만 owner의 결과 응답 확인이 완료되지 않아
종료 검사 FAIL이었다. 다음 캠페인은 중단했다. 실제 프로세스 정리는 강제 종료 없이
완료됐고 residual_live_pids는 비어 있다. 이 결과를 성공으로 대체하지 않는다.

## 시험 시작/진단 개선

실제 ROS ACK 회귀는 timer를 한 번도 실행하지 않고 enable→disable을 수행했을 때
기존 구현에서 상태 메시지 0개로 RED, 수정 후 [true,false]로 GREEN이었다.
서비스 승인과 비활성화를 즉시 발행하고, session generation과 명령 UUID를 연결한다.
시험기는 주기 메시지를 기다리지 않고 새 enable_ack와 같은 세션 명령을 확인하며,
명령 이전에 세션이 정지하면 명확한 사유로 실패한다. 자동 재시도는 하지 않는다.
관련 ROS/액션/검증기/검출기 회귀 33 passed (targeted-tests.xml).

## 진단 환경 오류도 보존

초기 진단 설치본은 시스템 `/usr/bin/colcon`으로 빌드해 console script가
`/usr/bin/python3`을 사용했다. 그 결과 첫 컵 YOLO 실행은 모델 실패가 아니라
`ModuleNotFoundError: ultralytics`로 실패했다. `mujoco-yolo-cup`에 원본 실패를 남긴다.
고정 venv의 `python -m colcon`으로 다시 빌드하고 실행 파일 shebang을 확인한다.
시스템 Python은 numpy 1.26.4 / OpenCV 4.6.0, venv는 numpy 1.26.4 / OpenCV 4.10.0이다.
검증기에서 보고한 venv 버전만으로 실제 노드의 실행 환경이 같다고 추정하지 않는다.

YOLO용 후보는 이 저장소 코드로 직접 생성한 흰색 속 빈 컵/손잡이/커피/탁자이다.
빨간 박스 기하 시험과 분리하고 COCO cup(class 41)만 의미 인식 성공에 포함한다.
배경 탁자만 탐지한 결과는 성공으로 계산하지 않는다. 사진/탐지 메시지를 삽입하지 않으며,
컵은 고정된 시각 시험체로서 물리적 파지 성공의 증거가 아니다.

올바른 venv 빌드 후 `mujoco-yolo-cup-venv` 실제 실행 PASS:
평가 구간 신선한 결과 24개, 컵 탐지 24개, 유효 3D 16개, coverage 1.0.
예시 class 41 / confidence .934. 단일 clock/odom/TF와 정상 종료 검사도 PASS.
이는 한 장면의 컵 검증이지 다양한 물체/조명/보행 상황의 일반화 성능 보장이 아니다.
`gazebo-yolo-cup`도 실제 실행 PASS: 신선한 결과 107개, 컵 탐지 107개,
유효 3D 82개, coverage 1.0, 단일 소유권/정상 종료 PASS.
모든 진단 실행은 최종 소스 고정 전의 비교 자료이다. 배포 상태 판정에는 설치/소스
일치 확인과 최종 고정 소스로 다시 수행한 결과를 별도로 사용해야 한다.

추가 실행기 회귀에서 production lock을 120ms 보유했을 때 동일한 제어 timer가
실제 4-thread executor의 4개 스레드를 모두 점유하며 기다리는 것을 재현했다(RED).
제어 timer만 별도 MutuallyExclusiveCallbackGroup에 배치하여 재진입 대기를 막는다.
액션·센서 콜백은 기존 그룹에 유지한다. 이 원인이 실제 native 결과 응답 지연을
모두 설명하는지는 수정 후 실측으로 확인해야 한다.

## 고정 소스 재검증: 1833497

`1833497b032c9896f1bf7c0e798abc71a8dbaae6`에 제품/시험 코드를 고정했다.
source-tests.xml: 246 passed / 101.90s, colcon-result.log: 98 tests,
0 errors / 0 failures / 0 skipped. 설치 Python/share 소스 49파일이 작업트리와
동일하고 Git canonical blob과 일치함을 installed-source-audit.json에 기록했다.
실행 console script의 shebang도 고정 venv Python임을 확인했다.

`verified-1833497/mujoco-tracking`은 여전히 FAIL이다. 2명령 뒤 target_fresh가
만료되어 정지했다. 다만 이 실행에서는 cancel 요청→ACK(return_code 0)→실제
CANCELED terminal 결과(status 5)가 약 46ms에 확인됐고, 정상 종료/잔여 프로세스
없음 검사는 PASS였다. 타이머 수정으로 5초 연속 추적까지 해결됐다고 쓰지 않는다.

`verified-1833497/mujoco-tf`와 `mujoco-joints`는 모두 PASS다. 실제 추적 명령 및
세션 ACK 확인 후 고장 주입했고, 입력 상실 시 deadline 이후 새 명령 없음과 terminal
취소 확인, 단일 소유권/센서 계약/정상 종료를 검증했다. 이전 고장 미주입 실패와 구분한다.

추적 계산의 독립 프로파일은 기본 스레드에서 중앙값 .00450s/최대 .00950s,
BLAS/OMP 환경 스레드 제한 1에서 중앙값 .00509s/최대 .00986s였다.
이 실행에서는 BLAS 스레드 제한이 계산 속도를 개선하지 않았다. 따라서 이를
근거 없이 제품 설정으로 추가하지 않는다. threadpoolctl이 없어 실패한 첫 측정 시도는
환경 의존성이 없는 별도 Python 프로세스 환경 비교로 대체했다(패키지 설치 없음).

## 완성된 RGB-D 후보의 소실 재현

고정 커밋의 Gazebo 추적도 target_fresh로 정지했지만 정상 취소/종료는 PASS였다.
기록을 역추적하여 detection A → detection B(더 최신, depth 미도착) → RGB-D A 순서를
실제 ROS 단위 시험으로 재현했다. 기존 단일 pending detection은 B로 A를 덮어써
완성된 신선한 A를 처리하지 못했다(fusion-candidate-red.log).

후보 metadata를 기존 RGB-D 캐시와 같은 최대 10건으로 제한해 보관하고, 원래 capture/
receipt TTL 안에서 최신 **완성** 후보 하나만 worker slot에 넣도록 수정한다.
inference/fusion worker 수와 처리 슬롯 capacity 1은 바꾸지 않는다.
완성 후보/기존 추적 정책 회귀 16 passed (fusion-candidate-green.xml).

같은 수정의 경계 시험에서 처리 중인 A의 중복 detection이 두 번째 작업을 만들고
첫 정상 결과를 LOST로 바꾸는 현상도 재현했다(fusion-duplicate-red.log).
제출 시각 watermark로 처리/대기 중인 같은 촬영을 다시 제출하지 않으며,
중복으로 receipt TTL을 갱신하지 않는다. 수정 후 실제 엔진 재검증이 필요하다.

## 2026-10-19 시간 예산 진단 및 승인 범위

fusion 회귀 17건과 gate 입력 진단 2건이 통과했다. 그러나 이후 실제 추적은
Gazebo에서 legs_standing, MuJoCo에서 target_fresh로 중단되었다. 단위 시험의
통과를 연속 추적 성공으로 해석하지 않는다.

`mujoco-tracking-input-diagnostic`의 OFF 시점 ROS 시각은 13.280s,
마지막 target 촬영 시각은 12.972s였다(308ms). receipt 후 wall age는 124ms,
관절 ROS age는 6ms, STAND/ready는 정상이다. 다음 target(촬영 13.048s)은
추론 완료 ROS age 226ms였으나, fusion 결과가 이전 target 만료 뒤 도착했다.
즉 이 실행은 300ms 촬영 시각 예산을 초과하여 안전 정지한 것이며, 오래된 목표로
계속 팔을 움직이도록 TTL을 늘리는 수정은 하지 않는다.

이 실행의 cancel ACK는 수신했지만 terminal 결과는 확인하지 못했다.
프로세스 잔여 없음과 액션 취소 완료는 다른 판정이다.

사용자는 기본 10Hz를 유지한 명시적 15Hz 옵션 및 비교 시험을 승인했다.
`max_rate_hz` launch 인자와 검증 도구의 `--inference-rate-hz`로 전달하며,
유한한 (0,15] 범위만 허용한다. 촬영/receipt 안전 기준 300ms와 팔 5Hz 상한은 유지한다.
노드/launch/검증 도구 설정 누락 3건을 먼저 실패 재현했다(rate-red.log).

관리자 권한 스택 수집은 승인되지 않았다. 일반 권한 GDB attach는 소유한 시험
프로세스에서도 거부되었다(gdb-permission-probe). ptrace 정책, 외부 소스, 시스템
설정은 변경하지 않는다. Gazebo 간헐 종료 정지의 내부 스택 원인은 아직 미확정이다.

## 동일 설치본의 10/15Hz 실제 엔진 비교

아래 네 실행은 rate-build.log의 동일 설치본이며 소스 바이트는 각 source_snapshot에
보존했다. 테스트/문서 수정이 있어 HEAD만으로 clean checkpoint 실행이라 주장하지 않는다.
각 trial은 한 번이며 통계적 우열이나 재현 확률을 추정할 수 없다.

| 실행 디렉터리 | 판정 | 팔 명령 수 | 중단 조건 | 정상 종료 |
|---|---|---:|---|---|
| mujoco-tracking-10hz | FAIL | 1 | 촬영 후 ROS age 326ms | PASS |
| mujoco-tracking-15hz | FAIL | 2 | 촬영 후 ROS age 302ms | PASS |
| gazebo-tracking-10hz | FAIL | 3 | target receipt wall age 약303ms (ROS age274ms) | PASS |
| gazebo-tracking-15hz | FAIL | 2 | invalid/lost target | FAIL |

15Hz MuJoCo의 마지막 신선한 촬영은 18.376s, 다음 탐지 입력 촬영은 18.594s로
218ms 차이다. 전자는 detector 수신 시 이미 134ms old였으며 추론 .02075s,
queue .00378s였다. 다음 입력이 수신되는 때 기존 목표는 302ms가 되어 정지했다.
이는 해당 구간의 카메라→탐지 입력 간격/수신 지연 증거이며, 렌더러·DDS·OS 스케줄러
중 어느 내부 구성요소가 원인인지까지 확정하는 스택 증거는 아니다.

Gazebo 15Hz에서는 stop ACK 후 native 종료 대기가 실패했다. 일반 권한 스택 수집은
소유권 확인 뒤 시도했지만 ptrace가 거부했다(`shutdown-stack-2062.txt`,
`shutdown-stack-2068.txt`). launcher가 SIGINT 5초 뒤 SIGTERM을 보냈고 native exit
code -15였다. 잔여 PID는 없지만 정상 종료 PASS로 취급하지 않는다. 관리자 권한은
사용하지 않았다. 다른 세 실행의 정상 종료로 이 실패를 덮지 않는다.

단위 회귀로 확인한 후보 덮어쓰기/중복 작업과 timer 재진입 결함은 각각 수정했다.
하지만 이 조치와 15Hz 선택만으로 연속 추적이 해결되지 않았다. 같은 방향의 임의 추가
수정을 중지하고, 다음 단계는 촬영→수신→추론→fusion→제어의 종단 시간 예산 및
시뮬레이터 정지 경로를 구조 단위로 검토하는 것이다. 300ms/5Hz를 완화하거나 자동
재활성화로 5초를 이어 붙이지 않는다. 외부 플러그인 수정·새 센서 프로파일은 별도
설계 결정이 필요하며 이번 비교에 포함되지 않는다. 13.5는 재개하지 않았다.

## 일반 권한 부모 디버거: 추가 진단

사용자가 후속 구조 검토를 승인했다. `parent_debugger_13_4.py`는 GDB가 직접 생성한
자식만 조사하는 진단 전용 prefix다. EUID0 실행을 거부하고 attach/sudo/sysctl/GUI/
autoload/debuginfod를 사용하지 않는다. 실제 자식 exit7 전달과 스택 수집 후 SIGINT
전달/exit0 회귀2건이 통과했다(parent-debugger-green-v2.xml). 첫 실패 로그도 남겼다.

첫 native 실행 `gazebo-parent-debugger`는 shell을 한 겹 더 만들었고 원래 launcher의
SIGINT가 wrapper까지 직접 전달되지 않았다. 8목표 뒤 입력 상실로 중단했고 종료도
미달이다. 디버깅 도구 자체의 신호 전달 문제를 native 교착의 증거로 사용하지 않는다.

공식 launch의 ExecuteLocal은 직접 생성한 PID에 send_signal을 호출하며,
gz_sim.launch는 shell=True로 Ruby 명령을 실행한다. executable basename은
`gz sim`이므로 진단 prefix 필터도 그 이름으로 한정한다. `exec`를 앞에 붙인
`gazebo-parent-debugger-exec`에서는 실제 MI interrupt→전체 thread backtrace→
SIGINT 전달→native exit0을 확인했다. 관리자 권한은 사용하지 않았다.

중단 시 main은 `Barrier::Wait → SimulationRunner::UpdateSystems → Step/Run`,
sensor thread는 `SensorsPrivate::RunOnce → RenderThread`의 condition wait였다.
이는 그 순간의 스택이며 반복 샘플/정지 기한을 입증한 영구 교착 스택이 아니다.
디버거 inferior는 별도 PGID가 되어 기존 native PID 대기와 다른 경로를 사용하므로
이 실행의 clean_shutdown=true도 제품 인수 PASS로 승격하지 않는다. 이 실행도6명령
뒤 계산 중 입력 만료로 추적 FAIL이었다. 실제 PID의 추가 잔여 검사는 별도로 수행한다.

실제 Gazebo ogre2 로그의 GL_RENDERER는 `llvmpipe (LLVM 20.1.2, 256 bits)`다.
별도 MuJoCo GLContext 조회도 같은 renderer를 반환했다. 현재 두 엔진은 CPU
소프트웨어 렌더링을 사용하며 WSL 가용 CPU는8, cgroup cpu.max는 max100000이었다.
렌더와 ROS가 공유 CPU에서 경합할 가능성을 다음 가설로 삼되, 이것만으로 모든
실패 원인이라고 확정하지 않는다. 이전 BLAS 스레드 제한 프로파일과는 다른 경계다.
프로세스 한정 LP_NUM_THREADS=2와 exec 전달을 변수별 비교하며, 제품 기본값과
해상도/안전 기한/시스템 환경은 변경하지 않는다.

`2c9f2212fac4ade3fd3813fb3a06c542b9972be4` 제품 체크포인트의 전체 소스 시험은
252 passed /95.24s, 설치 패키지 시험101 tests /0 errors /0 failures /0 skipped였다.
설치 Python/launch29파일과 venv shebang 일치는 comparison-installed-audit.log에 있다.
이후 추가한 부모 디버거 진단 도구는 별도 회귀와 전체 재시험 대상이다.

## 렌더 자원·신호 경계 비교 결과

`resource-comparison-console.log`에 각 프로세스의 LP_NUM_THREADS와 실제 launch
명령을 기록했다. 기존 환경과 제품 설정은 바꾸지 않았다.

| 새 실행 | 결과 | 관찰 |
|---|---|---|
| gazebo-exec-native | FAIL |11명령 뒤 계산 중 입력 만료. Gazebo 자체는 정상 종료했으나 clock parameter_bridge가 -11로 종료하여 clean_shutdown FAIL |
| gazebo-exec-lp2 | PASS |15Hz,5.2008초,15명령,픽셀 오차 중앙값6.0208→0px,모든 필수 검사/정상 종료 PASS |
| mujoco-lp2 | FAIL |15Hz,1명령 뒤 invalid/lost target. 정상 종료 PASS. 렌더 스레드 제한만으로 해결되지 않음 |

Gazebo PASS의 최소 명령 간격 .28544s, 실측 최대 q1/q5 속도 .05269rad/s,
최대 각도 .02071rad였다. 이는 기립·소각도·단일 장면의 **한 번의** 실제 엔진 실행이다.
PPO 이동 추적이나 재현 확률/일반화 보장이 아니며, 기본10Hz 결과를 대체하지 않는다.
GDB 없이 exec만 적용한 실행에서도 bridge 종료 crash가 남아 exec를 전체 종료 문제의
충분한 해결책으로 제품에 반영하지 않았다. LP_NUM_THREADS=2도 기본값으로 넣지 않았다.

부모 디버거를 포함한 최종 소스 회귀는254 passed /92.68s다
(`post-diagnostic-source-tests.xml`). 패키지 코드는2c9f221 이후 바뀌지 않았고
설치 패키지 시험101건은 그대로 유효하다. `graphics-and-process-audit.log`의 GL 조회는
EUID1000이며 별도 PGID의 과거 진단 native/GDB PID4개도 모두 존재하지 않았다.

사용자가 외부 원본을 유지하는 Ch13 전용 카메라 복사본의 **설계서 작성**을 승인했다.
`docs/specs/2026-10-19-camera-snapshot-ownership-design.md`에 두 mjData 버퍼의
독점 소유권·시각/카메라 목록 원자적 전달·종료·라이선스·실제 엔진 인수 기준을 명시했다.
새 플러그인 복사/구현/빌드와 launch 기본값 변경은 하지 않았다. 설계서 검토 후 구현
계획과 그 검토를 거쳐 진행한다. 외부 원본은 여전히 고정 커밋의 clean 작업트리다.

진단 도구 코드 체크포인트는 `caac5299765c72db7a44249f418f0b978d976fb0`이다.
artifact-integrity-audit.log는 각 result가 기록한180개 artifact의 크기/SHA-256 일치를
확인했다. 이는 무결성 검사이며 native FAIL을 PASS로 바꾸는 검사가 아니다.
문서/evidence 커밋과 원격 SHA는 자기 참조를 피하기 위해 별도로 확인한다.
