# v38 L3 저장 경로 조사와 최소 보완

2026-11-11. 명세 e6190f9d의 단계1. v37 실제 실패 원본은 변경하지 않았다.

실제 ValidateSolution은 후보0의616/617(전체1682)에서 table_leg_0↔link6, 후보1의973~977와1402~1408(전체1461)에서 같은 식탁 다리 충돌과 pick_target↔link7 충돌을 보고했다. 정확한 index를 실제 MoveIt GetStateValidity에 재생해 모두 재현했다. link3 padding .03/0의 결과는 같았다. 침투 깊이는 대략18μm~.83mm였고, .03m 링크 여유가 새 충돌을 만든 것으로 해석하지 않는다.

최초20표본 간격 재생에서는 짧은 충돌 구간을 놓쳤다. 이를 실제 장면 불일치로 단정하지 않고 원래 실패 index를 검사해 수정했다. 전체 경로 안전을 성긴 표본으로 증명할 수 없다는 진단 도구 한계다.

공식 MoveIt [시간 매개변수화 문서](https://moveit.picknik.ai/humble/doc/examples/time_parameterization/time_parameterization_tutorial.html)는 TOTG가 관절 공간 허용 편차 내에서 경로를 변경하므로 추가 충돌 검사가 필요하다고 설명한다. 설치된2.12.4의 실제 pipeline은 AddTimeOptimalParameterization 뒤 ValidateSolution이며 이 검증은 유지한다. 저장 시작→동일 끝 joint goal 대조에서 path_tolerance .001은2/2 error1, 기본 .1은1/2 error1·1/2 error99999였다. OMPL 재계획은 확률적이므로 동일 원래 기하 경로에 대한 TOTG 전후 인과 비교나 반복 강건성 증거는 아니다.

Ruling: L3에만 ompl.path_tolerance=.001을 적용한다. 작은 부품의 좁은 경로에서 기본 .1rad 블렌딩을 제한하되 전체 충돌 판정은 그대로 둔다. 이는 실제 파지 해결 선언이 아니며, 새 실제 gate에서 확인해야 한다. 다른 시나리오·물리 안전·joint limits·link3 여유는 유지한다. 적용 경계 시험4 RED/2.79초→관련15 PASS/4.07초(443 deselected).

진단 결과는 evidence/section_13_8_repair/v38_l3_exact_indices, v38_l3_small_blend, v38_l3_default_blend의 diagnosis.json에 있다. 세 진단은 engine/actuator goal 없이 별도ROS domain136에서 실행했고 planner shutdown ACK/exit0이었다. 다음은 L2 조사 후 전체 회귀·새 동결·실제 연결 gate이며 현재 단계1의 실제 기능 확인은 미완료다.
