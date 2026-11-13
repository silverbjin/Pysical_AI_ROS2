# Ch09 §9.8 — 네 발 원본 Gazebo 실제 지면 접촉력 검수 (Issue #165)

> 검수 시점: 2026-11-14 KST. **실제 Gazebo Contact 시스템의 4족–지면 접촉 이벤트 SCOPED PASS**. 이 문서는 기존 Ch09 §9.6 안정 기립, §9.7 관절 사인파, §9.8 TF 성공을 재판정하지 않는다. **Ch10 Issue #123 HOLD**.

## 1. 검증 범위와 변경되지 않은 원본

기존 [실제 기립 성공 CI #43244795784](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43244795784)와 [Artifact #13955504103](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43244795784/artifacts/13955504103)는 원본 `stand_up`의 안정된 자세(최대 roll/pitch 0.463056°, base z 0.423204m, 직전 창 XY drift 0.000181m)를 증명하지만 **실제 발–지면 힘을 측정하지 않았다**. 네 발의 충돌과 접촉이 물리적으로 일어났는지는 별도 시험이 필요했다.

이번 시험에서도 Ch09 `robot.urdf.xacro`, `stand_up.py`의 6초 smoothstep, ROS 조인트 토픽, 12개 위치제어기 및 PID, 원본 world `empty_world.sdf`의 마찰·중력 조건은 **바꾸지 않았다**. 생성한 원본 URDF의 네 발 충돌 링크가 각각 하나씩 존재함을 확인했다. 원본 발별 Gazebo 태그 `mu1=mu2=1.0`, 월드 ground의 `mu=mu2=1.0`은 **설정된 값일 뿐 실제 측정한 마찰계수가 아니다**.

변경은 임시 SDF 월드 사본에 `gz-sim-contact-system`과 `ground_plane/link/collision`의 접촉 센서 한 개를 추가한 것뿐이다. Gazebo의 실제 발 충돌은 고정 관절 lumping 때문에 `fr_calf_link_fixed_joint_lump__fr_foot_collision_1` 같은 이름으로 표시될 수 있으므로, 네 발별 충돌 이름을 독립 추적했다.

## 2. RED→GREEN 과정 및 증거

첫 [공개 CI #43477270491](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43477270491), [Artifact #14063418076](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43477270491/artifacts/14063418076)는 Gazebo 실제 로봇 spawn과 Contact 시스템 로딩까지 성공했지만, 새 시험 래퍼의 `/joint_states` 타입 탐색 시점이 너무 빨랐고 Bash cleanup의 `local rc` 참조 순서 오류로 센서 읽기 전에 **FAIL**이었다. 실패를 접촉력 없음이나 기존 기립 결함으로 취급하지 않았다.

최소 개선: `/joint_states sensor_msgs/msg/JointState`의 readiness를 bounded 반복으로 확인, native Gazebo Contact가 실제 생성한
`/world/my_empty_world/model/ground_plane/link/link/sensor/book_ch09_ground_contact/contact`
토픽을 확인, 함수 내부 `rc` 변수 초기화 순서를 수정했다. 카메라·Ch10·기존 기립·관절/TF의 성공 시험은 재실행하지 않았다.

**변경된 시험의 성공 증거**

- [공개 GitHub Actions #43477731785](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43477731785) **SUCCESS**
- [원본 Artifact #14064470470](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43477731785/artifacts/14064470470) ZIP SHA256 **`e97f470ce931d4bf71eb63f9261db06b57c4b5c64c5acd9bd67d90ef678a979c`**, GitHub Actions 업로드 로그 SHA와 일치. 원본 ZIP의 29개 항목, `ground_contacts_raw.txt`(19,551,910B), `contacts_receipt.json`, `result.json`, `stages.log`, `stand_up.log` 및 원본 소스/월드 blob을 보존.
- 실제 소스 체크아웃 SHA **`bc11adec6cf08671ca22c123ad6c475b84359029`**(GitHub PR synthetic merge); 해당 실측 PR HEAD는 **`5aa46abfc7fd448ab1ade11aaad0f19992709270`**. 원본 GHCR digest `sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f` 재사용.
- 원본 6초 `STAND_UP_MEASURED_START_RAMP_6S` 및 `STAND_UP_RAMP_COMPLETE_ORIGINAL_GOALS` 이후에만 contact capture. Gazebo sim stamp **12.400–19.286초**, 총 **27,548 실제 접촉 블록**, 각 발 **6,887**.
- 최종 `result.json`: `status=PASS`, `exit_code=0`, `shutdown=OWNED_GROUPS_EXITED_NO_SIGKILL`; 실제 Gazebo 및 원본 stand/bridge는 SIGINT 종료, SIGKILL 없음.

## 3. 실제 발별 접촉력과 접촉점 위치 (원본 메시지 사후 분석)

Gazebo `gz.msgs.Contacts` 메시지의 collision1/2 실제 쌍을 기반으로 발별 분리했다. 네 발의 접촉 기록 전부에 유효한 force 블록이 존재한다. **지면 collision의 `body_1_wrench.force.z`**는 모두 양수이다.

| 발(foot) | 실제 접촉 건수 | 평균 수직 Fz (N) | 최대 수직 Fz (N) | 접촉점 XY 시작→끝 거리 (m) |
|---|---:|---:|---:|---:|
| fr_foot | 6,887 | 23.926225 | 23.986395 | 0.000011420 |
| fl_foot | 6,887 | 23.928239 | 23.988292 | 0.000011415 |
| rr_foot | 6,887 | 34.873581 | 34.951067 | 0.000012183 |
| rl_foot | 6,887 | 34.872549 | 34.950054 | 0.000012178 |

합산 평균 수직 힘 **117.600594N**, 원본 질량 12.0kg × 중력가속도 9.8m/s² = **117.6N**과 부합한다. 앞/뒤가 같은 하중을 받는다는 가정은 하지 않으며, 실제 관찰은 앞발 각각 약 23.93N, 뒷발 각각 약 34.87N이다.

위 표의 XY 이동은 **원본 Artifact를 다시 파싱한 오프라인 결과**이다. 새 Gazebo 시험을 재실행한 것이 아니다. protobuf 텍스트에서 위치 `z: 0`은 생략되므로 x/y가 유효하면 접촉점 위치로 분석했다. 첫 독립 CI 수신기 `ci/docker/ch09_165_verify_ground_contacts.py`는 세 좌표값이 모두 명시돼야 위치가 있다고 해석하여 `sample_points=[]` / `contact_xy_extents_diagonal_m=null`을 기록했으나, contact/force 성공 판정은 올바르다. 이 차이를 숨기거나 CI가 XY 슬립까지 검수했다고 주장하지 않는다.

원본 표본 재확인을 위한 오프라인 개념식(각 발에 연결된 접촉점 `x(t),y(t)`에 적용):

~~~python
from math import hypot
# 동일 발에 속한 Gazebo Contacts 위치 표본을 원본 Raw 텍스트에서 읽는다.
# 주의: protobuf text의 z=0은 생략될 수 있다.
xy_start = (points[0]["x"], points[0]["y"])
xy_end = (points[-1]["x"], points[-1]["y"])
contact_xy_displacement = hypot(xy_end[0] - xy_start[0],
                                xy_end[1] - xy_start[1])
~~~

**이 값은 실제 발 링크의 slip velocity가 아니라 접촉점 위치의 단시간 변화 proxy**이다. 접촉점의 해상도, 충돌 반복, 센서/solver 특성에 영향을 받을 수 있으므로 '완전한 무슬립'이나 '마찰 계수 실측' 판정을 내리지 않는다.

## 4. 검증 판정과 남은 경계

- **SCOPED PASS:** 원본 Ch09 12관절 로봇이 기립을 완료한 뒤, 실제 Gazebo 지면–네 발 충돌/비영점 수직 접촉력 4개가 각각 다수 수신됨. 시뮬레이션 시각과 raw 충돌 쌍이 맞고, 실제 종료 rc0/SIGKILL 없음.
- **기존 PASS 보존:** §9.6 원본 기립 자세/드리프트, §9.7 단일 다리 명령/관절 측정, §9.8 ROS TF/clock. 새 시험에서 그 결과들을 재승격하거나 3회 반복하지 않았다.
- **NOT_RUN:** 직접 정지/운동 마찰계수 측정, 접촉점 속도 기반 동적 슬립과 traction 한계, 다른 지형·가속/제동, 3회 cold-start, GUI/WSLg, 실물 로봇 및 Ch10 Issue #123(계속 HOLD).
- **전체 Ch09 및 101개 교재 LAB 인수는 완료되지 않았다.** 추가 동역학/슬립 검수는 새로운 범위에서 수행하며 기존 성공한 접촉 시험을 무의미하게 반복하지 않는다.

### 실행 및 출처
- 시험 단독 실행기: `ci/docker/ch09_165_contacts_once.sh` (ROS_DOMAIN_ID=95, 고유 GZ_PARTITION)
- 테스트 임시 월드: `ci/docker/ch09_165_instrument_ground_contacts.py`
- 네 발 실제 충돌·힘 관측: `ci/docker/ch09_165_verify_ground_contacts.py`
- 전용 공개 workflow: `.github/workflows/book-ch09-165-ground-contacts.yml`
