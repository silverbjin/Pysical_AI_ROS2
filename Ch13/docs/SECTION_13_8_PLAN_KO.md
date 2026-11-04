# 13.8 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. 단일 작업자; 사용자의 추가 질문 없이 진행 지시를 따른다.

**Goal:** 13.8 전체 원고의 연속 임무와 계측·기록·평가를 단계적으로 개발한다.

**Architecture:** 13.7 BT 및 기존 같은-engine worker를 재사용한다. 계측·판정과 opt-in 운반 권한은 새 패키지에 둔다.

**Tech Stack:** ROS 2 Jazzy, MoveIt 2.12.4, rosbag2 0.26.11, MuJoCo 3.13.0, py_trees_ros 2.6.0.

**Spec:** SECTION_13_8_DESIGN_KO.md

## Global Constraints

sources/·Ch01~12·외부 모델·기존 증거는 수정하지 않는다. 0.5N·0.05rad/s·0.1rad/s²·300ms 관측·100ms TF 수명을 유지한다. 한 engine만 실행하고 engine 중 build/pytest를 하지 않는다. 새 build /home/jinho/ch13_reuse_13_8_build. 공유 lock work/ch13_reuse_engine.lock. 원격 push/merge 없음.

## Review Focus

중복/누락 시도와 NaN의 거짓 성공; CPU 정규화 및 sim/wall 혼동; 새 goal 예약과 관측 소유권; 운반 중 접촉 상실과 취소; bag 재생의 live 권한 획득을 검토한다.

### Task 1: 격리와 정량 판정

Files: 새 ch13_system_validation/{metrics,tools}.py 및 test/test_metrics.py, test/test_tools.py; scripts/reuse_13_8/{env,build}.sh.

Interfaces: assess_trials(trials, expected=10) -> dict; validate_build(value) -> Path. 이후 runner의 UUID·complete·success·sim_s·wall_s·position_error_m·max_tilt_rad·cpu_percent 필드를 소비한다.

- [ ] 누락/중복/비유한 지표·실패 분모·경계값·보호 경로 시험을 먼저 작성하고 RED 확인.
- [ ] 판정과 보호 구현 후 GREEN. 공식 패턴 및 M0 보고서 작성.
- [ ] 별도 BT overlay와 8개 패키지 build/설치 감사. 기존 소스 baseline은 필요한 부품만 확인.
- [ ] 선택 파일 commit 및 ledger 기록.

### Task 2: 연속 임무 수명 경계

Files: 새 transport.py; 기존 engine_extension.py, run_pick.py, run_navigation_probe.py의 작은 opt-in hook; 새 runner.

Interfaces: 사전 예약 transport goal UUID, 정착 기반 phase 전환, 원본 lease 소유권 유지. 기존 실행 기본값 유지.

- [ ] 예약되지 않은 goal·움직이는 base에서 place·접촉 상실·취소·FAULT latch 시험 RED.
- [ ] 최소 운반/정지 조작 전환 구현과 GREEN, 영향 부품 회귀.
- [ ] 동일 engine에서 파지 후 최소 이동·내려놓기 실험; 실제 실패와 잔여를 보존. 두 수정 후 같은 실패면 구조 검토 기록.
- [ ] 선택 commit 및 ledger 기록.

### Task 3: 계측과 rosbag

Files: 새 monitor.py, recording.py, scripts/reuse_13_8의 기록/재생/평가 도구.

Interfaces: Task 1 trial schema; 실제 토픽 원본 timestamp/receipt; 별도 domain 분석.

- [ ] 시간 역행·누락 샘플·CPU 분모·재생 격리 시험 RED → 구현 GREEN.
- [ ] 실제 bag 기록/닫기/읽기 확인 및 health report, 토픽/TF 흐름 문서.
- [ ] 선택 commit 및 ledger 기록.

### Task 4: 월드와 반복 검증

Files: 새 scenarios.py/config; mission runner 및 aggregate CLI.

Interfaces: Level 1/2/3 fixture manifest와 Task 1/3 지표. 실제 지원 범위를 명시한다.

- [ ] 월드 기하/목표 위치·5도 경사·문 폭 및 평가 누락 시험 RED → 구현 GREEN.
- [ ] 가장 불확실한 필수 사례부터 단일 engine 순차 검증; 기능 인수 후 고정 설정으로 10회 평가. 실패도 분모에 포함.
- [ ] 소스/자산 freeze·원본 보존·집계. 제어 변경 시 영향 회귀만 수행.

### Task 5: 교재 가이드와 최종 검토

Files: LAB_13_8_SYSTEM_VALIDATION_GUIDE_KO.md, SECTION_13_8_REPORT_KO.md, SECTION_13_8_REVIEW_KO.md.

- [ ] 다운로드/의존성/분리 build/각 터미널/13.8 소절별 실행과 실패·정상 종료 판독 작성.
- [ ] 사용자 단일 작업자 지시에 따라 자체 검토; 필요한 체크 실행 후 결과·한계와 미완료를 구분.
- [ ] 선택 commit. 원격 게시하지 않는다.
