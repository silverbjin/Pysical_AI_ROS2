# 13.4 실패 경과와 근본 원인 재분석

작성: 2026-10-20(Asia/Seoul). 조사 기준: e580702391c959f1e3debb7bdff4caa4238c9389.
사용자의 새 원인 분석·해결 요청으로 보존 전용 상태를 재검토했다.
이번 조사는 기존 로그와 현재 소스·설치 라이브러리의 읽기 대조다.
새 제품 수정·엔진 재실행·기준 완화는 하지 않았다. 아래 수정 방향은 아직 승인 전이다.

후속 갱신: 사용자가 첫 수정 단위를 EGL 전용 카메라·종단 계측으로 확정했다.
[서면 설계](specs/2026-10-20-egl-camera-latency-design.md)를 승인받았으며
[구현 계획](plans/2026-10-20-egl-camera-latency-plan.md)은 검토 대기다.
아래의 조사 당시 승인 전 표기는 역사적 문맥이며, 새 구현·실측 미착수 상태는 유지한다.

## 1. 경과 요약

| 실패 | 대응 | 남은 의미 |
|---|---|---|
| 무거운 뷰어와 지연으로 입력 만료 | headless 비교, 단계별 지연 계측 | 지연 기하는 개선됐지만 연속 추적은 별도 실패 |
| 컵 미탐지·ultralytics import 실패 | 기하 fixture와 자체 컵 분리, venv 실행 파일 교정 | 두 엔진의 컵 탐지 관측은 성공, 일반화·파지 증명 아님 |
| timer 재진입이 executor 점유 | 제어 timer를 MutuallyExclusive 그룹으로 분리 | 관련 회귀 통과, 모든 액션 지연이 해결된 것은 아님 |
| RGB-D 완성 후보 덮어쓰기·중복 처리 | 완성 후보 제한 캐시와 제출 watermark | 실제 순서 회귀 수정, 종단 기한 보장은 아님 |
| 10Hz 추적 입력 만료 | 승인된15Hz 비교 | clean10Hz3회·15Hz3회 모두 실패, Hz 증대만으로 해결 안 됨 |
| native snapshot 동시 접근 위험 | Ch13 두 버퍼·move-only lease·독립 플러그인 | 데이터 수명과 렌더 API 스레드 적합성은 서로 다른 계약 |
| snapshot과 원본 카메라 중복 렌더 | snapshot 경로의 자동 등록만 차단 | 숨은 발행/부하 제거, 추적 실패 자체는 지속 |
| 액션 terminal 미확인·Gazebo 종료 실패 | UUID별 사건·정리 기록, 부모 디버거, 후속 엔진 차단 | 일부 정상 실행과 실패가 공존, 원인 규명 미완료 |
| 최종 리뷰에서 worker GLFW 호출 위반 발견 | 사용자 선택으로 실험 브랜치·실패 증거 보존 | EGL 수정은 당시 수행하지 않음 |

상세 역사: [실패 수정 기록](SECTION_13_4_DEBUG_KO.md),
[종단 시간 검토](SECTION_13_4_TIMING_REVIEW_KO.md),
[최종 보존 판정](../evidence/section_13_4/cam-66d636a0/RETENTION_KO.md).

## 2. 확인된 원인과 미확정 가설

### A. 확정 결함: 데이터 소유권과 GLFW 스레드 계약의 혼동

snapshot_camera_plugin.cpp50행에서 worker를 시작하고 update_loop412행의
430/435/437행에서 glfwDestroyWindow/Init/CreateWindow를 호출한다.
설치 헤더와 공식 GLFW 문서는 이 API들을 메인 스레드로 제한한다.
렌더 worker 하나만 자원을 소유한다는 사실은 이 규정을 충족시키지 않는다.
이는 snapshot 구현에 남긴 실제 결함이며, 정상 이미지가 나온 시험으로 면책할 수 없다.
GLFW가 먼저 성공하면 init_egl_context를 호출하지 않으므로 MUJOCO_GL=egl 환경변수도
해당 C++ 실행 경로를 바꾸지 못한다. 실제 로그는 Snapshot renderer GLFW/llvmpipe다.

근거: [호출·헤더 원문](../evidence/section_13_4/cam-66d636a0/glfw-contract.log),
[GLFW 공식 스레드 계약](https://www.glfw.org/docs/latest/intro.html#thread_safety).
MuJoCo3.3.7의 [렌더링 문서](https://mujoco.readthedocs.io/en/3.3.7/programming/visualization.html)는
OpenGL context가 실행 스레드에 current여야 함과 Linux의 EGL 경로를 설명한다.
EGL 전환은 API 적합성 개선 방안이지 GPU 가속이나300ms 성공의 자동 보장이 아니다.

### B. 확정 실패 경계: 종단 age와 다음 결과 간격의 예산 미달

clean/m10a,b,c의 observations.json에서 마지막 enable_ack 이후 첫 disabled 상태를
선택하고, 노드가 발행한 inputs.ros_now_ns-target_capture_ns를 계산했다.

| 실행 | 중단 사유 | 촬영 age | 해당 노드의 목표 수신 후 wall age |
|---|---|---:|---:|
| m10a | target_fresh |306ms|143ms|
| m10b | target_fresh |304ms|141ms|
| m10c | target_fresh |302ms|192ms|

이 세 실행에서는 수신 후300ms가 아니라 촬영 후300ms 검사가 먼저 실패했다.
기존 입력을 계속 사용하도록 TTL을 늘리는 것은 해결이 아니라 안전 계약 변경이다.
clean15Hz 세 실행은 invalid/lost target이다. 그 경로는 target을 None으로 지우므로,
상태의 target_capture_ns=0을 실제 촬영 시각으로 빼서 age를 계산하면 안 된다.

연속 제어에는 각 결과의 지연만이 아니라 다음 결과가 오는 간격까지 여유가 필요하다.
같은 clock domain에서 '현재 결과의 촬영 age + 다음 유효 갱신까지 경과'가
300ms를 넘으면 중간에 안전 정지한다. 추론 평균 시간이나 설정10/15Hz만으로
최악 지연·갱신 간격·CPU 스케줄링을 보장하지 못한다.
두 엔진에서 llvmpipe CPU 렌더링이 관측됐고 렌더 제한 비교도 있지만,
자원 경합 하나가 모든 실패를 설명한다는 인과는 아직 입증하지 못했다.

관측기의 wall은 콜백 수신 시간이다. 진단 메시지에는 밀려서 도착한 과거 촬영도 있으므로
관측기 도착 간격을 원래 렌더 주기나 추론 시작 주기로 간주하지 않는다.
앞으로 원인을 나누려면 생산자 내부 submit/acquire/render/readback/publish 시각과
sequence를 기록하고, 추론·fusion·제어 수신을 같은 촬영 ID로 연결해야 한다.

### C. 별도 미확정 결함: terminal 결과 전달과 엔진 종료

주실험 md에서 서버 status4를 보았지만 owner의 result_future_done은 false였다.
cancel return_code3도 terminal 결과 수신 증명이 아니다.
이는 이미지 freshness 실패와 분리해야 한다. 설치된 Jazzy ActionClient는
_get_result_async의 send와 pending 등록을 같은 내부 lock에서 처리하므로,
과거의 무잠금 등록 race를 현재 버전에 그대로 적용해 원인으로 단정하지 않는다.
서버의 result 요청 수신/응답과 클라이언트의 take/execute/done 구간은 아직 분리 계측되지 않았다.

Gazebo는 정상 종료 사례 외에 SIGINT 후 SIGTERM/exit-15 및 bridge crash 사례가 있다.
부모 GDB의 한 번의 condition/barrier wait 스택은 영구 교착 증명이 아니다.
MuJoCo EGL 수정으로 Gazebo 종료까지 해결됐다고 주장할 수 없다.
원본 로그, status, cancel ACK, terminal 결과, 실제 native 종료를 각각 보존해야 한다.

## 3. 이전 대응이 충분하지 않았던 이유

처리량(Hz), 프레임 데이터 정합성, API의 스레드 적합성, 결과 전달, 종료 수명은
서로 다른 계약인데 일부 수정의 효과를 전체 안정성으로 기대했다.
기존 회귀는 개별 순서·데이터·GL 결과를 검사했지만 GLFW의 호출 스레드 적합성이나
실제 C++ controller와 소프트웨어 렌더러 부하 아래의 종단 여유까지 입증하지 않았다.
최종285 소스 시험과123 패키지 시험의 성공은 native 실패를 반증하지 않는다.

## 4. 권장 수정 순서 (설계 논의용, 구현 미승인)

1. Ch13 snapshot의 GLFW worker 경로를 제거하고 기존 EGL 코드를 엄격한 headless
   worker 소유 경로로 정리한다. init/부분 실패/current/reinit/destroy 스레드 회귀를 먼저
   실패 재현한다. EGL 실패는 명시 실패이며 GLFW 자동 fallback은 두지 않는다.
2. 같은 촬영 sequence의 단계별 steady-time 계측을 추가하고, 동일 해상도·기본10Hz·
   300ms·TF100ms·팔5Hz를 유지한 실제 MuJoCo에서 지연 기여도를 확인한다.
   큰 계측 부하가 성능 자체를 교란하지 않도록 범위를 제한한다.
3. 액션은 실제 FollowJointTrajectory controller를 포함한 독립 경계 시험으로
   status4/5/6와 result future 완료를 대조한다. 재현 전 임의 timeout 증가·
   재시도·status 기반 소유권 해제는 하지 않는다.
4. Gazebo 종료는 별도 소유권·신호 전달·렌더/bridge 대기 경계로 조사한다.
   외부 소스·드라이버·시스템 변경이 필요해지면 별도 승인을 받는다.
5. 원인별 수정마다 RED→GREEN과 관련 회귀를 수행하고, 마지막에 고정 소스로
   두 엔진·clean10/15Hz·손실 주입·정상 종료를 다시 검증한다. 실패를 보존하고,
   전체 인수 전에는 snapshot 기본 승격·main 병합·13.5를 진행하지 않는다.

이 문서는 조사 결과와 수정 방향을 제시하며, 새 아키텍처 설계서 승인이나
문제가 해결됐다는 보고를 대체하지 않는다.
