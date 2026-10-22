# 13.4 EGL·종단 계측 결과와 남은 실패

2026-10-21. 네이티브 단일 작업자, 작성자 자체 리뷰. 독립 리뷰·서브에이전트 없음.
승인 범위는 GLFW worker 계약 수정과 지연 관측이며, 액션/종료 정책 재설계는 포함하지 않는다.

## 1. 결론

EGL context/surface/GL 자원을 같은 렌더 worker에서 생성·사용·해제하도록 수정했다.
실제 EGL 호출 시험에서 GLFW0, worker TID 일치, 부분 실패·재초기화·peer context 보호를
확인했다. 원본 외부 플러그인·드라이버·해상도·300ms·팔5Hz·학습 정책은 바꾸지 않았다.
EGLDisplay 한 연결은 다른 context를 무효화하지 않도록 프로세스 수명으로 유지한다.
실제 renderer는 llvmpipe/Mesa 소프트웨어 경로이며 GPU 가속을 얻었다는 뜻이 아니다.

고정 소스 `09b057465da50ffcf892c30e2e8f7e9f516ab953`,
증거 체크포인트 `9f182b04b0e853d100c96ee95bfe17780b429fab`.
문서 체크포인트 `4b0a69ac286182f74957fed6d2c280f64efc1aec`의 절 브랜치 push는
non-fast-forward로 거절됐다. 확인된 원격은`91c02156fdcb50eac1de58d412ac95e7f8d34149`로,
main 병합·Ch11 및 이전 Ch13 패키지 추가 등165파일 변경을 포함한다.
원격 덮어쓰기·자동 병합/재배치는 하지 않았다. 새 브랜치 게시 또는 통합 방향은 사용자 결정 대기다.
[원본 색인](../evidence/section_13_4/egl-424240ff/INDEX.md),
[22회 수행·해시 감사](../evidence/section_13_4/egl-424240ff/task5-audit.log),
[실제 환경](../evidence/section_13_4/egl-424240ff/native-environment.json).

## 2. 실제 시험 결과

| 조건 | 결과 | 의미 |
|---|---|---|
| MuJoCo static 계측OFF/ON | 둘 다 PASS | 각30 고유 촬영, RMS3.1311/3.1314mm, 단일 소유권·정상 종료 |
| MuJoCo motion+150ms delay | PASS | 30개/RMS2.7048mm; 최신 TF 비교12.0724mm |
| MuJoCo tracking10Hz3회/15Hz3회 | 6회 모두 FAIL | 5초·픽셀 감소 미달; m15c는 취소 미확인/종료도 FAIL |
| MuJoCo 컵 YOLO, images/tf/joints 손실 | 4회 PASS | 실제 영상·고정 YOLO; 각 손실 대응·종료 검사 |
| Gazebo 컵 YOLO, images/joints 손실 | 3회 PASS | tf 손실은 대응 통과/정상 종료 FAIL |
| Gazebo static/delay | 2회 PASS | 실제 엔진 기하 시험; native 카메라 내부 trace 없음 |
| Gazebo tracking | FAIL | 1.28초/4명령; 각도·속도·명령 주기 통과, 지속/감소/종료 미달 |
| 기존13.3 MuJoCo/Gazebo 회귀 | PASS / FAIL | Gazebo는 mission_commander와 엔진에 SIGTERM 필요 |

13.4는20회 중12 PASS/8 FAIL, legacy2회까지 실제22회다.
모두 종료 뒤 잔여 엔진 없음이 확인됐다. 강제 정리·잔여 없음·정상 종료·물리 hold는 다르다.
`m10a/b`의 제한 검사 false에는 충분한 명령 표본 부재가 포함되므로 실제 제한 초과로
단정하지 않는다. Gazebo 컵은158 탐지 프레임/121 유효3D를 관측했다.
기하 RMS는 선언된 전면 x=.98 표면과 촬영 RGB ray의 일관성 지표이지 독립 실로봇 ground truth가 아니다.
OFF/ON 한 쌍의 차이는 환경 변동도 포함하므로 통계적 무부하 보장이 아니다.

## 3. 실패의 더 근본적인 경계

마지막 유효 촬영의 **발행 당시 나이**와 **다음 유효 갱신까지의 공백**이 함께 기한을 소비한다.
설정15Hz나 평균 추론 속도만으로 최악의300ms 여유를 보장하지 못한다.

| 실행 | 마지막 유효 fusion 발행 ROS age(ms) | 정지 관측 ROS age(ms) | 수신 후 wall age(ms) |
|---|---:|---:|---:|
| m10a |84|302|205.71|
| m10b |148|312|149.09|
| m10c |74|304|235.15|
| m15a |68|300|224.72|
| m15b |118|308|227.09|
| m15c |190|340|139.55|

ROS 나이는 원 capture와 해당 경계 ROS now끼리, wall 나이는 CLOCK_MONOTONIC끼리
계산했다. 서로 다른 시계를 더하거나 빼지 않았다. GATE_LOST는 취소 경로 직후의 관측
시각이지 입력이 물리적으로 바뀐 정확한 순간은 아니다. invalid/lost 경로에서도 마지막
유효 capture를 보존하며 capture0을 실제 촬영으로 계산하지 않는다.

관측 native publish 간격 중앙값은 약72–78ms였다(수신된 trace 사이 값이며 유실 시 늘어날 수 있음).
10Hz의 detector queue p95는 약69–76ms,15Hz는23–29ms로 줄었지만 모두 실패했다.
같은 세션의 native render API p95는 약74–88ms다. render/readback은 API span이며
독립 GPU 연산량이 아니다. CPU 경합 하나가 모든 실패의 원인이라는 인과는 확정하지 못했다.

예를 들어 m15a의 마지막 유효 capture25.933999999s는 age68ms에 fusion 발행됐다.
이후26.001999999s와26.157999999s의 detector PUBLISHED를 관측했지만 해당 촬영의
유효 fusion 갱신은 관측하지 못했고, 이전 목표는 age300ms에서 중단됐다.
다음 관측 유효 fusion capture26.307999999s는 이미 늦었다.
이 사례는 **탐지 처리량과 완성 RGB-D/TF 목표 갱신율의 불일치**를 보여준다.
그러나 제출되지 않은 후보의 cache 거부 사유·각 입력 callback 수신과 trace 전달 손실을
현재 기록만으로 완전히 분리할 수 없다. missing trace를 callback 미실행이나 cache 결함의
확정 증거로 삼지 않는다. 다음 조사는 이 경계를 먼저 재현·계측해야 한다.

[exact-capture 파생 분석](../evidence/section_13_4/egl-424240ff/native-analysis.json),
[명시적 촬영 창 문맥](../evidence/section_13_4/egl-424240ff/gate-neighbors.json).
전체 세션 gap 최대에는 시동·종료·유실이 섞여 있으므로 정상 추적 구간 최댓값으로 사용하지 않는다.

## 4. 구현·검증 계약

- C++ lease에 submit/acquire metadata를 함께 보존한다. producer에서 JSON/파일/trace ROS 발행은 하지 않는다.
- detector/fusion/tracking의 실제 발생 시각과 원 optical source header를 기록한다.
  제어 lock 밖에서 직렬화하며, trace 오류가 TTL·명령 소유권을 갱신하지 않는다.
- 실행 UUID/source_frame/capture_ns exact match와 boot/CLOCK_MONOTONIC 검증을 사용한다.
  epoch는 생산자 로컬 값이다. 중복·상충·음의 구간·누락은 nearest/now로 보충하지 않는다.
- BEST_EFFORT/VOLATILE/depth32,4096byte,20000attempts/producer,수집80000/16producer 상한.
  유실 총수 unknown은 null/PARTIAL이다. sequence gap은 전체 유실의 확정 수가 아니다.
- 실제 owned native PID/boot/EGL 로그와 camera/mailbox 두 .so 해시까지 맞아야 native 분석을 인정한다.
  Gazebo native 내부는 UNVERIFIED, Python 일부 구간은 관측 가능하다. 진단 상태는 제품 상태와 독립이다.

실측 전 소스345 PASS/148.40s, 패키지182 tests/errors0/failures0/skips0,
다섯 패키지 source/share/인터프리터/C++ manifest/두 라이브러리 설치 감사 PASS.
실제 EGL CTest5등록(41 named gtests)의 lifecycle·peer·lease·UTF-8·상한·transport 오류 회귀도 포함한다.
최종 `task6-final-pytest.log/xml`도345 PASS/154.42s, 패키지182 tests/errors0/failures0/skips0,
다섯 패키지 설치 감사 PASS다. 원본 JUnit은`task6-results/index.json`과 함께 보존한다.
단위/설치 PASS는 native FAIL을 반증하지 않는다.

## 5. 다음 수정 단위와 미검증

1. 탐지→완성 RGB-D 후보→fusion 제출/거부 경계를 같은 촬영의 유계 사건으로 재현한다.
   유효 갱신 공백을 설명한 뒤 최소 수정·RED→GREEN·실제 엔진으로 다시 검증한다.
2. 실제 FollowJointTrajectory 서버의 result 요청/응답과 클라이언트 take/execute/done을
   독립 계측한다. status4나 cancel ACK만으로 소유권을 해제하지 않는다.
3. Gazebo/runtime 종료는 신호·callback·렌더/bridge 대기 경계를 별도 설계로 조사한다.
   이번 결과로 영구 deadlock이나 외부 드라이버 결함을 단정하지 않는다.

위 정책·아키텍처 수정은 이번 동결 실측 뒤 임의 적용하지 않았다. 별도 설계/승인이 필요하다.
PPO 적재 보행, MoveIt2 계획, 물리 파지/운반, Nav2 접근, GUI 수동 검토, 실로봇은 UNVERIFIED다.
기립 기준 제어와 컵 탐지는 이를 대신하지 않는다. snapshot 기본 승격·main 병합·13.5는 보류한다.
