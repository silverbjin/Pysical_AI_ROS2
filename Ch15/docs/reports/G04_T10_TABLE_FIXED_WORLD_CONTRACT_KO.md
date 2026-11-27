# G04 T10 교육용 중간보고서 — 식탁 통합 절대좌표 계약 (사이클 5 사전검증)
## 1. 목표와 고정 PIN
독립 V3 GREEN 45934040387 (source 1cd16b1a66ce94fb3ef4a474c01b043a00e43112) 재사용. 실제 식탁 주변에서 원래 관측 목표를 고정한다. 실제 진입 위치로 목표를 재정의하면 XY 15mm gate가 잘못 통과할 수 있으므로 금지한다. 기존 Ch13, V3 제어기, safety gateway, 허용 오차 변경 없음.
## 2. 설계
V3 local final_target의 역변환으로 map entry를 계산한다. 반경 0.18m, 회전 1.45rad, 직선 0.20m 그대로. 초기 회전+진입 직선+곡선+최종 직선의 5mm/1deg 샘플. tangent mismatch 0.04rad 초과는 거부하는 새로운 계획 admission(완화가 아님). 실제 진입 XY 30mm/yaw 0.06rad 이내 및 성공 terminal4, active goal 없음, stationary, boundary IDLE, publisher chain valid, no fault인 경우에만 NAV2→V3 1회 인계를 허용하는 순수 상태 계약. 이 상태 계약은 실제 ROS 노드와 연동된 것은 아니다.
## 3. 실제 로컬 검증
python test_table_approach_contract.py: 5/5 PASS, 절대 목표 보존, 목표 재기준화 방지, 비정상 입력 거절, 샘플 연속성, 7가지 인계 음성조건과 재인계 거절. 코드 blob 1085a0cf61e4ad0b68b001c5cdb6ba5dbfcea439, test c3372f69dff80ae9596d67d0e0e9d6424bf4acf8. 아카이브 t10-heading-red1/2.zip 59/58 내부 SHA256 검증. 기존 level2_obstacles footprint와 world geometry, 요구 여유 .127264m 유지. 두 경우 전체 최소 .175437/.175447m, curve .184536/.184527m. 2D geometry PASS 2/2. 실제 Nav2 trajectory, 3D contact, sensor visibility, DDS, dynamic drift 증명 아님. Receipt에 source SHA 및 결과 보존. 실행 방법: python screen_fixed_world.py t10-red4.zip t10-heading-red1.zip t10-heading-red2.zip (Shapely 필요).
## 4. 남은 실제 통합 계약
Ch15 별도 launch/runner에서 Nav2 controller output만 private topic으로 분리하고 단일 multiplexer publisher가 기존 nav_cmd→velocity_smoother→NavigationBoundary→CommandGateway를 유지하도록 구현 및 검증 필요. 원본 raw/safe 직접 발행 금지. Nav2 entry FollowPath terminal/settle 증거를 확인하고 단방향 handoff; 관측 goal 고정, 실제 map 및 vision health lease, 곡선 이후/최종 실제 RGB-D, workspace IK, 원본 contact/force/time guards. 최종 XY15mm/yaw.06rad 유지. 이후 별도 BT/rosbag 및 10개 assessor 조건 검증. 현재 actual table runner NOT_IMPLEMENTED/NOT_RUN, G04 PARTIAL_PASS, 원래 CH13_NATIVE L2 RED4 FAIL, L3 NOT_RUN, main merge HOLD.
## 5. 교육 포인트
독립 실험의 좌표 기준과 실제 미션 기준은 다르다. 합성한 목표가 아닌 실제 관측 목표에 제어기를 역정렬한다. 기하학, 상태 계약, ROS publisher ownership, 실제 동역학을 다른 검수 단계로 관리한다. 성공 PIN을 반복 실행하지 않는다.
