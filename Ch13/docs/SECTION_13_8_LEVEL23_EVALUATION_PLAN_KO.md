# Level2·Level3·10회평가 실행계획

> 실행방법: superpowers:executing-plans,단일작업자. 사용자의질문없이진행/명세후실행지시를우선한다.

**Goal:** 실제월드와같은engine의관측이동을연결하고고정10회평가를실행한다.
**Architecture:** scenario의기하를MuJoCo/지도/MoveIt가공유하고,Session.ready의관측이동뒤기존관측기반접근을재사용한다. 평가전용world witness와batch plan으로누락/교체를검출한다.
**Tech stack:** 기존ROS2 Jazzy/Nav21.3.13/MoveIt2.12.4/MuJoCo3.13.0/py_trees_ros2.6.0/Python3.12.
**Spec:** [작업명세](SECTION_13_8_LEVEL23_EVALUATION_SPEC_KO.md).

## 제약·공유인터페이스

정책/PD/effort·속도/가속도·원본수명·취소/회수한계는명세대로유지한다. 기존13.6/13.7기본값·원본FAIL·source freeze수정금지. 새build는기존13.8분리경로만사용한다.

Task1→2: Scenario.survey_pose/기하와새profile이름공유. Task1→3: base_xyz/ramp_contact_N/found관측의평가스키마공유. Task3→4: source/scenario hash·10UUIDslot·success/complete를공유한다. 기존transport판정은변경하지않는다.

## Task1: 월드·실제기하·평가관측

Files: scenarios.py,새worlds.py,scene.py/world_map.py,run_pick.py,pick_monitor.py,worlds시험.

- [ ] 두새scenario/문폭/테이블상하/5도상면/지도와3D차이·기본값보존의실패시험실행.
- [ ] 기하단일정의와실제MuJoCo모델·Nav2지도·MoveIt충돌을연결.
- [ ] ramp를지면그룹으로유지하되팔접촉보호,평가전용base/ramp접촉기록추가.
- [ ] 정상/음성기하와원본모델·actuator/hash부품확인,선택commit.

## Task2: 관측이동과소유권

Files: 새survey.py,run_mission.py의ValidationSession.ready,run_navigation_probe.py의opt-in already-armed준비gate,관련시험.

- [ ] falsearm/미정착/취소/terminal없는client파괴거부와기본gate보존의실패시험.
- [ ] 기존단일owner until/poll·GoalTracker로관측이동수행,새3D관측의최종접근으로연결.
- [ ] 동기spin/시간연장/reset없이drain·정착·freshzero·두번째goal경계검증.
- [ ] 새scenario에만Nav2 1.5cm재작성적용. 실제가시성/필요한사전사례확인.

## Task3: world witness와고정batch평가

Files: 새world_assessment.py,batch.py,scripts/reuse_13_8/evaluate_batch.py,run_mission.py trial연계,음성시험.

- [ ] ramp미접촉/문미통과/find누락/중복UUID/source·scenario변경/누락·NaN·실패분모시험RED.
- [ ] 기존assess_trials를재사용하고불완전자료의엄격FAIL/유효부분집합보조평균구현.
- [ ] 10slot사전plan생성·overwrite거부·한slot1기동·case간실제잔여검사구현.
- [ ] 관련및필요전체회귀,실제child/설치/동결·동일source감사.

## Task4: 실제평가·보고

- [ ] engine없는상태에서source/94자산/lock·저장 공간·실행 권한감사.
- [ ] 사전개발사례후제어를동결,새batch plan10slot을순차실행.
- [ ] 시작FAIL/FAULT/미실행·시간/정밀도목표미달을원본그대로집계.
- [ ] 실행source/원본archive/hash·JSON/CSV·한국어결과보고/가이드·자체검토.

## Review focus

문폭만넓고실제벽을통과하지않는case,경사를피해가고도PASS하는case,상판을2D에투영해도달불능인case는Task1/3시험으로확인한다. already-armed상태를stale입력권한으로오용하는경우는Task2에서거부한다. batch실패를재시도/다른hash자료로교체하는경우는Task3에서거부한다.
