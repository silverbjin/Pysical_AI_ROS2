# 15.1 미션 요구사항
- A mock: readiness 후 navigate/detect/approach_stand/pick_retract/return_home/place/verify_finish; terminal 1회, 물리 전체 성공 false.
- B physical_basic: 기존 Ch13 owner가 이동·관측·정착·정상 종료 수행. 신규 mock tree에서의 단계명은 대응 설명일 뿐 native 명령 아님. 원통 20g 기존 fixture, pick/return/place 요청 금지.
- C physical_full: 예약 이름, 실행 거부.
- 독립 Gazebo 월드: 5cm red cube, 0.1kg, 탁자 상면 0.20m, 중심 z=0.225m. RGB-D 5Hz 설계. 실제 센서/GT/TF 검수 G04.
- F01~F10 및 정상 fixture는 JSON-compatible YAML, 실행 fault 주입/복구는 G08; F03 정상 복구와 지속 실패의 실행 variant는 후속 구현.
- 원고 전체 물리 KPI는 설계 목표. 기존 Ch13 guard 및 정책 수치 변경 금지.
