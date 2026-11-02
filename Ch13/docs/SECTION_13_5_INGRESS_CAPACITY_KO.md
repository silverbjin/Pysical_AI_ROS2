# Task8 수신 실행 비용 판별

## 최신 실제 결과와 다음 판별 경계

후속 순수 산술 후보는 독립 full-link FK100자세를 포함한10시험11.20초, G2 한정 구성/현재값·센서 안전·ACK 기한·기존 교정 등을 포함한56시험72.01초, sensors11개 CTest suite6.73초와8패키지 설치 감사를 통과했다. 수치 모듈/구성 연결의 실패 회귀 RED14.74/11.38초를 각각 먼저 보존했다. `native-mass-contention-replay-34896d4c`의 NumPy/native/native/NumPy 평균 CPU1.375/1.008/0.873/1.616ms는 약37% 감소이며, 원래 재생 timer 간격은 같았다. 설계·범위·원래 안전 계약은 `SECTION_13_5_CRAWL_NAVIGATION_DESIGN_KO.md`의 순수 산술 경계 절에 있다. 실제 엔진 인수는 새 고정 소스에서만 판단한다.

고정135소스 manifest `4cd75cb87689c59e5ff159eb2ddd88c420ad798df96b603670aa5025a66c82c9`에서 직접 직렬 소유자를 적용한 MuJoCo G1 `a104a38d`는24/24 PASS다. 같은 소스의 G2 `a9e062c5`는 첫 전진 SHIFT에서 FAIL했다. 원래 ROS41.120→44.748초,3.628초 동안 곡선2.625초에 필요한 참조는2.159142752초만 진행했고100ms 안정화는 시작하지 못했다.58회 발행/133회 판단이며, 발행 간격은 ROS 중앙값62ms/최대136ms다. 다른 물리·센서 검사가 통과했다는 사실을 이동 성공으로 바꾸지 않는다. G2 액션 terminal·runtime/engine 정상 종료·reap·잔여 없음, 부모 `38ce7f26`의 두 서비스 복원·두 foreground 정상 종료는 모두 확인했다. 연속3회 인수는 미달이다.

`ack-owner-readiness-a56d9743/result.json`은 원본 controller SHA `156221886614cde90741463088493e41280be1794a2095232385fc5d781bc7ef`의 보존된 마지막16개 ACK를 원래 판단과 연결한다. 유효 ACK가 도착하고 촬영 시각이 현재 원본 ROS 시각 이내가 된 첫 판단에서 모두 허용됐다. ACK가 먼저 도착해도 미래 촬영인 경우의 대기는 정당하다. trace 없는 ingress 알림의 누락을 단정하지 않으며, ACK 거부 조건이나 미래 시각 허용을 바꾸는 수정의 근거로 삼지 않는다. 발행→첫 수신 평균28.89ms와 수신→확인 평균13.43ms, 발행 전 계산 비용을 합친 전체 경계를 조사한다.

단독 계산에서 작은 NumPy 연산의 비용이 live보다 낮았다. Python 스칼라 시제품 두 판별(`scalar-mass-prototype-ac8b3972`, `fa545ffd`)은100상태 수치 오차≤1.39e-17m였으나 단독 비용 개선은 없었다. 이를 production에 적용하지 않았다. 실제 수신 부하4.2209초/1,353메시지를 원본 CDR에서 추출한 `contention-window-4948804b`로 엔진 없는 A/B를 이어간다. 이 재생은 현재 DDS 재전송이며 원래 헤더를 유지하지만 엔진 인수는 아니다.

G2의 참조 상한은 원래40ms다. 파생 분석 `clock-model-boundaries-00202b96`은 nominal20ms를 잘못 적용한 proxy이므로 사용하지 않는다. `ec8c3759`가 max_step40ms를 읽는 정정본이다. 원본 실패 결과는 수정하지 않았다. 정확한 원래 reference state를 발행 간격 proxy로 대체하지 않는다.

## 최신 판별: G1의 직렬 모델 작업자 큐 비교

G1 실행기 선택 RED14.59초 → 관련23회귀36.52초 PASS → Gazebo/native 유지·입력 분리·모델 수치 동등·교정·fault stop을 포함한51회귀81.39초 PASS다. native 설치17.3초와8패키지 일치 감사도 통과했다. 실제073 고정본의 소스135개와 현재 바이트를 대조한 변경은 `clock_execution.py`, `crawl_controller.py`, runner의 실행 방식 기록까지3파일이며, `g1-owner-candidate-062bc55d-80e4-4447-9e10-3516b7e70764`에 diff를 남겼다. 새 실제 인수는 아직 실행 전이다.

고정135소스 manifest `56ce26df067546208b960077358369ad3bd1f293096d269e97b37ba86d4bc1e2`의 실제 MuJoCo G1 `073ad2cb`가 교정 SHIFT에서 실패했다. 부모 `0af91400`은 서비스 복원·두 foreground 정상 종료·잔여 없음이 true다. 액션 terminal은 확인했으나 실측 STOPPED 대기 실패로 `normal_runtime_exit`는 false다. 엔진 process exit/reap은 확인했다. G2는 실행하지 않았고 연속 성공 계수에 포함하지 않는다. 원본은 비교용 pin으로 보존한다.

원래 ROS26.622→29.418초, 2.796초 동안 참조는1.7372042초 진행했다. 필요한 곡선1.744655041887119초에 약7.45ms 못 미쳤고100ms 안정화는 시작하지 못했다. 명령107회의 간격은 중앙값22ms/p95 56ms/최대100ms(ROS), wall 중앙값22.31ms/최대89.04ms다. G1의 원래20ms 개별 참조 상한을 유지한다. 발행 간격으로 계산한 상한 손실535.75ms는 proxy이며 실제 모델의 전체 미소비1.0588초와 같은 값이라고 주장하지 않는다.

새 C++ 원본 수신/발행 계측에서 trace 비용은 평균0.0762ms, source→RMW 중앙값0.3766ms, RMW→callback 중앙값0.1005ms다. trace 뒤 타이머 재설정 결함은 단위 재현으로 교정했지만, 그 비용만으로 이번1초 수준의 참조 손실을 설명할 수 없다. 원본 기록은 `clock-model-boundaries-1eb83420-fd21-45ab-a439-93b8707fb50e/result.json`이다. G1의 결정 비용 trace는 기존에 비활성이라0행이며, 이를 callback 부재로 해석하지 않는다.

다음 가설은 G1의 이미 직렬인 모델 callback을2-worker pool로 전달하는 추가 경계가 제어 지연과 짧은 연속 실행을 키운다는 것이다. 설치된 rclpy7.1.12의 [고정 원본](https://github.com/ros2/rclpy/blob/bd637294dd02b1c128422395c059fa06df8387a3/rclpy/rclpy/executors.py#L905)은 SingleThreaded의 직접 handler 실행과 MultiThreaded의 ThreadPoolExecutor 제출을 구분한다. 실제 지연 감소는 새 엔진으로 판별해야 하며 이 소스 차이만으로 원인을 확정하지 않는다.

비교 구현은 MuJoCo의 명시적 relay100 검증에만 기존 G2의 직접 직렬 모델 실행을 G1까지 확장한다. G1의 별도 wait-set ingress·원본 TimeSource·wall50Hz·20ms 참조 상한과 G2의 기존 cadence/ACK 규칙은 유지한다. G1에도 기존 숫자 전용512행 wall/thread-CPU trace를 켠다. Gazebo의2-worker와 native 기본 실행, 모터 적용·보간·게인·물리·기한·실측 인수 조건은 바꾸지 않는다. 실패 회귀에서 G1이 실제 DrainingExecutor를 선택하는 것을 먼저 재현했다. 새 실제 실행 전까지 해결로 선언하지 않는다.

최신 고정 소스133개 manifest `88e556faec7da302ad26f89a83d184ff7920017fb457c698573bd5037b487ba6`에서 MuJoCo G1 `eed57b87`은24검사 전체 PASS, G2 `6a7d1a30`은 좌회전 SHIFT timeout으로 전체 FAIL이다. 실패 실행을 연속 성공에서 제외하거나 재시도하지 않는다. 양 실행의 액션 terminal·runtime/engine 정상 종료·reap·잔여 없음이 확인됐고, 부모 `clock-single-owner-d1b4bdb3`의 두 서비스 복원 및 두 foreground 종료도 true다. G2 ZIP SHA는 `3798ecb9f519bb72fc7620a8524d4b63df72ae8fe23efb8109b3eb1e14877e2a`다.

## 판별 근거

실패 단계는 원본 ROS986.115999990→989.745999990초(3.630초), 원래 곡선2.625초와 추가1초 제한이다. 참조 시간은2.685470293초까지 진행했지만 안정화는989.691999990초에 시작해54ms만 확보했다. 요구100ms에 미달한다.100회 발행의 간격 중앙값24ms/p95 84ms/최대122ms다. 원본40ms 참조 상한과 양 시계의 개별 간격 제한을 넘긴 시간은 다음 목표로 임의 이월하지 않는다. 이를 누적 시계 예산으로 바꾸면 개별 구간의 속도 계약을 바꿀 수 있으므로 이번 수정 대상으로 삼지 않는다.

같은 모델 소유 스레드의100회 발행 판단은 평균CPU6.252ms/wall8.803ms다. 별도 수신을 포함한 crawl 프로세스는 해당 구간 주변 약0.829 CPU 코어를 소비했다. 관측된 비용만으로 수신 실행기를 단독 원인으로 확정하지 않는다. 먼저 엔진 없는 실제 DDS A/B로 수신 실행 비용을 판별한다.

## 참고 사례와 실험

이미 일반 navigation 노드에 사용한 설치본 rclpy7.1.12 EventsExecutor는 수신 전용 직렬 실행기에도 적용 가능한 후보다. [원저자의 발표](https://discourse.openrobotics.org/t/faster-rclpy-executor-now-in-rolling/42852)는 C++ 이벤트 루프의 비용 개선과 모든 콜백을 직렬로 처리하는 제약을 설명한다. 검토 태그7.1.12/commit `bd637294dd02b1c128422395c059fa06df8387a3`, 실제 설치 wrapper/extension SHA를 실험마다 기록한다. 외부 소스 수정·복사는 없다.

1. 실제 DDS8토픽×100Hz, wait-set/events/events/wait-set 순서로 동일 부하를 비교한다. 별도 receiver 스레드 CPU, 원본 발행→콜백 지연, 수신 수, MessageInfo 및 정상 join을 기록한다. UInt64 부하는 dispatch 비용만 분리하며 실제 센서 파싱·물리 성공을 대신하지 않는다.
2. 개선 근거가 있으면 MuJoCo G2 relay100 수신 전용 실행기에만 적용한다. 모델 소유자·기본/G1/Gazebo 실행기는 유지한다. 활성 스레드에서 backend 교체·예외 후 재시작은 금지한다.
3. 실제 DDS의 원본 시각·메타데이터·직렬 실행·오류 영구 보존·정상 join을 실패 회귀부터 검증한다. 기존 제어/ACK/시계 정지·롤백/소유권 시험을 통과시킨다.
4. 설치 감사 후 새 G1/G2 한 쌍으로 실제 효과를 확인한다. 모든 원래 물리·시간·속도·그리퍼 기준을 유지하고 첫 FAIL에서 중단한다. 이후 고정본 연속 성공과 후속 Tasks9–14를 진행한다.

모터 보간·게인·물리·촬영 헤더·센서 나이·곡선 시간 상한·phase 마감은 변경하지 않는다. 이벤트 실행기의 callback group 무시는 이미 직렬인 수신 전용 노드에만 허용한다. 병렬 모델/액션 소유권에 확대하지 않는다.

## 비용 비교와 구현 회귀

`ingress-backend-benchmark-5afda1c2-e3ce-4c18-8563-cc18d12e2aab`의4회 각각2,400/2,400수신·원본 MessageInfo·정상 join을 확인했다. wait-set 수신 CPU284.2/425.0ms에 비해 events113.4/117.9ms였고, callback 지연 p95는0.866/1.386ms와0.674/0.705ms다. 실제 G2의 성공이나 모델 전체 지연 감소로 환산하지 않는다. 초기 도구는 환경 전달 실패와 종료된 스레드 CPU 시계 조회 실패가 있었고, 이때 실제 receiver 예외는 저장하지 않아 원인을 소급 확정하지 않는다. 최종 도구는 두 MessageInfo 표기를 읽고 오류·진행 파일을 즉시 남긴다.

명시적 MuJoCo G2가 아직 wait-set을 선택하는 실패 회귀 RED13.26초를 먼저 확인한 뒤, 시작 전 backend 선택과 MessageInfo 호환을 구현했다. 관련 실제 DDS/시계/ACK/소유권54시험40.74초 PASS다. backend는 시작 후/실패 후 교체할 수 없고 예외는 sticky이며, 종료 시 원래 receiver를 join한 뒤 ROS 자원을 닫는다. 실제 PID/thread·설치 entrypoint와 함께 event wrapper/extension SHA·선택된 backend도 확인한다. 후속 설치 감사와 실제 엔진 결과는 별도 기록한다.

추가 안전/시간/의존성·backend 오인 거부 회귀105시험53.36초 PASS. 실제 엔진 비교는 소스·설치본을 새로 고정한 뒤 수행한다. 정상 종료가 확인되기 전에는 다음 엔진을 시작하지 않는다.

실제 후속 G1 b055c8a9는 measured_startup 뒤 runner의 미정의 engine/gate 변수명 오류로 FAIL했다. G1 모델 자체는 STAND였지만 나머지 물리 검사를 수행하지 못했으므로 전체 실패를 보존한다. runtime/engine 정상 종료·reap·잔여 없음·부모0b846674 서비스/foreground 복원은 모두true, G2는0회다. 실제 호출부를 args.engine/is_g2로 고쳤고, 변경된 네 실행 경로의 미정의 이름을 검사하는 정적 회귀 RED11.48초→관련56시험21.36초 PASS를 기록했다. 기존54+105회귀 뒤 바뀐 내용은 호출부와 테스트 의존성뿐이다. ZIP11283360bytes/SHA af01caf5fd1fe2d078dd2cf45e5959ea605826b6ad877b549349f39dfaa01187, source133/fd6bc748을 보존한다.

## 실제 후보 결과와 채택하지 않은 가설

수신 실행기 후보의 새 G1 `34cf0c81`은24/24 PASS, 같은133소스 manifest `34a8e9412255b67ea601eec208a9d0ddb2b497e15de03e0573ba808c38618297`의 G2 `22afb6c3`은 전진 SHIFT759.030→762.666초(3.636초)에서 FAIL했다. 참조는2.623844197초로2.625초에도 미달했고 안정화는 시작하지 못했다.74회 발행의 평균 간격49.452ms·최대112ms,152회 판단이었다. 실제 backend `owned_serial_events`가 확인됐으므로 수신 경로 변경만으로 해결됐다는 가설은 기각한다. 액션 terminal/runtime/engine 정상 종료·reap·journal join·잔여 없음·부모7d4c109d 서비스/foreground 복원은 모두true다. ZIP516,473,970bytes/SHA `aa5c1ba6698838effd427d07b799d0316ac5acb6432d1f3e52ec514d288569f6`,8개 분할과 원본을 보존한다.

`math-thread-benchmark-4355108f`는 동일 모델·원래 관절/몸체/제한값의 계산을 별도4프로세스로 비교했다. BLAS1은 큰 차이를 만들지 않았고 출력은 동일해 적용하지 않았다. 계산 단독 약0.8ms CPU와 live의 큰 비용 차이를 물리 성공으로 환산하지 않는다. 서비스 복원 뒤 kernel 시간 보정이 진행될 수 있어 이 비교의 wall/CPU 비율로 runtime 시계 건전성을 주장하지 않는다.

`contention-window-81ee368b`는 원본 CDR SHA `9c392765bbe493b96657298965ee2f8aa482f3f9f9e83ef6a4f98c1cd13fec11`을 CRC/순번/종료 footer까지 검사해4.236초/1,502메시지를 추출했다. 원래 CDR header를 유지했고, clock만 실제 기록의 원래 capture_ns로 재구성했다. `contention-replay-eb94e6a7`은 별도 DDS 송신자와 비활성 실제 CrawlController의 동일 상태 계산을 비교했다. 전환 간격5/1/1/5ms 모두187callback·최대 간격 약76.5ms였다.1ms 조절만으로 긴 간격이 해소되지 않아 적용하지 않았다. 활성 guard/명령 발행·엔진 부하는 빠져 있으므로 모든 GIL 영향을 배제하는 증거는 아니다. 모터 발행0·송신 exit0·receiver join을 확인했다. 도구 초기 QoS API/대기 계산 오류는 별도 실패 로그로 보존한다.

## 시계 중계 경계의 최소 수정

`relay-window-7de78731`의 실패 단계에는242회 중계 발행이 있었고 간격 중앙11.845ms·평균15.039ms·최대59.443ms였다. `independent-clock-witness-905fa603`에서25ms 초과19간격 중12간격에 독립 native 관측기의 원본 시계 진행이 존재했다. 이는 엔진 전체 정지 가설을 지지하지 않는다. 중계 input의 정확한 callback 시각은 기존 기록에 없어 middleware와 executor 지연을 아직 분리할 수 없다.

확인된 코드 결함은 다음10ms 기한을 발행과 JSON/파일 기록이 모두 끝난 뒤 재설정하는 순서였다. 실제 ROS의 제어된5ms 기록 부하 시험은1.5초99회로 실패했고(기준120회 이상), `timer.reset()`을 실제 발행 직후·기록 전에 옮긴 최소 수정은 통과했다. 이것이 실제 엔진의 기록 시간이5ms였다는 뜻은 아니다. 원래 header·publisher·100Hz 상한·기존10ms watchdog·200ms stall·영구 fault를 유지한다. source-event 전달로 구조를 확장하는 대신 이 작은 순서 교정을 먼저 검증한다.

같은 파일의 종료 행에 입력4096개·발행/기록 span2048개의 유계 메모리 기록을 추가했다. 입력의 첫 MONOTONIC/SYSTEM 및 RMW source/receipt, RAW bracket을 별도로 저장하며 서로 변환하지 않는다. 입력 callback은 파일을 쓰지 않고, gate를 닫은 뒤 기록한다. 향후 실패에서는 원본 발행→middleware→callback→중계 발행을 실제 값으로 구분할 수 있다. 시계 최신성의 기준은 더 늦은 처리 시각으로 갱신하지 않는다.

참고한 [topic_tools Jazzy1.3.4의 rate 제한 구현](https://github.com/ros-tooling/topic_tools/blob/462af78b06ad8baafc27ce09cb3dfee96421cfab/topic_tools/src/throttle_node.cpp)은 Apache-2.0, blob `03252f6b6a03b8c430ea1e19a347b0415bab76fd`다. 코드 복사는 없고, Ch13은 이 구현의 시간 역행 시 재시작 동작을 채택하지 않는다. 자체 baseline의 SHA는 evidence의 `relay-period-baseline.json`에 있다. 원본 수신 경계 회귀도 먼저 FAIL한 뒤 구현했다. 관련 ROS7시험4.610초 PASS이며 추가 실제 발행 간격·전체 센서 회귀와 새 엔진 검증은 별도다.
