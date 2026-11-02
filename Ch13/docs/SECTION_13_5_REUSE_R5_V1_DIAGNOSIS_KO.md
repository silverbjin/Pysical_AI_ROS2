# R5 v1 실제 인수와 보완 계획

v1 고정본 여섯 시나리오를 전수 실행했다. 우회·비어 있는 목표의 도달 불가·취소·raw 손실은 PASS, 자유 이동과 비전은 FAIL이다. 모든 실행은 잔여 없이 회수됐다. [원본 결과](SECTION_13_5_REUSE_R5_V1_REPORT_KO.md)를 보존하며 기준 수치를 바꾸지 않는다.

자유 이동은 navigation boundary가 WAITING인 동안 이미 gateway를 재무장한 상태에서 raw 원본 만료가 발생했다. 출발 준비 중인 zero와 실제 제어가 시작된 상태를 같은 재무장 순서로 다룬 설계 문제다. boundary가 실제 controller/smoother 입력을 받고도 zero를 유지하는 준비 단계를 두고, fresh zero 확인→gateway 재무장→명시적 release로 순서를 바꾼다. 도달 불가가 준비 중 terminal로 끝나면 움직임을 허용하지 않는다.

비전은 Source9228 촬영이273.667wall, health 검증273.874wall이었고, 다음 유효 health9240은273.994wall로300ms 만료 이후 도착했다. 촬영 자체는 이어졌으며 큰 RGB-D를 원본→C++→hex 문자열→Python으로 중복 전달하는 경로가 남아 있다. 큰 원본 영상은 native ROS 메시지로 직접 수신하고, C++에서는 실제 GID·최초 receipt·source stamp·원본 CDR SHA256만 보내 정확히 대응하는 샘플을 결합하는 구조를 검토한다. 입력의 원본 시각과 내용 검증을 유지하며 카메라/목표 age 기준을 확대하지 않는다.

이 변경은 새 v2 source snapshot과 별도 동결본에서 검사한다. v1 FAIL을 덮어 쓰거나 통과 수치를 바꾸지 않는다. 두 수정 뒤에도 같은 실패가 남으면 전체 재실행 전에 다시 부품·구조 검토로 돌아간다.
