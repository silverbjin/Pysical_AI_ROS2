# G04 T10 교육용 디버깅 사이클 — ARC RED4: 직선 정지 후 횡오차
## 1. 실제 결과 및 인수 범위
Run 45933266376 / Job 140290534749 / Artifact 15169796413 / source 16f8b057a806f7d2f50d05e6d2d1a3f3f1d43587. ZIP 2,068,707 bytes SHA256 f8d0122d745b0f31bba5dd2cccdeaf452d36f78c35e814cbe6dd25aa1203ef35, 내부 53/53 해시 독립 검증. ARM 재시작0, 양쪽 armed sim3.68s. V2 실제 곡선 728개 표본, 정지 XY20.150mm(기존39.440mm)/yaw .005129rad, 곡선 30mm/.06rad PASS. 이어 실제 직선 227개 표본, 정지 명령 시 XY12.464mm, 실제 정지 후 XY17.089mm>15mm, yaw .019662rad PASS. 전체 FAIL. Native engine COMPLETED, force cap1.0, active fault 없음, clean 3/3, residual PASS. 최초 gateway source timeout은 실제 stationary shutdown ACK(701.976180209)보다 297.352ms 뒤; 원본 guard fault 그대로 보존. G04/원본 CH13_NATIVE L2 PASS 아님.
## 2. 근본 원인 및 측정
실제 직선 정지 전 종방향/횡방향 오차 6.820/10.433mm, 정지 후 1.593/17.015mm. 정지에 의해 횡오차 +6.582mm, 종방향 오차 -5.227mm. 정속 구간 실제 body vx=.043594m/s, vy=-.002919m/s, yaw rate .002498rad/s, mean wz cmd .015856. 측면 미끄러짐의 기하 보상각 atan2(-vy,vx)=.066868rad. 주행 중 오차를 줄였어도 정지 과정에서 15mm gate를 놓칠 수 있다. 종료 판정은 명령 0이 아니라 실제 settled pose로 유지.
## 3. 변경 (V3)
곡선 알고리즘 그대로 유지. 직선에 측정 편향각 .067rad를 남은 0.10m 내에서 점차 0으로 줄이는 feedforward, 정지 횡오차 추정 +.0065m를 cross feedback에 반영. 속도 .035m/s, 기존 yaw cmd ±.05, 정지 lead7mm, tracking/final gates 불변. 실제 RED4 trace를 명령 변화에 대한 선형 yaw gain1.08 근사로 재생: baseline XY17.036mm, 후보8.707mm/yaw .04225rad, 최대 heading .07854rad. 이는 반례를 줄이는 민감도 평가이며 실제 물리 PASS 보장 아님. 선행 곡선은 직선의 동일한 초기 상태를 물리적으로 만들기 위해 필요하며 별도 반복 시험 아님. 실제 V3 pending. 단위 시험은 taper, stop, command limit, 원래 final reject 포함.
## 4. 교육 포인트
제어 명령이 끝난 시각과 로봇의 실제 정지 시각은 다르다. 성공한 구간은 고정하고, 다음 실패 경계(직선의 실제 settle)만 수정한다. 단일 시나리오의 실제 계측으로 추정한 보상량은 일반 모델이 아니라 실험 후보이다. 기존 Ch13 소스/guard/목표 변경 없음.
