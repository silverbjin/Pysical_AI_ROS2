# 13.4 종단 인수 변경·리뷰 보고

기준 커밋은 `64f6c0ce91637e90ef44f1dc9c49c7d747adc91f`이며 작업 브랜치는
`feat/ch13-section-13-4-completion`이다. **2026-10-22 종단 인수PASS:** 실제13.4 22회,
양엔진13.3 회귀, 원본 증거·실제 액션 terminal·소스/설치 감사가 모두 통과했다.
원격 SHA는 게시 뒤 Git 원격 ref와 최종 전달 메시지에서 확인한다.

## 변경과 근거

| 경계 | 관찰한 결함과 변경 | 검증 방법 |
|---|---|---|
| 입력→완성 후보 | 같은 촬영의 depth·탐지는 있지만 fusion RGB 캐시에 없는 구간을 확인했다. 탐지기·fusion 입력과 탐지/보정 출력을 유계 reliable로 맞췄다. | 실제 ROS QoS·미완성 후보 회귀, 실제 Gazebo 브리지 publisher 검사, 촬영별 수신/선택/거부 기록 |
| 카메라→제어 시간 | CPU 소프트웨어 렌더링·실행기·작은 영상에 대한 OpenCV 병렬 비용이300ms 여유를 소모했다. shadow map4096→512, 비차단 보행 단일 실행기, 탐지 프로세스 OpenCV1thread로 제한했다. | eye-in-hand EGL 비용 분리, 실제 native 지연,계산 CPU 쌍대 비교,50Hz/기존 기능 및 관절·속도·명령 제한 검사 |
| 액션 수신→소유권 해제 | 공유 실행기 worker가 바쁘면 실제 서버 실행 뒤에도 수락·결과 처리가 지연됐다. 저부하 별도 노드/단일 실행 스레드로 액션 통신을 격리했다. 기존 ArmActionOwner만 명령 수명과 실제 result future 완료를 관리한다. | 부모4worker 점유 최소 재현 RED→GREEN, 실제 RCL goal/result 경계, 목표 UUID별 terminal, context 이전 수신기 종료 |
| 제어 계산→입력 수신 | 서보 TF/math 동안 공용 잠금을 잡아 새 목표·관절·안전 무효화가 대기했다. snapshot 계산을 잠금 밖으로 옮기고 발행 직전 세션 generation·계산에 사용한 원래 표본의 촬영 ROS age와 수신 wall age300ms를 모두 재검사한다. 최신 입력으로 옛 계산의 수신 시각을 갱신하지 않는다. | 계산 중 안전 callback 차단 RED→GREEN, 늦은 세대 명령0, 계산 만료300ms·새 입력의 옛 계산 TTL 갱신 금지 회귀 |
| 기구학 계산 예산 | 매 명령의 정적 URDF 재해석과5회 유한차분 FK가 스케줄링 지연에 취약했다. 모델 수명에 정적 변환/축/limit를 컴파일하고 한 번의 FK와 관절 screw로 투영 Jacobian을 계산한다. | 비영 자세의 독립 MuJoCo 카메라·유한차분 Jacobian 일치, 기존 singular/limit/신선도 검사, 실제 비용·엔진 비교 |
| 고주기 입력 실행 | 긴 stow/PickObject 대기 때문에 입력도 thread pool로 넘겨500Hz clock 처리 비용이 컸다. 입력/제어는 단일 실행기로, 긴 프로토콜만 동시에1건의 worker로 분리한다. | 실제 stow 중 입력 timer 진행, 중복 작업 거절, 시동 중 종료·실제 result drain 회귀 |
| runtime→엔진 종료 | 엔진을 먼저 끄면 runtime이 명령을 받을 수 있고 worker/액션 drain이 엔진 수명보다 늦어진다. 소유 runtime 종료를 먼저 확인한다. Gazebo는 실제 paused 상태를 확인한 뒤 server stop과 native 종료를 기다린다. | 실제 자식 종료 회귀, 양 엔진 native 실행, forced/residual/exitcode·단계 시각 기록 |
| 자식 종료→launch 회수 | 좀비를 완료로 보고 다음 launch SIGINT를 보내면 Popen.poll과 pidfd child watcher가 종료 상태를 경쟁해255가 보고됐다. 부모가 실제 회수할 때까지 PID/start ticks를 확인한다. 자기Popen만 직접poll한다. | 실제Python pidfd/Popen의255 최소 재현, 좀비 조기 완료 RED→GREEN, 소유권·기한 회귀와 실제 영상 손실 재검증 |
| 인수 시험 준비 | 고정1초 대기는 제어 전 픽셀 기준 표본을 보장하지 않았다. 고유 촬영3개와 기존 >1px 조건을 실제 확인한 뒤 한 번 활성화한다. | 실패한 final/m10a 보존, baseline RED→GREEN, 제어 전 capture/wall/명령0 기록 |

320×240 RGB-D, 카메라 목표15Hz, 추론 기본10Hz·선택15Hz, 촬영 ROS age·수신 wall
age300ms, 과거 TF100ms, 팔 명령 최대5Hz를 유지했다. shadow map 변경은 그림자
경계 품질의 변경이며 카메라 출력 크기·물리·관성·intrinsics를 바꾸지 않는다.
프로세스 한정 LP_NUM_THREADS=2는 지연이 악화되어 채택하지 않았다.
실제 fixture 계산300회에서 OpenCV8→1thread는 CPU1.977→0.388s,
p95 2.545→1.668ms였다. 별도 프로세스의 BLAS/OMP 제한은 servo를 개선하지 않아
채택하지 않았다. 운영체제·드라이버·전역 환경은 바꾸지 않았다.

기존 EGL worker/렌더 소유권 구현은 재작성하지 않았다. 외부 checkout/underlay,
sources/ 및 Ch01~Ch12는 수정하지 않았다. 초기 입력/계측 보완에는 제3자 복사가 없었지만,
서버 경쟁 재현 후 최종 수정에는 최소3파일의 Ch13 한정 파생본을 추가했다.
[controller 출처 명세](../ros2_ws/src/integrated_robot_controller/REUSE_MANIFEST.md)를 참조한다.

## 검증과 증거

최신 소스 시험374PASS(`source-final-v5-probe`,193.29s), 6패키지 검사199건/
오류0/실패0/건너뜀0 및 설치 감사가 통과했다. 제품 동결 직전은373PASS였다.
`final-v4/`의 batch UUID는 `084026ad-ae1f-45c2-9536-1726011a86df`이며 소스167파일과
설치380파일을 동결했다. 이 batch는10PASS 뒤 영상 손실의clean_shutdown1FAIL로 중단됐다.
해당 안전 정지·실제 취소 결과와 엔진 종료는 통과했지만 launch가 runtime255를 보고했다.
`source_archive/`의167파일은 당시 동결 해시와 모두 일치한다.

### 최신 실제 엔진 결과

`final-v5` batch `4e8c9e6a-b53e-482a-a563-c09276ebfa84`는 구현 커밋
`f2fa0eba4c042b00bb70f15b4066869ed370d84f`의167소스/380설치를 고정했다.
원래20회 matrix에 Gazebo 추적2회를 추가한22native가 모두PASS다.
실제 명령·UUID·촬영 자료는 각 디렉터리의 result/observations/system/trace에 남아 있다.

| 검사 | MuJoCo(snapshot/EGL) | Gazebo |
|---|---|---|
| 정적, 각30고유 촬영 / RMS≤.03m | OFF .00313131m, ON .00313140m | .00229323m |
| 카메라 이동+150ms,30고유 촬영 / RMS≤.05m | .00252216m | .00187220m |
| 연속 추적 / 픽셀20%이상 감소 | 기본10Hz3회·선택15Hz3회, 각5.20s /91.7%감소 | 3연속, 각5.20s /100%감소 |
| 실제 YOLO 고정 컵 | 102/102탐지 촬영, 유효3D113 | 182/182탐지 촬영, 유효3D181 |
| images / tf / joints 손실 | 각각PASS | 각각PASS |
| 명령·실측 각도/속도·주기 | 모든추적PASS, 최대5Hz/.04rad/.1rad/s 유지 | 모든추적PASS, 같은한계 유지 |
| 실제 액션 결과·runtime/native 정상종료 | 13회 전부PASS | 9회 전부PASS |

추적·취소·종료는 고정 제품 소스에서 MuJoCo10Hz/15Hz 각각3연속, Gazebo3연속을
확인했다. 실패한 실행을 빼고 연속 횟수를 재계산하지 않았다. 기본10Hz와 선택15Hz는
최대 추론 시작 빈도이며 모든 촬영을 처리한다는 보장은 아니다. 실제 컵은COCO class41,
고정 yolov8n SHA256 `f59b3d833e2ff32e194b5bb8e08d211dc7c5bdf144b90d2c8412c47ccfc83b36`을
사용했고 fixture 검출로 fallback하지 않았다.

최초13.3 MuJoCo 회귀는 probe가 만든 합성 목표가 서버의 수신 시계보다56ms 미래여서
FAIL했다. 안전 거절과 runtime/engine 정상종료는 유효하며 원본 실패는 보존했다.
서버의 미래50ms/촬영300ms 허용치를 늘리지 않고, **시험 생성기만** 원래header를
보존한100ms 전달 준비 후1회 전송하도록 보완했다. 제어된실제ROS 경계의RED→GREEN과
전체소스374PASS 후 `legacy-clock-final`에서 양엔진13.3를 재검증해 모두PASS했다.
이는 런타임 수정이 아니며, native22회가 사용한 소스·설치본은 바뀌지 않았다.
새 manifest는 기존167중probe1개 변경과 새회귀1개 추가만 허용하고 모든380설치를 대조한다.
최종 수집 감사는 이 실패를 별도 항목으로 포함하며 원본 결과를 성공으로 고치지 않는다.

최종 파생 판정은 [FINAL_ACCEPTANCE_SUMMARY.json](../evidence/section_13_4/completion-f8c0bed5/final-v5/FINAL_ACCEPTANCE_SUMMARY.json),
마지막 읽기 전용 감사는 [FINAL_POST_TRIAL_AUDIT.json](../evidence/section_13_4/completion-f8c0bed5/FINAL_POST_TRIAL_AUDIT.json)이다.
모든 native 원본 artifact의 크기/SHA256, 명령267건의 실제 결과267건, 취소 요청17건의
실제 terminal17건을 대조했다. 취소 요청 중16건은CANCELED5,1건은이미 완료된SUCCEEDED4다.
취소 요청 자체나ACK를CANCELED로 간주하지 않았다. 최종 pending UUID는 모두없다.
원래167파일 archive와 보완168파일 archive도 각각 manifest와 일치한다.
보완 manifest SHA256은 `284caaed9391a16d96bf4f42ea5652a7c15b41f2a8a82aadfe430ade19227bdb`다.

13.3 회귀는 시동 순서·50Hz 출력·동기화·겹친 목표 거절·취소 실제 결과·미구현 파지 실패·
미션 실패 보존·stale pair 거절·inactive 출력 차단을 검사했다. MuJoCo 명령 주기 중앙값
.018898s/p95 .045139s/max .104857s, Gazebo .020362s/.029862s/.057364s였다.
이는 중앙값 기반 실습 허용치를 통과한 측정이지, 매20ms의 hard realtime 보장이 아니다.
두 엔진 모두 runtime5노드 정상종료와 native exit0, 강제정리 없음/잔여없음을 확인했다.
최종 감사의 일반 사용자UID는1000이며 외부 underlay HEAD는c261f55 그대로 clean이다.

완료된 범위는 **명시적으로 선택한 MuJoCo snapshot/EGL 경로와 Gazebo의13.4**다.
기존 upstream 카메라 기본값은 비교·호환 경로로 유지했으며 이번 수정을 검증한 경로로
승격하지 않았다. main 병합·PR·13.5 재개·실로봇 배포 준비는 이 판정에 포함하지 않는다.

최상위 증거는 [이번 실행 기록](SECTION_13_4_COMPLETION_LEDGER_KO.md)과
[새 evidence](../evidence/section_13_4/completion-f8c0bed5)다.
각 실행은 고유 UUID, 실제 명령, 소스 working-byte 해시, 설치/라이브러리 감사,
원본 센서·촬영 TF·관절·명령·액션·종료 로그를 보존한다.
`frozen-source.json`은 Git HEAD만이 아닌 실제 소스와 설치 바이트를 고정한다.

원래 EGL20회 결과12PASS/8FAIL과13.3 Gazebo FAIL은
[원래 보고서](SECTION_13_4_EGL_TRACE_RESULTS_KO.md)에 보존했다.
이번 첫 최종 batch `final/`도 정적/지연3PASS 뒤 픽셀 기준 표본 부족1FAIL로 중단한
원본 그대로다. 이를 성공 연속 횟수에 넣거나 나중 결과로 덮지 않는다.
두 번째 `final-v2/`는 기하3회와10Hz추적3연속 PASS 뒤15Hz에서 FAIL했다.
그 실행의13번째 목표는 서버 실행 후 클라이언트 수락 콜백까지 약2.36초 지연됐다.
독립 실제 ROS 서버와 부모4worker 점유 시험에서 동일한 수신 정체를 재현했다.
이 시험은 물리 엔진 시험을 대체하지 않으며, 수정 후 새 동결 batch에서 전부 다시 확인한다.
세 번째 `final-v3/`는 기하3PASS 후10Hz에서 FAIL했다. 새 목표가 있어도 계산에
사용한 원래27.242s 표본이 계산 종료 시 약302ms가 되어 명령이 거절됐다.
이는 안전 검사의 정상 동작이다. 새 목표의 시각을 이전 계산에 덮어쓰거나 자동
재계산·재활성화하지 않고, 기구학 계산 비용을 줄인 새 소스로 검증을 다시 수행한다.

실제 액션 경계 계측에서는 서버 결과 응답과 클라이언트 수신을 각각 관찰했다.
일부 과거 간헐 미수신의 단일 내부 원인은 그 당시 경계 로그가 없어 확정하지 못했다.
최신 최소 재현은 부모 실행기의 가용성에 대한 액션 수신 의존성을 입증하지만,
과거 모든 지연을 특정 rclpy 내부 결함 하나로 확정한 것은 아니다.
현재 결과는 새 고정 소스에서 실제 terminal 수신·소유권 해제와 연속 실행으로 검증한다.
trace 누락은 callback 부재로 단정하지 않으며, 관측 범위가 PARTIAL인 자료는 그대로 표시한다.

## 설계 판단과 리뷰

추가 참고 사례는 [quadruped_ros2_control 고정 커밋](https://github.com/legubiao/quadruped_ros2_control/tree/5434c5810d1a7fe223bcfd04550e9d3bfdd4b458)이다.
제어 update와 추론 worker 분리, Gazebo executor cancel/join을 현재 설계의 비교 근거로
사용했다. 이 저장소의 SDK2 DDS 하드웨어 에뮬레이션은 Ch13의 내부 MuJoCo 연결과 다르므로
교체하지 않는다. RGB-D 과거 TF·팔 액션 terminal·전체 정상 종료의 검증 자료를 대신하지 않는다.
특히 해당 RL worker의 무한 루프와 명시적 join 부재는 그대로 도입하지 않았다.
외부 사례를 실행 검증하거나 코드를 복사한 것은 아니며, 이번 비교 때문에 추가 권한·RMW·
드라이버·해상도·인수 기준을 변경하지 않았다.

사용자 지정에 따라 단일 작업자가 구현·자체 리뷰했다. 별도 리뷰 에이전트를 사용하지
않았으므로 독립 검토보다 제한적이다. 자체 리뷰에서 시작 전 실패의 원래 오류가 누락
로그 예외로 덮이는 문제와 engine-first 종료 순서를 발견해 실패 회귀 후 보완했다.

| 설계 판단 | 이유·남는 제약 |
|---|---|
| 사용자 지정 checkout 재사용 | 기존 측정 자산 보존. 별도 파일시스템 격리는 없음 |
| 승인 범위 내 세부 변경의 재승인 생략 | 명시적 사용자 지시. 각 근거와 실패를 실행 기록에 공개 |
| 자체 리뷰 | 네이티브 단일 작업자 지시. 독립 리뷰는 미수행 |
| 입력 단일 실행기·긴 프로토콜 유계 worker | 측정된 clock/pool 비용 완화. OS 실시간 우선순위 보장은 아님 |
| 그림자 맵512 | 렌더 비용 완화. 그림자 품질 변경은 있으나 출력 해상도·물리·보정 불변 |
| 실제spawner/6패키지 기준의 시험 정합 | 소스 문자열 횟수와 예전5패키지 가정을 실제 실행 의미로 교정. 소유권/인수 기준 유지 |
| 남은matrix에서Gazebo추적 우선 | 미검증 긴 경계를 먼저 판별.22개 label/check는 동일 |
| 13.3 합성 목표 전달 준비 | 원래header·1회전송·모든서버 안전 검사 유지. 영향받은 양엔진 회귀만 재검증 |

서비스 발견과 액션 발견은 별개다. 기존 ROS 경계 시험의 action_ready 경합은
액션 서버 준비를 확인한 뒤 신선한 시험 입력을 생성하도록 수정했다. 실패 후 활성화
재시도나300ms 연장으로 통과시키지 않는다.

수신 전용 노드는 launch의 전역 시뮬레이션 시계/노드명 재매핑을 상속하지 않는다.
따라서 high-rate clock·영상·TF 작업이 액션 수신 대기열에 들어가지 않는다.
부모의 시계·입력·제어는 단일 실행기에서, 긴 서비스·PickObject 대기는 유계 worker에서 처리하며,
단일 명령 소유권과
취소 ACK≠terminal 계약은 그대로다. 수신기 비정상 종료는 자동 재시작하지 않고
추적 준비 조건을 차단한다. 생성 실패와 context 이전 종료/재진입 종료를 시험했다.

서버 측 별도 결함도 재현했다. 설치 realtime_tools3.13.0에서 RT 성공이 대기 중인 사이
cancel이 ACCEPT되면 원본 non-RT timer가 성공도 취소도 terminal로 발행하지 못했다.
실제 C++ action 서버/클라이언트의 동일 fixture에서 원본은 cancel ACK0/CANCELING/결과 없음,
파생본은 실제 CANCELED5 결과 수신을 확인했다. 기존 controller를 덮어쓰지 않고 별도
namespace와 `integrated_robot_controller/JointTrajectoryController` ID로 분리했다.
vision=true 경로만 선택하며 vision=false13.2/13.3 설정은 원래 타입을 유지한다.
실제 엔진에서 새 라이브러리의 소유 PID/PGID 매핑과 해시를 필수 검사한다.

문헌 대조: ROS2 [QoS 설계](https://design.ros2.org/articles/qos),
Gazebo8 [Sensors 수명/대기 구현](https://github.com/gazebosim/gz-sim/blob/gz-sim8/src/systems/sensors/Sensors.cc).
Gazebo 내부의 특정 영구 교착을 입증했다고 주장하지 않는다. 부모 GDB 실행은 타이밍을
바꾸므로 진단으로만 보존하고 native 인수 성공으로 승격하지 않았다.

## 해석 범위

이 실습은 기립한 통합 모델의 제한된 두 관절 시선 추적과 RGB-D/과거 TF 처리를 다룬다.
이동+150ms 시험의 이동은 명시적 팔 카메라 진동 fixture이며 PPO 보행 시험이 아니다.
기하 정답은 선언된 물체 전면과 촬영 광선의 교차점으로, 모든 TF 오차를 독립적으로
계측한 결과는 아니다. TF 단일 소유권은 그래프·모델 간선 계약의 확인이며 패킷 GID 인증은 아니다.

PPO 적재 보행, MoveIt 경로 계획, 물리 파지, Nav2/13.5, 실로봇, 실제 motion blur 및
하드웨어 노이즈 일반화는 미검증이다. PickObject의 미구현 파지는 성공으로 반환하지 않는다.
정상 종료 검증은 관리 실행기의 순차 종료 절차 기준이다. 통합 launch에 일괄 Ctrl+C만
보내는 경로는 같은 종료 순서를 보장하지 않으므로 실습 가이드의 관리 절차를 사용한다.
