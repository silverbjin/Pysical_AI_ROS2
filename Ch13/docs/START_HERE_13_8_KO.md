# 13.8 기본 실습 시작하기

이 패키지의 교재 목표는 **이동·관측·상태 확인·안전 종료와 실패 판독**이다. 학생 실행은 아래 `--exercise basic`을 사용한다. 관측 후 파지하지 않고 종료하며 MoveIt 계획 서버와 팔/gripper action을 시작하지 않는다. 원래 보행·native hold·센서·안전 감시는 유지한다. Level2 운반·놓기는 [과거 시연 해설](DEMO_13_8_LEVEL2_ARCHIVE_KO.md), 연속 임무 개발은 [향후 과제](FUTURE_13_8_TASKS_KO.md)로 구분한다.

## 1. 다운로드·의존성·분리 build

새 WSL Ubuntu24.04 폴더에 받는 예시다. 기존 작업 폴더를 덮어쓰지 않는다. 이미 이13.8 작업본이 있다면 clone 대신 그 루트를 사용한다.

```bash
git clone --filter=blob:none --sparse --single-branch --branch feat/ch13-section-13-8 \
  https://github.com/silverbjin/Pysical_AI_ROS2.git Pysical_AI_ROS2_13_8
cd Pysical_AI_ROS2_13_8
git sparse-checkout set Ch13
export ROOT="$PWD"
git rev-parse HEAD
```

OS/ROS2 Jazzy/Nav2·원본94자산·시뮬레이터venv는 [13.5 준비1·3·4](LAB_13_5_REUSE_GUIDE_KO.md)를, MoveIt/TRAC-IK 등 기존 패키지 build 의존성은 [13.6 준비](LAB_13_6_REUSE_GUIDE_KO.md)를 따른다. 소스는 위13.8 branch를 유지하고 그 문서의옛branch나build를사용하지않는다. 기본 모드에서는 MoveIt 서버를 실행하지 않지만 기존 통합 패키지의 build 의존성은 남아 있다. 외부 자산은 `$ROOT/../upstream-iit-locomanipulation-d010212`에 두며 모델·정책 가중치를 저장소가 재배포하지 않는다.

BT 공식 deb 준비와 전체8개 패키지 build는 다음 명령으로 한다. 모든 터미널에서 같은 값을 사용한다. 기존13.6/13.7 build를 덮지 않는다. 이 작업은 기존 환경에서 검증하며 새 OS/원격 clone부터의 전 과정 재현 검증과는 구분한다.

```bash
export CH13_REUSE_BUILD="$HOME/ch13_reuse_13_8_build"
export CH13_REUSE_VENV="$HOME/ch13_reuse_iit_d010212_venv"
bash Ch13/scripts/reuse_13_8/build.sh
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/audit_install.py /tmp/ch13_basic_install_audit.json
```

터미널 전체에venv를activate하거나 ROS apt 경로를venv앞에 넣지 않는다. ROS CLI는시스템Python, 실행기는env.sh가선택한venv를쓴다. 검증 기준은Jazzy/MuJoCo3.13.0/원본94자산이다. 설치 감사는실제실행Python과자식Python의경로도확인한다.

## 2. 소스 고정과 현재 실행 소유 상태 확인

실행 중인 다른 engine이 있으면 그 소유 runner에서 정상 회수한다. PID나오래된lock파일만보고다른작업을죽이거나lock을삭제하지않는다. 같은 자산을 쓰는 worktree는 같은 실제 공유 lock을 사용해야 한다.

```bash
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py /tmp/ch13_before_basic.json
```

`owned_stack_matches=[]`, `engine_lock_free=true`, `result=PASS`를 확인한다. 새 폴더에서는 공유lock 파일이필요하다. 기존파일이없을때만다음으로생성한다.

```bash
test -e "$ROOT/../ch13_reuse_engine.lock" || touch "$ROOT/../ch13_reuse_engine.lock"
```

현재 소스와 일치하는 새 동결을 만든다. 파일명은매번새이름을쓴다. 기존v28/v52/v53 등 과거동결을고쳐맞추지않는다.

```bash
FREEZE="Ch13/dependencies/my_basic_$(date +%Y%m%d_%H%M%S).json"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/freeze_runtime.py write "$FREEZE"
STAGE="$(mktemp -u /tmp/ch13_basic_stage_XXXXXX.json)"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/stage_runtime.py \
  --manifest "$FREEZE" --output "$STAGE"
RUN_ROOT="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["runtime_root"])' "$STAGE")"
```

## 3. 기본 실습 실행

먼저 Level2 하나를 선택한다. Level3는 다음 실행에서같은명령의scenario만`level3_house`로바꾼다. 두engine을동시에시작하지않는다. engine중build/전체시험/큰분석을병행하지않는다.

```bash
CASE="$(python3 -c 'import uuid;print(uuid.uuid4())')"
EVIDENCE="$ROOT/Ch13/evidence/section_13_8_system/$CASE"
cd "$RUN_ROOT"
CH13_CAPTURE_OVERLAP=1 CH13_EXPERIMENTAL_SE2=0 \
bash Ch13/scripts/reuse_13_8/env.sh -u Ch13/scripts/reuse_13_8/run_mission.py \
  --repo-root "$RUN_ROOT" --manifest "$RUN_ROOT/$FREEZE" --evidence "$EVIDENCE" \
  --exercise basic --scenario level2_obstacles --auto-start
```

`--auto-start`가 `/start_mission`을보내면 대기→관측지점이동→새RGB-D관측을이용한최종접근→실제정착→새관측확인→종료로진행한다. known upright원통관측이며일반물체인식이아니다. 상태확인을위해두번째터미널에서같은ROOT/build/venv를설정하고읽는다.

```bash
cat "$EVIDENCE/live_status.json"
```

진행표시의`completed`는navigate/find/finish를보인다. pick/return/place는기본실습의요청/완료목록에없어야한다. 파일표시지연은물리상태자체가아니므로최종결과와구분한다. 중간에종료하려면실행터미널에서Ctrl+C를한번누르고회수를기다린다. 반복강제종료로정상종료를대신하지않는다.

## 4. 결과와 실패 판독

```bash
cd "$ROOT"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/inspect_case.py --case "$EVIDENCE"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py /tmp/ch13_after_basic.json
```

기본결과는`basic_result.json`이다. 전체미션평가용`trial.json`을만들지않는다. `scope=basic_navigation_observation_only`, `full_mission_success=false`가정상적인범위표시다. 기본실습PASS는이동·관측·종료검사가모두통과했다는뜻이며파지·운반·놓기를뜻하지않는다.

|확인할 기록|판독|
|---|---|
|basic_result의checks|어떤 기본동작/종료 항목이충족됐는지확인|
|bt_summary의terminal/port.completed|실제완료단계와첫error,worker종료확인|
|navigation_summary|목표도달·실제정착·최초안전fault·자식회수확인|
|engine.normal_shutdown_requested와thread join|정상종료요청/수신·정책스레드회수확인|
|after residual 검사|남은소유프로세스없음/공유lock해제확인|

관측수명초과·이동기한·사용자취소등이면동작결과는FAIL일수있다. 실패를숨기거나수치를바꾸어PASS로만들지않고, **어디까지완료→무엇이최초원인→어떻게정지·회수했는지**를실습보고서로제출한다. 오류원인판독과이동·관측PASS는별도학습항목이다. arm_probe.json/pick_mission.json이생겼다면기본모드실행인지확인한다.

최신한번의실제검증과한계는 [마무리검증보고](SECTION_13_8_BOOK_CLOSEOUT_REPORT_20261112_KO.md)에기록한다. 학생에게전체부품suite나과거10회matrix를매번요구하지않는다. `--exercise full` 및 evaluate_batch.py는미완료연속임무의개발자용이며기본실습명령에추가하지않는다.
