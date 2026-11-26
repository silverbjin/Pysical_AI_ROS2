# G01 — 미션·시나리오·독립 월드
2026-11-27 KST / C01·C02, T01·T02 부분.
## 설계
원고의 RobotState/MissionContext/ErrorCode 유지, 순수 상태 전이 oracle 추가. readiness 명시, 순서 강제, terminal 재등록 금지, full 실행 거부. A mock 7 leaf, B 4개 상위 표현(실제 native owner 변경 없음). F01~F10 및 정상 설정 11개. 독립 큐브 모델과 RGB-D world 작성.
## RED / GREEN
로컬 Debian 13 / Python 3.13.5. RED: 구현 전 unittest discover exit 1, 모듈·world 부재 3 errors (0.002s). GREEN: readiness negative case 추가 후 7 unittest PASS (0.002s), schema 11개 확인. 실제 DDS/Gazebo가 아닌 순수 Python/XML 시험. C의 실행 금지, 초기 상태, ID 재사용, readiness, 잘못된 battery, negative budget/profile, cube 크기/관성/높이/센서 검수. T02 native gz sdf validator NOT_RUN; actual RGB-D T11 NOT_RUN. negative geometry mutation 및 실제 3.12 CI 후속.
## REVIEW
기존 Ch01~14 변경 없음, 외부 자산 미복제, 원고 파일 게시 안 함. MissionRegistry는 G01 교육 oracle이며 G03 actual executor/UUID/cancel을 대체하지 않는다. 코드 단위 보고서와 테스트 함께 커밋. 패키지 설치 등록은 후속 G02/G04, 원샷 출고 금지.
## 판정
T01 scoped static; T02 XML/geometry scoped static. G01 SCOPED_LOCAL_L0; 완전 T02/Ubuntu CI 미확정. G00 physical assets/rights/closure 여전히 BLOCKED. 동일 실패 반복 금지. 다음 G02 ICD 실제 ROS DDS 개발은 target preflight 확인 후.
