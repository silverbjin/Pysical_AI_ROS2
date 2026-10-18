# 13.4 종단 시간 예산·종료 경로 구조 검토

2026-10-19. 10/15Hz 비교 네 건 실패 후 사용자가 일반 권한 부모 디버거 진단과
구조 검토를 승인했다. 이것은 새 제어기 구현 완료 또는 설계 대체안 확정 문서가 아니다.

## 변하지 않는 계약

- 촬영 ROS age와 receipt wall age 모두 300ms 이내여야 한다. 시계 역행/정지는 별도
  invalidation이다. 시뮬레이션 시각과 wall 시각을 섞어 한쪽 실패를 숨기지 않는다.
- 팔 명령은 최대5Hz, q1/q5 소각도 및 측정 속도 제한을 지킨다. 한 세션/한 outstanding
  액션만 허용하고 cancel ACK가 아니라 terminal 결과를 확인한다.
- 안전 정지 후 자동 재선택/자동 재시도는 없다. 여러 짧은 성공을 이어5초로 세지 않는다.
- 기본 추론10Hz, 명시적 선택 최대15Hz. 해상도320×240와 RGB-D 목표15Hz는 유지한다.
- 외부 플러그인/앞 장/시스템 ptrace 정책/관리자 권한 변경은 이 검토에 포함되지 않는다.

## 실제 측정과 미확정 구간

| 경계 | 현재 근거 | 해석 한계 |
|---|---|---|
| 촬영→detector 수신 | 원본 capture_ns, receipt_ros_age_s | 렌더 snapshot 생성·native publish·DDS 전달 시간을 각각 분리하지 못함 |
| 수신→추론 시작 | queue_s, one-slot worker | 상한 Hz는 시작 주기 상한이지 OS 스케줄링 보장 아님 |
| 변환·추론 | conversion_s, inference_s | 별도 프로세스여도 CPU/GPU/메모리 대역폭은 공유함 |
| 탐지→fusion | 같은 촬영 header, RGB-D 후보 캐시, TF 예외 | observer 도착 시각은 실제 publish 시각과 다름; 음의 도착 차이를 인과 지연으로 사용하지 않음 |
| fusion→제어 | target 원본 stamp/제어 receipt, OFF 입력 snapshot | 추론만 빠르다고 오래된 입력 또는 미도착 다음 프레임을 복원하지 못함 |
| 액션 수락→결과 | UUID별 sent/accepted/result_requested/terminal/cancel 로그 | status/ACK만으로 결과 수신 완료를 추정하지 않음 |
| stop ACK→엔진 종료 | native PID 대기·실제 자식 로그·exit code | ACK는 정지 완료가 아니며 launcher0도 내부 SIGTERM을 숨길 수 있음 |

MuJoCo15Hz 실패 직전 queue3.78ms, 추론20.75ms만 개선해도 카메라 입력 촬영 간격
218ms와 수신 당시 ROS age134ms 문제를 모두 해결한다는 근거는 없다. Gazebo10Hz는
ROS age274ms이지만 receipt wall age가300ms를 초과했다. 따라서 ROS TTL만 늘리거나
시뮬레이션 속도를 낮추는 식으로 양쪽 계약을 동시에 만족한다고 할 수 없다.

## 검토 순서

1. 현재 바이트/의존성/실행 결과를 고정한다. 회귀 테스트 통과와 native 추적 실패를
   나눠 기록한다. `2c9f221`은 complete-pair/중복 방지와 rate 전달 체크포인트다.
2. 일반 권한 부모 GDB로 **Gazebo만** 시작한다. 공식 launch prefix 필터는 실제
   executable basename `gz sim`에 적용한다. 나머지 센서/제어 프로세스에는 적용하지
   않는다. autoload·debuginfod는 끄고 외부 소스/시스템 설정은 수정하지 않는다.
3. 종료 요청 때 자체 inferior만 MI interrupt로 멈춰 thread backtrace를 기록한 다음
   원래 종료 신호를 전달한다. 이는 관찰로 실행을 교란하는 진단이며 정상 종료 성공
   또는 성능 인수 시험으로 쓰지 않는다. 기존 프로세스에 attach하지 않는다.
4. 스택에서 확인한 종료 대기/렌더링/제어 경계를 실제 소스와 대조한다. 샘플 하나로
   교착을 단정하지 않는다. symbol 부재/중단 위치/재현 실패도 그대로 기록한다.
5. 종단 지연의 비중이 확인된 뒤에만 구조 변경안을 확정한다. 수신·state 갱신을
   막는 임계구역, 비동기 계산 완료 시 재검사, native render/physics snapshot 소유권,
   제한된 최신 입력 전달을 검토한다. 이미 별도 프로세스라는 이유로 격리를 보장하지 않는다.
6. 외부 plugin 결함 수정이나 새 센서 프로파일이 필요하면 별도 설계·승인을 받는다.
   변경 후 두 엔진·입력 상실·기존 기능을 새 고정 소스로 재검증하기 전에는13.5를 재개하지 않는다.

## 부모 디버거 도구의 검증 한계

`parent_debugger_13_4.py`는 진단 전용 prefix다. 실제 GDB 자식 시험으로 native exit7
전달과 스택 수집 후 SIGINT 전달/정상 exit0을 검증했다. 첫 시도에서는 준비 문자열이
명령 메타데이터에도 있어 초기화 중 SIGINT를 보내는 시험 오류가 드러났다. 실제 독립
출력 행으로 준비를 판정하고 MI 실행/중단 상태를 추적하도록 수정했으며 실패 로그도
보존했다. 단위 자식 시험이 Gazebo 정지 원인을 밝혔다는 뜻은 아니다.

첫 native prefix 실행은 중간 shell 때문에 직접 신호 전달을 못 받았다. prefix 앞에
`exec`를 추가한 진단에서 실제 전체 스택을 수집하고 SIGINT 전달 후 native exit0을
확인했다. 이 관찰로 제품의 모든 간헐 종료가 해결됐다고 쓰지 않는다. 추적은6명령 뒤
계산 중 입력 만료로 실패했다. 또 debugger inferior는 별도 PGID이므로 제품 검증기의
동일 PGID 기반 대기/잔여 검사와 다르며, 이 실행은 진단 결과로만 해석한다.
