# G04 T10 디버깅 사이클 — ARC RED2: DISARMED 수신 순서 실패
## 1. 재현 및 증거
- 실행 45931318335 / Job 140284391526 / 소스 bf4d37d588cb87656c13e34056e4aaa6e5fd774b
- Artifact 15168868803, ZIP 1,792,507 bytes, SHA256 1111ead2eefdf096aa88073f38f7f865b0937b7a1169736e738f52e8034f4a59, 내부 52/52 독립 검증.
- 실제 엔진 1,128개 표본, 비영 속도 명령 0건, phases=[]: 곡선과 직선 모두 NOT_RUN.
- Gateway DISARMED 이후 FUTURE_SOURCE:base, 마지막 승인 base/joints 604ms, raw 600ms. Platform DISARMED. 기존 300ms ARM 이후 timeout과 다른 첫 실패.
- 엔진 COMPLETED, 22.568 sim s / 29.519 wall s, 같은 compiled model SHA, actuator cap ratio 1.0, 3/3 exit0, 잔류 없음/lock free.
## 2. 원인 가설과 반증
엔진의 .48~.88 sim s 구간 20ms 표본이 wall 약 24~33ms 간격으로 계속 발생했다. RED1에서 확인된 엔진 자체의 360ms stall과 구별한다. 원본 CommandGateway는 clock보다 100ms 초과 앞선 base를 즉시 차단하며 FutureInbox는 원래 receipt 및 50ms catch-up/300ms lifetime을 검증한다. 그러나 이번 archive에는 최초 패킷 native receipt와 처리 순서가 없어 어느 분기인지 확정하지 않는다. 단순 ARM 게이트 완화는 disarmed latch에 효과가 없다.
## 3. 변경 및 검수
Ch15 실행기에만 Linux CPU affinity를 추가: ingress 전용 첫 CPU, gateway 두 번째 CPU(작은 supervisor와 공유), platform/renderer 나머지 CPU, 최소 4 available CPUs. 기존 4-core runner에서 DDS callback 경쟁을 줄이는 단일 후보이며 인과 입증 전 가설이다. Ch13 내장 CH13_REUSE_STARTUP_TRACE를 gateway에만 활성화하여 original source stamp / native receipt / Python processing / first fault를 보존한다. FAULT 발생 즉시 prearm 실패, reset 없음. 기존 prearm 연속성, 원본 guard, 동일 곡선 제어 및 모델 모두 유지. 실패시 next cycle에서 trace 분기 분석, 추측성 파라미터 조정 금지. 실제 결과는 아직 미확정.
## 4. 교육 포인트
정지 상태도 안전 입력 계약을 만족하지 못하면 주행을 시작하면 안 된다. 검수 로그의 최종 timeout보다 최초 latched fault를 먼저 찾는다. DDS 수신과 Python 처리 시간을 구분한다. CPU affinity는 안전 검수 완화가 아닌 호스트 스케줄링 실험이다. 성공해도 table-area/BT/rosbag 전체 G04와 동일하지 않다.
