# Book Lab Acceptance CI

This directory implements an incremental, evidence-based check of the textbook exercise guides on the currently checked-out commit. It does not import or upgrade historical PASS states.

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
