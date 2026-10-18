# 13.4 대상별 추적·필터 중간 검증

`full.txt`: 기존 Ch13과 시각 패키지 테스트 전체 130개 통과.
실제 엔진 3D 오차·팔 시선 추적을 통과했다는 뜻은 아니다.

## 고정한 동작

- odom 기준으로 한 대상을 선택한다. class·IoU≥0.1·3D 거리≤0.2m를 검사하고,
  동률/0.05 이내의 모호한 association은 무효화한다.
- ID는 프로세스 UUID + epoch + 증가 counter다. 새 class/calibration/epoch,
  상실 후 재획득에는 새 ID와 새 필터를 사용한다.
- time-constant LPF 기본 tau=.2초, alpha=1-exp(-dt/tau).
  비교용 fixed_alpha 모드도 있으며 0<alpha≤1을 검사한다.
- outlier·역순/중복 표본은 관측 시각이나 TTL을 갱신하지 않는다.
- 최대 age는 ROS/monotonic 모두 .3초다. clock 정지에도 steady timer가 만료를 알린다.
- LOST/INVALID/TF_UNAVAILABLE/RESET은 valid=false로 발행하며 원래 마지막 관측 시각을 보존한다.
  raw/filtered PointStamped를 새 시각으로 반복 발행하지 않는다.
- TrackedTarget의 score·source_header·processed_at·공분산과 filtered 위치를 확인했다.
  공분산은 depth 표본 근사이며 보정된 통계 신뢰도가 아니다.

## 추가 회귀

- 실제 tf2 Buffer와 ROS publisher/subscriber로 150ms 과거의 두 표본을 재생했다.
  필터 값·ID 유지·원본 header·만료 후 새 유효 위치 부재를 확인했다.
- calibration 변경 시 TTL을 기다리지 않고 즉시 RESET을 발행한다.
- Unix epoch 초를 float로 왕복하면 1ns 일치를 보장할 수 없어, 실제 ROS 경계는
  원본 Time 메시지의 정수 nanoseconds로 RGB 일치와 depth skew를 검사한다.
  합성 float-seconds API는 남기되 나노초 식별에는 Time 입력이 필요하다.
- 비정규 nanosec 필드는 거부하고 callback 밖으로 예외가 새지 않도록 했다.
- tf2 기본 backward-jump threshold(-1초)보다 작은 -0.1초 clock 역행에서도
  이전 동적 TF가 남는 문제를 RED로 재현했다. epoch 변경 때 명시적으로 동적 TF를
  지우며 고정 extrinsics가 유지되는지 실제 Buffer로 검증했다.

관측 전에는 가짜 좌표·시각을 만들어내지 않으므로 TrackManager.update는 None을 반환할 수 있다.
다른 기준 frame의 좌표를 odom으로 단순 재명명하지 않고 무효화한다.
이 인터페이스를 소비하는 팔 제어기는 valid/status/원본 시각/ID를 함께 확인해야 한다.
