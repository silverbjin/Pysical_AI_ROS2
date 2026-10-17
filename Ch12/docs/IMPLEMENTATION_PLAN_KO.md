# Section 12.1 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 실행 가능한 12관절 MuJoCo/Gymnasium 실습과 Gazebo 비교 검증을 제공한다.

**Architecture:** Ch12 독립 Python 패키지에서 MJCF·환경·CLI를 제공한다. Gazebo 검증은 Ch11 패키지를 별도 overlay로 빌드해 재사용한다.

**Tech Stack:** Python >=3.10, MuJoCo 3.3.7, Gymnasium 1.2.1, pytest 8.4.2, ROS 2 Jazzy, Gazebo Harmonic.

**Spec:** [승인한 설계](DESIGN_KO.md).

## Global Constraints

- 관절 순서 fr/fl/rr/rl × hip/thigh/calf, 토크 행동 12차원.
- 기본 30차원, 선택 45차원 관측. seed, terminated/truncated, 좌표계를 명시.
- 기존 Ch11 코드를 변경하지 않고 실제 두 물리 엔진의 실행 증거를 보존.
- 코드와 가이드·수정 보고서를 로컬 Git 브랜치에 커밋.

## Review Focus

- NaN·Inf·잘못된 행동 크기로 물리 상태가 오염되지 않아야 한다.
- reset 전과 에피소드 종료 후 step 사용은 명확한 오류여야 한다.
- 명명된 관절·actuator 매핑과 좌표계가 모델 배열 순서에 묵시적으로 의존하지 않아야 한다.
- CLI의 0 이하 steps와 유효하지 않은 설정값을 거부해야 한다.
- wheel 설치 후에도 MJCF 자산과 CLI를 찾을 수 있어야 한다.

## Task 1: 환경과 모델

파일: `pyproject.toml`, `src/quadruped_rl/{__init__,env}.py`, `src/quadruped_rl/models/quadruped.xml`, `tests/test_env.py`.

인터페이스: `QuadrupedEnv(observation_mode='textbook', render_mode=None, max_episode_steps=1000, frame_skip=5, target_velocity=0.5)`.

- [x] 실제 엔진을 사용하는 계약·재현성·토크·보상·종료 테스트 작성 후 실패 확인.
- [x] 12관절·free base·바닥을 가진 MJCF와 Gymnasium 환경 구현.
- [x] 테스트와 Gymnasium checker 실행. 오류 발견 시 재현 테스트 후 수정.

## Task 2: 실습 실행과 설치

파일: `src/quadruped_rl/demo.py`, `tests/test_demo.py`, `scripts/verify_mujoco.py`.

인터페이스: `quadruped-rl --steps N --policy {random,stand} --observation-mode {textbook,full} --output PATH`; 검증은 JSON 결과 및 선택 렌더 이미지를 저장.

- [x] CLI 입력 오류 및 에피소드 실행 결과 테스트 작성 후 실패 확인.
- [x] 데모와 검증 명령 구현, 무작위 정책과 PD 자세 유지 비교.
- [x] editable·wheel 설치 후 외부 디렉터리에서 실행, 실제 렌더링 검증.

## Task 3: Gazebo 실행·문서·리뷰·커밋

파일: `scripts/verify_gazebo.sh`, `docs/LAB_12_1_GUIDE_KO.md`, `docs/CHANGE_REPORT_KO.md`, `evidence/*`.

- [x] 격리 DDS/Gazebo partition에서 Ch11 빌드·회귀검사·실제 기립 프로브 실행. 이 실험의 프로세스만 종료.
- [x] 설치·관측 슬라이스·보상·종료·명령·엔진 차이·재현 방법을 가이드로 작성.
- [x] 코드 리뷰 후 중요 문제 수정 및 회귀·런타임 검증 재실행.
- [x] 실제 수치와 남은 제한을 보고서에 기록하고 diff 검사 후 커밋.
