# EGL camera ownership / latency tracing execution

Run 424240ff-0bfe-4a4b-92d4-93f6a78d49b8; start HEAD 0ff4063f75e2f551aee09349e7fe9454792beea2.
Approved plan: docs/plans/2026-10-20-egl-camera-latency-plan.md.
Native, ordinary EUID1000, no external source/driver/TTL/arm-rate changes.
Execution in progress. No new implementation or native acceptance PASS implied.

## Task1: EGL 소유권

Checkpoint `194b7302afbf8dbcde38d0a6b110353c16395220`.
`egl-contract-red.log/xml`: 원래 구현의 실제 EGL 영상 수신 후 GLFW 호출1,
eglTerminate1로 두 행동 시험 실패. `baseline-build.log`, `egl-final-build.log`의
일시적 시험 작성/함수 서명 컴파일 오류는 행동 RED와 구분한다.
`egl-clean-build.log`, `egl-clean-ctest.log`, `task1-done.log`: 소스 동결 후 실제 EGL
context/실패 경계/peer 보호/worker TID/영상 깊이·flip·헤더 회귀 통과.
`task1-pytest.log/xml`: 285 PASS. `task1-result.log`: 136 tests, errors/failures/skips0.
`task1-installed.json`: 다섯 패키지 소스·설치·실행기·camera/mailbox library 일치 감사.
`task1-results/index.json`: raw JUnit11개 원래 경로·크기·SHA-256와 복사본.
실제 renderer는 llvmpipe/Mesa 소프트웨어 EGL이며 GPU 가속의 증거가 아니다.

## Task2: 촬영 lease 계측

Checkpoint `8788fb6d475e868a743629fe3eb75cff6f7dfdc5`.

`trace-integration-red.log/xml`: 기존 영상은 나오지만 trace 없음 / 잘못된 UUID 허용의
두 행동 실패. `trace-api-red-build.log`: 새 timing/trace API 부재의 별도 컴파일 RED.
`trace-green-ctest.log`: 영상·mailbox·EGL·loader는 통과, QoS graph depth0 시험만 실패.
설치된 Jazzy `rmw_fastrtps_shared_cpp/qos.hpp`129는 발견된 history/depth를 설정하지
않는다고 명시한다. [상위 이슈684](https://github.com/ros2/rmw_fastrtps/issues/684)도
같은 조회 한계를 설명한다. 제품 depth32를 낮추지 않고 실제 `rcl_publish` 경계에서
`rcl_publisher_get_actual_qos`를 관측하도록 시험을 수정했다.
`trace-final-build.log`, `trace-final-ctest.log`: 5개 CTest 등록 모두 PASS/10.09s.
실제 DDS 호출을 전달하며 BEST_EFFORT/VOLATILE/KEEP_LAST depth32를 직접 확인했다.
실제 readback barrier 안에서 submit2가 진행되어도 취득한 stamp1와 13개 시각이 일치한다.
UTF-8 JSON escaping/4096byte/20000attempt 상한, 오류 집계, trace 출력 거부 시
320×240 RGB-D/Info 원 헤더 보존을 검사했다. trace 성공은 DDS 전달 완료의 증거가 아니다.
`task2-pytest.log/xml`:285 PASS/117.88s. `task2-result.log`:147 tests, errors/failures/skips0.
`task2-installed.json`: 다섯 패키지 설치 감사, camera SHA
`a3c10806ee41a857ac9327aa23b4c6aaa58675b5aab9ace7e013d64bc939b6e1`, mailbox SHA
`6a2ff6b3edf96e64b7fe079967b7b3824edce12b674d9548a0b893b96987b5a8`.
`task2-results/index.json`: raw JUnit12개 복사본과 SHA. `task2-done.log`: CTest5/5 PASS/11.94s.

## Task3: Python 발생 시각

Checkpoint `2ff7d560ba16e7208202ef96c9a8b8b846840c0c`.

`python-hook-red.log/xml`: 기존 실제 탐지는 유지되지만 trace 없음, 제어 hook 부재의3실패.
`fusion-hook-red.log/xml`: 기존 실제 PointStamped는 유지되지만 trace 없음의1실패.
`python-api-red.log/xml`: trace.py 부재의 별도 API RED.
`python-first-green.log/xml`:49 PASS/22.44s. 실제 RGB header·fusion 수신 순서·제어 잠금
밖 발행·transport 실패가 중복 목표의 TTL/활성 상태를 바꾸지 않음을 검사했다.
이 단위는 제어 정책·현재/과거 TF 선택·300ms 만료·명령 소유권을 변경하지 않는다.
제어 trace의 gate_lost는 원래 판단/취소 경로 직후 관측한 경계이며 조건 변화의 외부 실제
발생 순간 자체가 아니다. 같은 producer의 관측 시각을 새로운 촬영 시각으로 바꾸지 않는다.
`task3-pytest.log/xml`:318 PASS/122.84s; `task3-result.log`:180 tests/errors/failures/skips0.
`task3-installed.json`: 다섯 패키지 일치 감사. `task3-done.log/xml`:116 PASS/43.41s.
`task3-results/index.json`: raw JUnit12개 및 SHA.

## Task4: 연결·수집·분석

`trace-routing-red.log/xml`, `trace-analyzer-api-red.log/xml`: 전달 및 새 분석 API 미구현.
`gate-age-red.log/xml`: 실제310ms 계산 뒤 안전 정지했지만 목표 나이를6.15ms로
보고하는 계측 결함. 정지 경계의 ROS now를 lock 안에서 함께 복사해 수정했다.
`trace-shutdown-red.log/xml`: context 종료 뒤 로그 발행 오류. node 파괴 전에 요약을
기록하도록 수정했다. `gate-shutdown-source-green.log/xml`:2 PASS/8.55s.
`callback-loss-isolated-red.log/xml`: 타이머 없이 즉시 callback 정지가 계측되지 않는 결함.
`callback-loss-source-green.log/xml`:1 PASS/3.55s, 마지막 유효 촬영·수신 시각을 유지한다.
`callback-loss-red.log/xml`는 최초 약한 시험이 PASS한 기록이며 실제 RED로 세지 않는다.

`analyzer-contract-red.log/xml`:7 PASS/6 FAIL. 없는 stage를 defaultdict 조회로 생성해
IndexError가 난 원인을 수정했다. C++ 교차 시험의 출력 marker 부재는 별도 항목이다.
`event-conflict-red.log/xml`: 상충된 동일 event ID에서 첫 기록을 선택하는 결함을 재현해
해당 촬영 전체를 격리했다. `no-source-loss-red.log/xml`: 원 목표 없는 정지 누락을
수정하며 ROS/receipt age는 null로 보존한다.
`trace-origin-api-red.log/xml`와 `trace-origin-behavior-red.log/xml`: 기존 EGL/library
존재 검사만으로 다른 PID999의 기록도 인정하는 문제를 분리 재현했다.
`trace-origin-green.log/xml`:1 PASS/2.48s; 실제 owned native PID·boot·clock에 연결한다.

`trace-audit-build.log`, `trace-audit-ctest.log`:5패키지 build 및 실제 EGL5/5 PASS/9.63s.
`task4-pytest.log/xml`:341 PASS/145.57s. 첫 패키지 회귀에서는 새 MuJoCo launch의
flake8 지적5건이 발생했으며 wrapper까지 포함해6 failures로 집계됐다.
`task4-first-results/index.json`에 원본12개를 보존했다.
`description-lint-final.log/xml`: 수정 뒤4파일/문제0. `task4-final-*`는 추가 PID 연결과
lint 수정 후 새 전체 검증이며 결과를 확인하기 전 성공으로 간주하지 않는다.

실험적 `python-malformed-*.log`는 모두 허용 byte 범위의 잘못된 JSON을 ValueError로
거부한 PASS이며, 파일명에 red가 있어도 실제 결함/수정으로 세지 않는다.
`analyzer-first-green.log/xml`은 잘못된 선택식으로0건 실행한 오류이며 GREEN이 아니다.

Checkpoint `09b057465da50ffcf892c30e2e8f7e9f516ab953`.
`trace-causal-red.log/xml`: native 미완료 publication 및 TF/입력 수신 이전 publication을
종단 지연으로 연결하는3개 실패를 재현했다. `trace-causal-green.log/xml`:3 PASS.
`task4-stable-pytest.log/xml`:345 PASS/130.79s; `task4-stable-result.log`:182 tests,
errors/failures/skips0. `task4-stable-installed.json`: 다섯 패키지·두 library 해시 일치.
`task4-stable-results/index.json`: 원본 JUnit12개 및 SHA.
`task4-done.log/xml`: 최종 계약88 PASS/91.35s. 소스 테스트의 통과는 엔진 과제 성공이 아니다.

## Task5: 실제 엔진 matrix

고정 소스 `09b057465da50ffcf892c30e2e8f7e9f516ab953`와 새 설치본을 사용한다.
`task5-build.log`:5패키지/45.9s, `task5-pytest.log/xml`:345 PASS/148.40s,
`task5-result.log`:182 tests/errors/failures/skips0, `task5-installed.json`:설치 일치.
`native-environment.json`: 실제 EUID1000·외부 clean 고정 커밋·가중치 SHA·버전·boot 기록.
관리자 권한·외부 원본·스레드 설정·해상도·기한·명령 상한 변경은 없다.

`matrix-progress.jsonl`은 완료된 개별 실행의 UUID/명령/제품 판정과 잔여 검사를 보존한다.
static-off/on/delay-on은 각각 고유30개·RMS3.1311/3.1314/2.7048mm로 PASS다.
이 한 쌍의 OFF/ON 비교를 무부하나 보편적인 성능 보장으로 해석하지 않는다.
10Hz3회·15Hz3회 추적은 모두 FAIL이며, m15c는 취소 미확인/정상 종료 FAIL도 남았다.
원 목표를 잃은 뒤 capture0으로 가짜 age를 계산하지 않고 trace의 마지막 유효 촬영을 보존했다.
MuJoCo 컵 YOLO·images/tf/joints 손실, Gazebo 컵 YOLO·images 손실은 PASS다.
Gazebo tf 손실은 대응 검사 통과/정상 종료 FAIL(SIGTERM 필요)이다.
Gazebo joints/static/delay는 PASS, tracking은 지속 추적/정상 종료 FAIL이다.
실제13.4 총20회는12 PASS/8 FAIL이다. `legacy-progress.jsonl`의13.3 회귀는
MuJoCo PASS/Gazebo FAIL(runtime mission_commander와 native engine에 SIGTERM 필요)이다.
22회 모두 잔여 엔진 없음이 확인됐지만 이는 정상 종료나 controller hold의 증명이 아니다.
`task5-audit.log`: 고정 소스/20개 고유 UUID/legacy2회/234개 artifact 해시의 수행 감사 PASS.
이 감사는 제품 인수 FAIL을 PASS로 바꾸지 않는다.
`native-analysis.json/log`는 완료된 원본 결과·발생 시각을 읽은 파생 분석이다.
`gate-neighbors.json/log`는 마지막 유효 촬영부터 정지 ROS 시각+100ms의 명시적 창이다.
이는 시간창 문맥 표시이며 다른 촬영을 nearest join한 지연 값이 아니다.
전체 세션 target gap 최대에는 시동/종료와 수신 유실이 포함되므로 정상 추적 공백의
최댓값으로 일반화하지 않는다. fusion으로 제출되지 않은 후보의 내부 거부 사유는
이번 trace만으로 모두 분리할 수 없다. missing trace를 실제 callback 부재로 단정하지 않는다.
각 trace의 발생 시각과 관측기 수신 시각을 구분한다. PARTIAL은 제품 PASS가 아니다.
Gazebo에는 native 카메라 내부 trace가 없어 해당 경계는 UNVERIFIED다.
과거 실패 증거를 EGL 성공으로 재명명하지 않는다. 13.5는 보류한다.

## Task6: 최종 회귀와 인계

`task6-final-pytest.log/xml`:345 PASS/154.42s. `task6-final-result.log`:182 tests,
errors/failures/skips0. `task6-final-installed.json`:다섯 패키지·소스/설치·두 .so 일치.
`task6-results/index.json`:덮어쓰기 전 raw JUnit12개/원래 경로/크기/SHA 보존.
최종 추가 감사는 기존22회/234개 native artifact와 문서 로컬 링크33개를 다시 검증했다.
제품 인수는 여전히 FAIL이며 독립 리뷰가 아닌 작성자 자체 검토다.
상세 변경·원인·미검증·다음 범위는`Ch13/docs/SECTION_13_4_EGL_TRACE_RESULTS_KO.md`를 따른다.
