# v46 관측 만료 경계 진단 명세

정상 완주 기준과 Owner 인수 보류를 유지한다. v45는 실제 이동/대상 확인을 통과했으나 팔 준비 중 340.476ms 관측 만료로 중단했다. v42의15Hz 실패도 보존하므로 처리율만 바꿔 재시도하지 않는다.

공식 Jazzy rclpy executor 원본은 SingleThreadedExecutor가 spin을 호출한 한 thread에서 callback을 수행함을 보여 준다: https://github.com/ros2/rclpy/blob/jazzy/rclpy/rclpy/executors.py . 이 원본을 참고해 기존 executor를 바꾸기 전에 callback 시작/끝을 계측한다. 문서가 특정 callback 정체의 실제 원인 증거는 아니다.

1. RED: 제한된 callback 계측의 반환/예외 보존, 상한 보존, 꺼짐 상태에서 무계측을 시험한다.
2. GREEN: 개발용 opt-in CH13_CALLBACK_TIMING=1에서만 platform monitor·manipulation monitor·action monitor·관측 packet callback의 monotonic 시작/끝/thread CPU를 최대4096건 저장한다. 메시지·receipt·stamp·callback 순서·lock·executor·수명·정책은 바꾸지 않는다. 종료 JSON에 계측을 남긴다.
3. REFACTOR/자체 REVIEW/전체 부품 시험/COMMIT/공개 CI의 실제 steps 확인을 수행한다.
4. v46 소스 동결 후 v45와 같은10Hz/overlap1/전진DUBIN+RPP 조건의 단일 계측 실행을 한다. 원본 FAULT·capture/receipt/inference·callback·graph 조회 구간을 같은 monotonic 축으로 대조한다. 관측 수명 완화와 executor 재구성은 진단 결과와 별도 회귀 근거 전까지 금지한다.
5. 첫 실패와 종료·잔여·압축 증거를 기록한다. 정상 완주 전에10회 평가를 시작하거나 인수 완료로 바꾸지 않는다.

이 작업은 반복 장애의 원인을 구분하는 제한된 진단이다. 새 제어기나 도서 기본 필수 절차를 추가하지 않으며 계측 기본값은 꺼짐이다.
