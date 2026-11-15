# G04B 개발·분석·디버깅 Cycle 01 — 고위치 joint2 실제 명령 전달 경계

- 날짜: 2026-11-15
- Issue: #181 / Draft PR #202
- 기준 main: `9431fb535ce7a51416c19c4395fb2ba3fabdad40`
- 기준 HEAD: `304b68519bbeb5111b7a7a990e9f9ca367b2a57b`
- **상태: 시험 준비 / G04B BLOCKED (CI L2 결과를 보고서 후속 커밋에 기록)**
- 방법: Architecture-First → 기존 실패 원본 분석 → 하나의 반증 가능한 가설 → read-only 계측 + L0 → 승인형 L2 1회 → Artifact 감사 → 보고서 갱신

## 1. 기존 실패 원본(이전 실행, 새 수정의 PASS 증거 아님)

- [Run #43714625440](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/43714625440), SHA `a7ced054e024ce4eeac24584d113346cdc34b049`; 원본 Artifact #14162335655, ZIP SHA256 `433a6b3898eabd7ff4f5debb96888d01456d2ed09e3c4218cad34815744badab`.
- 실제 5관절 high MoveGroup 후 joint2 오류 0.01253rad(기준 0.01rad). 추가 직접 FJT 시 desired 0.105683816858rad, actual 0.093309155752rad, status 6/error -5. 접촉·상승·hold는 실제 성공했지만 하강·release·ROI 미실행.
- 실패한 직접 FJT 후보는 `f4f0e55a...`에서 원복. 이 사이클은 **보정/하드웨어 동작 변경 없이** 최초 제어–물리 전달 경계를 측정한다.

## 2. 단일 가설과 반증 계획

**가설:** high MoveGroup 종료 직전 joint2 오차가 남는 이유를 `JTC reference → hardware position command → ECS JointVelocityCmd → native JointPosition` 중 한 경계에서 확인할 수 있다.

예상 반증: 명령 자체 누락이라면 JTC/HW 경계, 명령이 native에 도달했는데 변위가 없다면 DART 제약/물리 경계, 실제 joint2가 이동하지만 잔차가 남으면 track/목표 종료 조건 또는 접촉 부하를 후속 검토한다. 자료 부재는 UNKNOWN이다.

## 3. 적용 코드(수정 요인: 관측 범위만)

- `ci/ch07_77_g04b_actual_physics_witness.py`: high MoveGroup 발행·결과 구간의 controller reference/feedback/error 및 hardware command 원본 보존. 실패 예외에서도 receipt 기록.
- `ci/ch07_181_rod_trace/finger_ecs_trace.cc`: 이미 `joint2` pre/post read-only 관측 구현. command/physics 변경 없음.
- `ci/ch07_181_high_joint2_native_audit.py`: 같은 sim-time 구간의 native ECS와 컨트롤러 관측을 연결. **물리 PASS 반환 금지**.
- `ci/tests/test_ch07_181_high_joint2_native_audit.py`: 명령 누락·ECS 누락·관절 미이동을 정확하게 구분하는 L0 TDD.
- 기존 G04B 진짜 양측 접촉·lift≥0.05m·hold≥1.3s·release/settled ROI와 허용오차 모두 유지.

## 4. 실험 실행·원본 결과

- **L0:** PENDING
- **L2:** NOT_RUN (자동 실행 없음, 승인형 한 번만)
- **Artifact/ZIP SHA256:** PENDING
- **실제 첫 실패 및 반증 여부:** PENDING

## 5. 교육용 회고

- 물리 실패에서 Action SUCCEEDED는 실제 관절 추종 증명이 아니다.
- 목표값 재전송은 기존 실행에서 반증됐다. 새 가설에는 관측할 신호와 반증 기준을 먼저 정의한다.
- 이미 성공한 물체 상승을 별도 실험으로 재검증하지 않고 한 번의 필요한 시나리오에서 부수적으로 재사용한다.

**남은 인수:** G04B BLOCKED, G05 NOT_RUN, Ch10 HOLD, Owner WSL2 NOT_READY. 후속 실험 없이 완료 승격하지 않는다.
