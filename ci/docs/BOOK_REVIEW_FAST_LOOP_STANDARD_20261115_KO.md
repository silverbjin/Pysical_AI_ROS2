# 도서 코드 검수 Fast Loop 표준 — Architecture-First + 선택적 TDD + 가설 기반 Gazebo
_2026-11-15 / Issue #118, #173, #181 / 승인 전 프로세스 제안_

## 목표 및 불변식

이 문서는 **도서 부록 재현성 검수**의 개발시간을 줄이되 물리적 인수 기준을 느슨하게 하지 않는 표준이다. 새로운 PR마다 전체 Gazebo를 실행하는 대신, (P0) 설계/좌표/판정기 → (P1) 재사용 런타임 → (P2) 한 가설과 정보량 높은 시험 → (P3) 단일 작업 PR → (P4) 도서 검수와 연구성 물리 인수의 상태 분리를 적용한다.

- 기준 저장소 `silverbjin/Pysical_AI_ROS2`, 기준 `main`은 반드시 작업 착수 시 원격 HEAD를 다시 조회한다. SHA가 다른 CI 증거는 동일 시험으로 묶지 않는다.
- **G00–G04A 이미 검증된 성공은 NOT_RERUN**, **G04B=BLOCKED**, **G05=NOT_RUN**, **Ch10=HOLD**. 새 코드로 성공 판정을 승격하지 않는다.
- 실제 Gazebo/ROS 2 Goal을 수반하는 시험은 Public CI에서 **명시적으로 승인된 단 한 번의 가설 시험** 이후, raw 증거 원본을 별도 감사한다. Owner WSL2는 최종 인수만 수행한다.
- 유지할 증거: source SHA, container SHA256 digest, 실제 `/joint_states`와 FollowJointTrajectory reference/feedback/error, `/clock`, native Gazebo model/link world pose, 실제 collision geometry, 시간 동기화된 native contacts, dynamic rod lift/hold, 최종 정착 ROI 및 해제. Action SUCCEEDED, positive contact force 및 motion planning SUCCESS만으로 물리 PASS를 판정하지 않는다.
- 가짜 접촉·물체 강제 부착·텔레포트·판정 임계치 변경은 금지한다.

## P0 — 실험 전에 아키텍처와 판정기를 검증

1. 원본 URDF/Xacro의 `world → base_link` 고정 조건과 시험용 SDF의 실제 변환 결과를 비교한다. **원본 Ch07 로봇은 world_to_base_joint가 주석 처리**되어 있다. 이것을 확인하기 전까지 솔버와 접촉력을 만지지 않는다.
2. `T_world_finger = T_world_model × T_model_finger` (회전 포함)를 충돌 형상까지 적용한다. SceneBroadcaster의 model-relative link Pose를 world Pose로 직접 비교하면 오판한다. `gz::sim::worldPose`와 직접 ECS 컴포넌트의 의미를 구분한다.
3. 판정기의 실패 여부를 기존 원본 Artifact에서 재현한다. 판정기가 틀린 경우 **물리 시험 재실행 대신 offline oracle 수정**을 먼저 수행한다.
4. 물리적 첫 실패가 finger FJT의 2mm 이동인지, lift/hold인지, high carry인지, ROI인지 확인하여 뒤 단계는 실행하지 않는다.

## P1 — 설치 및 빌드 비용 분리

- G04B의 고정 `ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f`은 현재 재사용하고 있지만 실제 실행 스크립트에서 MoveIt/Gazebo 개발 의존성 apt 설치를 매번 수행한다.
- 별도 `Dockerfile`에서 실험 의존성만 미리 포함한 이미지를 **한 번 빌드·게시·digest 검증**한 뒤 새 digest를 CI와 Owner에서 공통 사용한다. 이미지 내용이 확정되기 전에는 새 digest를 추측하거나 기존 런타임을 전환하지 않는다.
- 로봇 workspace colcon 빌드는 빌드키 `(소스 SHA, ROS distro, 이미지 digest)`가 일치할 때만 캐시한다. 다른 SHA의 install/overlay 사용 금지.
- 구성만 바꾸는 L0/L1에서는 Docker pull, apt, Gazebo, MoveGroup를 시작하지 않는다.

## P2 — 시험을 원인 가설에 맞춰 선택

| 레벨 | 진입 조건 | 실행 | 판정 |
|---|---|---|---|
| **L0** | 매 관련 파일 변경 | `bash -n`, `python -m unittest` 대상 테스트만, YAML/URDF/SDF 불변식 | 사전검증 PASS ≠ 실제 물리 PASS |
| **L1** | ROS 인터페이스/JTC 코드 변경 | 대상 노드와 `/joint_states`, FJT 계약의 최소 통합시험 | 독립 피드백 판정 |
| **L2** | 원본 증거로 미확인 경계 + 단일 가설 + L0/L1 통과 | **실제 Gazebo CI 1회** 및 raw Artifact | G04B 물리 판정; FAIL 원본 그대로 |
| **L3** | L2의 native geometry·contact·ROI 등 해당 전항목 PASS | 전체 통합 Pick-and-Place | 이전 성공 근거와 SHA 관계 기록 |
| **Owner** | L3 검수 뒤 | WSL2 마지막 검수 | 현장 승인 전 임의 승격 금지 |

**한 가설 = 변경 요인 하나 = 예상되는 관측값 한 개 이상의 명시적 예측 = 원본 증거와 비교**. 새 정보 없이 같은 실패를 두 번 관찰하면 새로운 Gazebo 호출을 멈추고 설계/판정기/계측 방법을 재검토한다. 속도·솔버·FCL 등 무관한 요인 스윕 금지.

## P3 — 기존 소스 관리의 통합

- **하나의 미해결 이슈 → 하나의 활성 작업 PR**. 진단 결과는 원칙적으로 해당 PR과 Issue #181 원본 증거 링크에 기록한다.
- #180~#202의 기존 Draft는 사용자 승인 전 병합/삭제/닫지 않는다. 기존 증거 SHA의 관계를 바꾸는 강제 push도 하지 않는다.
- 새 진단마다 Draft PR을 만들지 않는다. 한 PR 안에서 `cause → patch → relevant unit test → one CI → receipt`를 기록하고, 동일 실패 경계에 대한 중간 계측만 변경한다.
- 목표는 코드 변경의 양이 아니라 원인/관측 정보의 증가다.

## P4 — 도서 부록 범위와 연구성 물리 인수 구분

- **BOOK_LAB_REPRODUCED**: 본문의 명령·환경·관찰을 재현한 절. ROS 메시지와 기본 동작을 확인했다는 뜻이며 물리 Pick-and-Place 완료가 아니다.
- **G04B_PHYSICAL_BLOCKED**: 실제 native world-frame contact, lifting, holding, carrying, release, final ROI 중 미충족 항목 존재. 절 전체를 물리 완성으로 표시하지 않는다.
- **G05_NOT_RUN**: 같은 실행의 실제 RGB-D→MoveIt→물리 파지 통합은 미수행.
- **CH10_HOLD**: 명시적인 보류 상태. 범위 확대 또는 우회 PASS 금지.
- **FUTURE_RESEARCH**: 솔버/마찰/접촉력 연구나 반복 신뢰성 검증. 도서 핵심 부록 인수와 구분하여 별도 개선 과제로 관리한다.

## 첫 적용과 최종 결과 기록법

1. 일반 `Book Lab Acceptance`의 자동 PR 경로를 도서·문서·검수 스크립트로 좁힌다. `ci/tests/**`나 `Ch[0-1][0-9]/**` 전체 트리거 금지. 예외적으로 `workflow_dispatch`의 기존 Ch02/Ch12 파일럿은 유지한다.
2. 문서 검사에서는 `test_check_guides.py`, `test_book_acceptance_matrix.py`와 정책 불변식 검증만 실행한다. `test_ch07_77_target_gate.py` 등 ROS 경로 테스트는 대상 워크플로가 소유한다.
3. G04B 활성 PR #202는 동일한 물리 워크플로에서도 **PR 변경 시 L0만 자동**, 실제 Gazebo는 명시적 수동 선택으로 분리한다. 물리 평가와 원본 Artifact는 해당 이슈에 연결한다.
4. 기존 #202 Artifact `14154511511`은 2mm FJT 초기 단계 finger1 응답 없음(반대쪽은 2mm): `G04B_BLOCKED`. 베이스 고정 성공이나 물체 배치 성공으로 승격하지 않는다.
5. 측정할 생산성 지표: `(a) 최초 실패까지 시간 (b) CI 실행 준비시간 / 실제 계측시간 (c) 같은 실패 재시험 횟수 (d) 1 Run당 새 검증 근거`. 정식 기능 성공률을 오염시키는 단순 CI green은 금지.

현재 문서의 지침 채택과 전체 프로젝트 물리 성공은 별개다. **원격 실제 Gazebo 검증 없이 G04B PASS 선언 금지**.
