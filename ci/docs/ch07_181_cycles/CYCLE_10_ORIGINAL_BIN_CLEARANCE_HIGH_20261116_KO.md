# G04B Cycle10 — 원본 bin 충돌 상자에 대한 고위치 목표 자세 재설계
_2026-11-16 / Issue #181 / Draft #202_

## RED / 원본

직전 승인형 실제 Gazebo [#43781963845](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43781963845), Artifact **#14188569056** (ZIP sha256 `076bf90754e09a7a39dd3d23672681ceb191b43130ed8083a6bab46b15d0e87c`): 50g rod **실제 상승 0.14509m**, hold drift **0.00077469m**, 실제 static bin을 적용한 MoveIt 고위치 자세는 원본 0.5m `link4`와 **충돌**하여 plan_only ABORTED. 원래 +elbow 및 Cycle09 -elbow 모두 high real Goal 이전에 차단. 하강·해제·정착 NOT_RUN.

## 한 가설 / 변경 한 가지

다른 솔버/속도/충돌 물체/ROI 허용오차를 건드리지 않고, **high 단계의 목표 관절 자세만** 바꾼다. 기존 Xacro link4 박스 0.05×0.05×0.5m, 원본 Gazebo bin 박스 0.30×0.30×0.20m at (0.55,0.25,1.63)m와 test-only fixed-base world 변환을 정확히 계산한다. 실제 held 50g rod offset을 반영하는 결정론적 제한 탐색으로 원래 bin 내 high XY≤0.025m·height≥1.98m·world jaw drift≤0.25rad를 만족하는 후보를 찾는다.

## 코드/불변식

- `ci/ch07_181_clearance_verified_high.py`: 3D OBB SAT; 충돌 상자는 전혀 변경하지 않음. SAT 분리는 **후보만** 의미하며 MoveIt/FCL 또는 물리 PASS 증거가 아님.
- `ci/tests/test_ch07_181_clearance_verified_high.py`: 이전 양/음 팔꿈치 목표의 실제 상자 교차와 raw held offset 신규 후보, scene/bin 조작·NaN·물체 미파지 방지.
- `ci/ch07_77_g04b_actual_physics_witness.py`: **명시적 C10 flag**일 때만 후보 목표를 적용. 반드시 실제 MoveIt `plan_only` 통과 후에만 real high goal.
- 고정 Docker digest, original Gazebo bin/URDF/solver/contacts/Goal tolerance/lift·hold·release·settled ROI 게이트 모두 보존. Fake attach, rod pose overwrite, collision disable 없음.

## 검증·회고

L0와 승인형 L2 Run/Artifact는 뒤이어 원본 조회 후 이 문서에 기록한다. 후보 탐색의 기구학적 수치만으로 **G04B PASS 불가**.

교육 포인트: 원래 구조의 OBB와 실제 월드 장애물의 3D 교차를 검증한 뒤 목표 *자세*를 수정한다. 물리 충돌을 무시한 MotionPlanner 재시도는 문제를 은폐할 뿐이다.

**G00~G04A NOT_RERUN / G04B BLOCKED / G05 NOT_RUN / Ch10 HOLD / Owner WSL2 NOT_READY**.
