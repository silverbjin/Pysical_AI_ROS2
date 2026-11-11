# v38 L2 survey deadline 원인 분리

2026-11-11. 단계2 저장 증거 조사. v37 UUID7fdc7295-bcb1-44a2-85c2-7cd7902ea161의 원본 판정은 유지한다.

launch는 survey_checker 플러그인 생성을 확인한다. timeout 직전 navigation_last는 ACTIVE/fault빈값, gateway와 platform은 ARMED/fault빈값이었다. 최초 FAULT가 아니라120wall초 survey 대기 만료 뒤 Action cancel/idle로 종료된 사례다. 마지막 live_status FAULT만으로 선행 안전 고장이라고 해석하면 안 된다. 두 Action 서버의 취소 로그는 후행 종료다.

목표는(1.9,.3,yaw.566729rad)다. 실제 raw를 재계산하면60mm 범위 최초 진입은40.760sim/wall2798.574879초, XY59.837mm/yaw1.766122rad로 방향오차1.199393rad였다. 마지막44.860sim에서XY54.213mm/방향오차.906348rad다. XY 안에서 관측된 최소 방향오차도.906312rad로.06rad 조건을 충족하지 못했다. 최종 gateway 원본 입력은44.298sim초에vx0/wz-.1이며 진행은 계속됐다.

실제 위치/yaw 표본:10sim(.526,-.332,-.586),20sim(1.237,-.561,.215),30sim(1.747,-.209,.963),35sim(1.922,.156,1.353),40sim(1.933,.243,1.715). 최종 관측 지점까지의 우회 경로와 회전 비용이 고정120wall초를 소진했다. 따라서 다시 XY 허용값을 늘려도 방향오차를 설명하지 못한다. 마지막 인정 RGB-D는35.756sim초라서 방향을 무시하고 현재 위치에서 성공 처리할 근거도 없다.

후속 최소 대조는 실제 경로에서 이미 지났고 target RGB-D를 관측하던 이전 지점을 중간 관측 후보로 삼는 것이다. 예를 들어30sim 부근을 후보로 검토하되 실제 footprint/계획 경로·원통 RGB-D fit·종료 후 fresh 관측을 먼저 검사한다. 후보 검증 전 Scenario나timeout/yaw를 변경하지 않았다. 경로 비용·관측 가시성을 함께 통과한 후보만 별도 source/scenario hash로 구현한다. 명세 단계2는 조사 완료/보완 구현·실제 gate 미완료다.
