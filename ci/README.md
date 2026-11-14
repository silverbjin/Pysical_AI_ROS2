# Book Lab Acceptance CI

This directory implements an incremental, evidence-based check of the textbook exercise guides on the currently checked-out commit. It does not import or upgrade historical PASS states.

## 2026-11-14 도서 코드 검수 / 출판 범위 인수 (Issue #118)

**최근 인수 점검은 `101개 가이드 존재·링크 정상`과 `101개 동작 PASS`를 분리합니다.** 이 저장소는 현재 후자를 달성했다고 주장하지 않습니다. 최신 분류는 번호가 있는 **98개 절**, 추가 보조 가이드 **3개**로 실제 문서 합계 **101개**입니다.

- `ci/book_acceptance_evidence.json`: 과거 성공한 원본 CI/Artifact 및 frozen native source evidence만 연결. 성공하지 않은 실습은 `SCOPED_PASS`로 임의 승격 금지.
- `ci/book_acceptance_matrix.py`: **ROS/Gazebo/MuJoCo를 실행하지 않는 L0 증거 연결기**. `ci-results/book-101-matrix/acceptance_matrix.csv`, `acceptance_matrix.json`, `SUMMARY.md`를 출력.
- `ci/BOOK_101_PUBLICATION_SCOPE_CLOSEOUT_20261114_KO.md`: 출판용 범위 한정 인수·미완료·현장 GUI/WSL2 Owner 항목과 Ch10 HOLD 정책.
- 실제 일부 성공 원본을 재실행하지 않고 Ch04 §4.3/4.4 real TF, Ch05 §5.6 real Gazebo wave, Ch08 §8.8 offline guard와 Ch12·Ch13 native 역사적 receipt를 연결.
- **Ch07 §7.7** 원본 미션 목표 단절 `BLOCKED`; **Ch08 §8.7** 원본 PPO 10회 목표 성공 0/10 `PERFORMANCE_FAIL`; **Ch11 §11.7** 원본 SaveMap service FAIL / 별도 공식 Nav2 CLI 저장 PASS; **Ch10 #123 HOLD**. 전체 101/101 동작 인수는 허용하지 않는다.

CI 공개 워크플로 `Book Lab Acceptance`의 기본 PR 경로에서 실습 대상 변경에 대해 L0 매트릭스를 만들며, 예전 Ch02·Ch12 파일럿 ROS/물리 잡은 요청하지 않으면 실행하지 않습니다. 원본 GitHub Actions Artifact가 남아 있는 섹션은 다시 Gazebo를 구동하지 말고 읽기 전용으로 대조하세요. 수동 WSLg/실기 기능은 별도 인수합니다.

## Current coverage

- **L0 / all 13 chapters**: Markdown guide inventory, missing required LAB documents, relative Markdown links, and fenced-code syntax. Outputs JSON, JUnit XML, and a Markdown summary. No ROS, Gazebo or MuJoCo runs in this level.
- **L1 / Ch02 2.6 pilot**: Published rosdep and colcon build, interface discovery, Action Server and CLI goal/feedback/success result. Rejection, cancellation, GUI, and other Ch02 sections are NOT_RUN.
- **L1 / Ch12 12.3 pilot**: Published package installation, MuJoCo physical/reward tests, and stand/random CLI smoke. Viewer, PPO training, long-horizon locomotion and other Ch12 sections are NOT_RUN.
- **L2**: Gazebo, MoveIt, full interactive GUI and Ch13 third-party assets are NOT_RUN.

Passing a pilot is **not** chapter completion. Artifacts contain the exact checkout SHA and bounded scope. Runtime jobs use a 20-minute per-lab timeout and upload logs even on failure.

## How to run

On pull requests touching this CI or chapter source, the document check and both pilots run. After the workflow is on main, use Actions > Book Lab Acceptance > Run workflow.

- Chapter all / level preflight: document audit for Ch01 through Ch13.
- Chapter Ch02 / level pilot: document audit for Ch02 plus section 2.6 runtime.
- Chapter Ch12 / level pilot: document audit for Ch12 plus section 12.3 runtime.
- Chapter all / level pilot: all-document audit plus BOTH pilots, not full chapter acceptance.
- Selecting another chapter at level pilot performs L0 only; its runtime is NOT_RUN.

Do not edit guide commands silently to pass CI. If a guide contradicts the current source, report the difference as a guide defect and separately patch the relevant chapter.

## Expansion plan

1. Fix failed L0 broken links and inventory defects, preserving source evidence.
2. Expand the manifest to each numbered guide with command source, readiness, assertion, shutdown and output contracts.
3. Add Ch01–Ch11 ROS/Gazebo runtime only after a controlled ROS Jazzy/Gazebo Harmonic container image is built and pinned by sha256. Distinguish headless CI from GUI/manual WSL2 acceptance.
4. Add Ch13 basic navigation-observation scope only with third-party source and model manifests, isolated engine ownership, and safety cleanup; do not claim full grasp/transport completion.
5. When repeating checks, rerun affected failures only and preserve prior artifacts.

Outputs: ci-results/docs/{results.json,junit.xml,SUMMARY.md} and ci-results/ChXX/section/{run.log,result.json,SUMMARY.md,...}.
