# ROS 통신 회귀 시험의 시작 경쟁 분석

2026-11-05 KST. 단일 작업자. 실제 로봇 engine을 실행하지 않은 DDS 시험의 준비 경계를 분석한 기록이다.

## 결과

시험 발행자가 relay의 연결 준비 전에 합성 시각을 진행해, 서로 다른 시점의 최신 메시지가 첫 수신 묶음에 섞였다. 기존 gateway는 미래 입력으로 이를 거부했다. 실제 gateway의 시간 허용치와 안전 정책은 수정하지 않았다. 시험 발행자에 연결 준비 확인을 추가한 뒤 통신 시험군24개가 통과했다. 전체 회귀와 실제 미션 결과는 별도로 기록한다.

| 확인 단계 | 결과 |
|---|---|
| v19 최초 전체 | 347 PASS/1 FAIL,81.39초. publisher 교체 주입 전 arm 준비에서 FUTURE_SOURCE:joints |
| 독립 통신 시험군 | 23 PASS/1 FAIL,23.91초. base 손실 주입 전 같은 시작 실패 |
| 원본 수신 추적 | 해당 시험 파일10 PASS/1 FAIL,10.62초. 정상 raw→safe 시험이 시작 경쟁으로 중단 |
| 연결 준비 확인 추가 | 통신 시험군24 PASS/23.00초,324 deselected |
| 최종 전체 회귀 | 348 PASS/57.79초. 시험 source357개와v19 실행 동결 source357개의 hash 전수 일치 |

## 실제 수신 자료

기존 StartupTrace를 시험용 gateway에만 연결해 원본 C++ 수신 시각과 Python 처리 시각을 보존했다. 실패한 gateway_8의 첫 메시지들은 아래와 같다.

| 입력 | 원본 stamp(sim초) | native receipt(monotonic wall초) |
|---|---:|---:|
| clock | 2.34 | 32584.917187943 |
| raw | 2.40 | 32584.917244685 |
| joints | 2.44 | 32584.917288227 |
| base | 2.54 | 32584.917354685 |

거의 같은 수신 구간에서 base가 마지막 clock보다200sim ms 미래였다. 아직 clock이 없는 앞선 base/joints 샘플도 기록됐다. gateway는 원래의100ms 미래 입력 거부 조건으로 FAULT를 걸었다. 다른 두 실패의 상세 수신 순서까지 이 추적으로 증명한 것은 아니다.

코드상 시험 발행자의20ms timer는 relay를 실행한 직후부터 시각을 증가시켰으며, 개별 DDS 구독의 구성·매칭 완료를 기다리지 않았다. 이 시험들의 목표인 arm 후 입력 손실/소유자 교체 전에 준비 경쟁이 혼입된 것이다. 관측 결과를 gateway의 허용 시간 부족으로 해석해 기준을 넓히지 않는다.

## 공식 패턴과 수정 범위

[설치 rclpy7.1.12 Publisher.get_subscription_count](https://github.com/ros2/rclpy/blob/7.1.12/rclpy/rclpy/publisher.py)는 매칭된 구독 수를 제공한다. [Jazzy executor 설명](https://github.com/ros2/ros2_documentation/blob/jazzy/source/Concepts/Intermediate/About-Executors.rst)은 서로 다른 callback의 실행 순서를 일반적인 FIFO 보장으로 취급할 수 없음을 설명한다. 이 문서만으로 이번 지연 원인을 추정하지 않고, 위 원본 수신 자료와 시험 준비 코드를 함께 확인했다.

test_ros_wire의 합성 producer는 다음 연결을 확인한 뒤 첫 sample을 발행하고 시각을 진행한다: clock 구독2개, base/joints/raw 각각1개, gateway relay 발행자1개. 실제 ingress.cpp의 연결 수와 맞췄다. 준비 완료는 한 번만 latch해 이후 publisher 교체·입력 손실 주입을 막지 않는다.

매칭 수는 동작 권한이 아니다. 기존 fresh sample/zero command/명시적 arm과3초 준비 예산을 그대로 통과해야 한다. 원본 stamp/receipt/GID를 바꾸지 않았고, 미래 입력 거부·50ms 순서 대기·300ms 원본 수명·FAULT latch를 유지했다. production gateway/relay의 코드는 수정하지 않았다.

## 한계와 보존

수정 후24개 시험군 통과는 이번 준비 경쟁에 대한 회귀 확인이다. 모든 DDS 부하에서 시작 성공을 보장하거나 과거 실제 engine의 모든 startup 실패를 해결했다는 뜻은 아니다. 실패 로그와 추적 자료, 수정 전후 결과를 preflight_v19에 보존한다. 안전 guard가 실제로 거부한 원본 FAIL을 삭제하거나 PASS로 재판정하지 않는다.
