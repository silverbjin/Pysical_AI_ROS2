# v47 관측 시작 지연 최소 보완 명세

정상 완주 기준 유지·Owner 인수 보류. source v46 기준의 저장 자세 재현에서, 첫 vision.tick 지연이 원통 모델 모듈의 lazy import와 겹치는 것을 직접 측정했다. 별도domain136, 실제 renderer/원본 DDS relay/observer만 사용하고 physics/policy/action/lease는 실행하지 않았다.

lazy 대조: import410.233ms, 같은 tick413.631ms. 수신 전 preload 대조: 초기화232.883ms는 callback 밖에서 수행했고 tick 최대4.719ms, health validation 최대 간격135.819ms. 각 수치는 해당 프로세스 안의 monotonic 차이다. 서로 다른 부팅의 절대 시각을 대조하지 않는다. 첫 v47 prototype의 상대 경로 오류는 ROS 자식 시작 전 실패였고 FAILED.json으로 보존했다. 재사용 probe의 accepted>50 판정은 이 자세에서 대상이 안 보이는 조건과 맞지 않아 component_result=FAIL이다. 이를 실제 대상 인식 성공으로 바꾸지 않으며 본 대조는 초기화 지연 측정에만 사용한다.

공식 Jazzy rclpy SingleThreadedExecutor 구현은 callback을 spin thread에서 실행한다. callback 안의 동기 import도 그 thread를 점유하므로 기존 원통 fit 모듈을 observer 생성 중 수신/타이머 시작 전에 준비하는 패턴을 적용한다.
https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/executors.py

1. RED: 원통 observer의 첫 frame 처리에서 모듈 초기화를 금지하는 실제 ROS fixture 시험을 작성하고 기존 lazy import의 실패를 확인한다. 원래 capture/TF/hash/receipt 검사를 재사용하고 인식 결과 자체는 별도 geometry 시험에 맡긴다.
2. GREEN: 기존 fit 함수를 observer 생성 때 준비하고 tick에서 그 함수를 호출한다. fixture 대상의 기본 경로는 유지한다. 새 executor/thread/인식 모델·기준을 도입하지 않는다.
3. REFACTOR→자체 REVIEW→관련/전체 시험→COMMIT→공개 CI 실제 runner/steps 확인. 초기화 경계와 안전·권한 불변을 검토한다.
4. 이후 관측 누락의 장시간 경계는 저장 자료 또는 별도 짧은 부품으로 조사한다. 이 변경만으로 v45/v46의 장시간 관측 만료가 해결됐다고 하지 않으며, 실제 연속 성공 전10회 평가를 재시작하지 않는다.

가이드에 필수 계측 절차를 추가하거나 범위를 늘리지 않는다. 임계값300ms/TF100ms, RPP/정책/PD/원래 정상 완주 수치는 유지한다.
