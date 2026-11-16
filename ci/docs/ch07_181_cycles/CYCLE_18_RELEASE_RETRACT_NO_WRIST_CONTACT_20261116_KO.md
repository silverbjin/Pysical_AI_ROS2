# G04B Cycle18 — 원본 손목↔원통 낙하 충돌에 대한 동시 해제·후퇴 단일 실험
_2026-11-16 / Issue #181 / Draft PR #202 / BOOK_ROS2_DEV_DEBUG_CI_STD_V1_

## RED: 원본 실제 Gazebo 근거

- [L2 #43800612279](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43800612279) FAIL, Artifact #14196048989, ZIP SHA256 `9abea85bad69d41d9a77fafa123bd37b9c5d8b19359f43856d523e4861062f0c`. 소스 HEAD `839e44ff9e7012c21e1a8718b57a3dc13ff34637`.
- 실제 G04B 50g rod lift `0.118310m`, 1.3s hold drift `0.0008153m`; native 양손 최근 positive ECS force 38샘플씩, high→lower collision-aware MoveIt 및 실제 이동, 실제 손가락 release, 최종 settled XY `0.04244m`/height `0.028m` 모두 통과.
- **최초 독립 원본 실패:** `native_wrist_rod_contact_events=648` (70.011~70.687s) 및 최초 body1 contact force 약 `17.13N`, 따라서 전체 PASS **금지**. Wrist support collision 0건.
- 기존 pre-release native rod=(0.503606,0.238149,1.91499)m, arm q=[0.509164,-0.331197,1.049568,1.569168,-0.346061]rad. 원본 URDF `link_wrist` 0.08×0.06×0.06m, local Z+.03m 상자와 24mm×80mm 실제 rod. Rod vertical drop trajectory와 고정 손목 박스의 **보수적 충돌 영역 약 30mm 겹침** (원래 actual rod 첫 방향을 기준으로 한 넓은 AABB). 이 물리적 충돌을 raw-audit에서 무시하거나 허용오차 상향 금지.
- 새 환경/비전/ROS/TDD 전면 재실행 금지. G00~G04A NOT_RERUN, G05 NOT_RUN, Ch10 HOLD.

## Architecture / 가설 하나

동일 로봇·원본 yaw=.35 실제 solid bin, 50g rod/양손 native contact/원래 FJT/MoveIt 컨트롤러를 유지하면서 **해제 시작과 동시에 손목을 bin 바깥·상방으로 후퇴**시키면, 정적인 원통 낙하 경로와 손목이 충돌하던 구간을 물리적으로 분리할 수 있는가?

- 최초 실제 release lower arm에서 **joint3만 -0.055rad**. 원본 FK 기준 wrist 원점의 수평 후퇴 약 0.042m, 상방 약 0.034m. 조건부 **원통이 해제 위치에 그대로 있는 경우** 넓은 AABB 원통 낙하와 wrist의 SAT 분리 약 +0.012m. 기존 고정 손목에서는 약 -0.030m. 시작 위치에서 FJT 보간 17개 상태 전체 원래 link4↔bin SAT≥3mm.
- 이는 **오프라인 조건부 분리 후보**일 뿐, 실제 붙잡힌 원통의 초기 동반 이동·낙하 타이밍·충돌 성공의 증거가 아니다. 소스가 위험하면 Goal 전 중단. 기존 정적 하강 자세만 바꾸는 bounded 탐색에서 안전 분리 목표가 없었던 이유를 숨기지 않는다.

## 최소 구현과 안전 장치

1. `ci/ch07_181_release_wrist_retract.py`: 실측 lower joint+native rod+원본 PlanningScene 검증, q3만 -55mrad, 원래 bin link4 path SAT와 wrist/rod drop 보수적 static sweep. 기존 원본 bin, 로봇 충돌 형상/수용 임계치 **변경 0**.
2. `ci/tests/test_ch07_181_release_wrist_retract.py`: C17 원본 collision 및 기하 후보, 잘못된 bin/JointState/rod 입력, 물리 사칭 금지 L0.
3. Witness에서 **원본 MoveIt FCL plan_only 성공 후에만** 기존 두 ROS 2 액션 서버에 각각 별도 FJT Goal 송신: 두 손가락 release 명령값 0.0m, time_from_start 기존 2.0s, 새로운 작은 arm q3 retract (0.8s, q3만 움직이고 속도/관절 limit 검증). 각 Action handle/status/result/실제 joint feedback 기록. 실제 native 양측 contact/물체 custody/settled ROI 및 마지막 독립 `no_wrist_rod_collision_in_entire_physical_sequence` 게이트 **엄격 유지**.
4. 마지막 독립 감사 스크립트는 신규 `release_retract_from_rod` Goal을 오로지 Action 성공+실측 q error≤0.01rad로 확인한 경우에만 허용. collision=0와 모든 기존 gate가 여전히 필수. Fake attach/teleport/contact 삭제·force threshold 변경 금지.

## 검증 순서 및 판정

- L0: 집중 Python+safety+shell, 공개 CI 자동 실행 후 원본 Run ID 추가.
- L2: L0 성공 시 **새 label 이벤트 딱 1회**, 실패 시 같은 Goal 재시도 금지; 원본 100MB native contacts·ECS frame+force·joint state와 실제 settled 확인.
- G04B는 독립 감사 PASS, shutdown clean, original artifact checksum 고정, Owner WSL2 실제 인수 전까지 **BLOCKED**. 기하 후보/MoveIt plan-only/Action SUCCESS만으로 승격 불가.

**교육용 주제:** '기구학상 목표 도달'과 '낙하 물체와 손목의 시간 의존 충돌'은 다르다. 정적 충돌이 필연적이면 controller gain/speed/threshold 반복 대신, 유효한 제어권을 가진 손목 후퇴 Goal을 해제와 동기화해 한 요인으로 반증한다.
