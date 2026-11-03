# 13.5 공개 통합 로봇 재사용 개정안 — 설계·구현 인계

> 후속 작업자는 이 문서를 먼저 읽는다. 네이티브 단일 작업자로 진행하며, 실행 단계에는 `superpowers:executing-plans`를 적용한다. 이 문서는 새 개정 방향의 설계와 단계별 실행 계획이다. 기존 Task8 재개문서를 그대로 실행하지 않는다.

**작성일:** 2026-11-02, 한국 시각.

**Goal:** 기존 Go2+Piper 통합 로봇·공개 이동 정책을 재사용하여, MuJoCo에서 ROS2/Nav2가 물체 근처의 작업 위치로 이동하고 실제 정지하는 13.5 실습을 만든다.

**Architecture:** 모델·정책·관측/명령 규약·시뮬레이터 설정을 하나의 검증 단위로 채택한다. 보행 제어는 upstream을 재사용하고 Ch13은 속도 명령 어댑터·안전 게이트·TF/센서 연결·Nav2·접근 과제와 인수 도구를 소유한다. 원본 동작을 먼저 재현하고 그 다음 ROS2/Nav2를 연결한다.

**Tech Stack:** ROS2 Jazzy, MuJoCo, 공개 Go2+AgileX Piper 모델/사전 학습 이동 정책, Nav2. 실제 채택 버전은 원본 재현 단계에서 고정한다. Isaac Lab 재학습은 본문 필수 과정에 넣지 않는다.

**Spec:** 이 문서의 ‘승인 방향·비목표·변경되는 요구’가 개정 명세다. 기존 연구의 사실 확인에는 `SECTION_13_5_TIME_RETROSPECTIVE_KO.md`, `SECTION_13_5_TASK8_REFERENCE_SELECTION_KO.md`, `SECTION_13_5_BOOK_ACCEPTANCE_POLICY_KO.md`를 참고한다. 마지막 문서의 자체 crawl 조건은 새 플랫폼의 모터 사양으로 자동 이식하지 않는다.

## 1. 사용자 요청과 승인된 방향

사용자는 13.5 제작이 장기화되어, 새 로봇/보행기를 개발하는 대신 이미 개발된 로봇 모델과 코드를 활용하는 전면 수정을 요청했다. 다음 제안을 받은 뒤 ‘이 방향으로 개정안을 구체화하되 인계문서로 작성’하도록 지시했다.

- 기존 Go2+Piper 통합 시스템의 재사용을 우선한다.
- IIT-DLSLab 공개 시스템을 첫 번째 원본 재현 후보로 삼는다. 최종 채택은 재현 결과로 결정한다.
- MuJoCo를 본문 필수 실행 환경으로 삼는다.
- Gazebo 동등 구현과 자체 crawl은 확장/연구 범위로 분리한다.
- 13.5 학습 목표는 이동 제어기 개발에서 공개 이동 플랫폼과 Nav2의 통합으로 옮긴다.

**이번 턴에서 수행한 것은 인계문서 작성이다.** 새 패키지 구현·외부 설치·정책 실행·엔진 시험·브랜치 전환·commit/push는 수행하지 않았다. 사용자에게 이 문서로 구체안을 전달한 뒤 후속 실행 지시가 오면 진행한다. 실행 시 이미 합의된 내부 세부 선택마다 다시 허가를 요청할 필요는 없다.

## 2. 실제 저장소와 기존 작업 상태

저장소 절대 경로:

```text
C:/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2
```

문서 작성 전 조회 결과:

- 브랜치: `feat/ch13-section-13-5`.
- HEAD: `bc31d370501bde5653dd6254ae6c18766d45aacc`.
- 커밋: `fix(ch13): defer future contact pairs until original clock catches up`.
- author 시각: 2026-11-02 13:42:25 +09:00.
- `git status`에는 기존 evidence의 삭제·retention 메타데이터 수정이 있다. 보존 정책 작업일 수 있으므로 복구·삭제·stage하지 않는다. 이 문서 작성으로 생긴 변경과 구분한다.
- 기존 체크포인트의 head는 `8e9cca5`로 실제 HEAD보다 오래됐다. 그 파일 전체를 최신 사실로 신뢰하지 않는다.
- 체크포인트상 active root/session은 null이다. 작성 중 WSL/OS 프로세스를 독립 조회하지 않았으므로 ‘현재 소유 프로세스가 전혀 없음’까지 보증한 것은 아니다.
- 원격 SHA는 이번 문서 작성에서 다시 조회하지 않았다. 과거 동기화 보고를 현재 일치 증명으로 사용하지 않는다.

기존 Task8의 마지막 실제 기록은 G1 `24438df2` PASS, C1 `da616654`의 contacts wall age214.065ms FAIL이다. 수치 요청0건이므로 새 힘 모델이 실제 검증된 실행이 아니다. 후속 경계 수정은 source/설치 감사와 관련 회귀가 있지만, 체크포인트 기준 새 실제 C1 성공은 없다.

기존 자료:

- `.superpowers/sdd/SECTION_13_5_IMPLEMENTATION_PLAN_KO/CURRENT_TASK_STATE.json`
- `Ch13/docs/HANDOFF_SECTION_13_5_2026_11_02_KO.md` — 이전 연구 인계, 새 개정 실행 지시가 아님.
- `Ch13/docs/SECTION_13_5_FORCE_APPLICATION_DIAGNOSIS_KO.md`
- `Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b/EXECUTION_LEDGER.md`

## 3. 변경되는 요구와 보존할 사실

| 항목 | 이전 연구 경로 | 개정 경로 |
|---|---|---|
| 로봇·보행 | Ch13 독자 통합 모델 + 자체 저속 crawl | 공개 Go2+Piper 모델·검증 대상으로 배포된 이동 정책 |
| 핵심 개발 | 하중 전환 QP·접촉·서보·궤적 | 공개 플랫폼 재현·속도 인터페이스·Nav2·접근·안전 정지 |
| 보행 모드 | crawl 필수 | 정책이 실제 지원하는 모드. 저속 이동을 crawl로 부르지 않음 |
| 엔진 | MuJoCo/Gazebo 동등 인수 | MuJoCo 필수, Gazebo는 별도 확장 |
| 학습 | 필요 시 새 이동기 개발 가능 | 기존 가중치 추론 우선. 학습이 필요하면 후보 탈락/별도 결정 |
| 기존 Task8 | 미완료 | 미완료 연구 기록으로 보존. 새 시험으로 과거 FAIL을 덮지 않음 |
| 최종 통과 | 독자 crawl 내부 조건 + Nav2 | 채택 플랫폼의 안전 운전 + 실제 Nav2 접근·취소·정지·종료 |

이것은 같은 구현의 검사를 느슨하게 만드는 패치가 아니라, **사용자가 요청한 교재 실습 범위의 변경**이다. 기존 required_checks는 수정해 과거 결과를 PASS로 만들지 않는다. 새 실행기·기준·증거에는 별도의 개정 식별자를 쓴다.

다음은 계속 유지한다.

- `sources/`, Ch01~Ch12, 외부 checkout/underlay 원본은 수정하지 않는다.
- 사용자 작성 `Ch13/docs/SECTION_13_4_DEBUGGING_LESSONS_KO.md`는 수정·선택적 stage 금지.
- 단일 관절/TF/명령 소유권, 원본 촬영 시각·최초 receipt 보존.
- 관측 만료·비유한 값·중복 소유자·시계 역행에 fail-closed, 자동 재활성화 금지.
- 실제 terminal result와 cancel ACK 구분. 실측 정지와 프로세스 소멸 구분.
- 엔진 순차 실행·소유 PID 확인·정상 회수·잔여 검사.
- 영상 연결 시 기존13.4의320×240/카메라15Hz/추론10Hz 기본·15Hz 선택, age300ms/과거TF100ms/팔 명령5Hz 계약 유지.
- 시스템 권한·드라이버·공유 시간 설정 변경은 자동 승인으로 확대하지 않는다.

**플랫폼 고유값은 따로 확정:** 기존 자체 모델의 hip20Nm/기타30Nm,2ms 물리,100Hz manager,50Hz 보행,10ms/32회 QP는 새 Go2/Piper 정책에 무조건 적용하지 않는다. 원본 모델·훈련 조건·정책 제어주기·actuator cap을 먼저 재현하고 새 사양표에 기록한다. 다른 수치를 썼다고 과거 안전 계약과 같은 것으로 표시하지 않는다.

## 4. 후보 선택과 탈락 조건

### 우선 후보 A: IIT-DLSLab Go2+Piper

- [공식 코드](https://github.com/iit-DLSLab/locomanipulation-teleop-isaaclab)
- [배포 안내](https://github.com/iit-DLSLab/locomanipulation-teleop-isaaclab/blob/main/README_DEPLOY.md)
- [기본 정책 설정](https://github.com/iit-DLSLab/locomanipulation-teleop-isaaclab/blob/main/deploy/config.py)
- [공개 학습 결과](https://github.com/iit-DLSLab/locomanipulation-teleop-isaaclab/tree/main/tested_policies/arm_moving_clock)
- [LocoPilot 연계 ROS2 스택](https://github.com/iit-DLSLab/LocoPilot)

조사에서 확인한 항목: Go2+Piper 통합 모델, 팔 상태를 고려하는 이동 정책, `play_mujoco.py`, `run_simulator_ros2.py`, `run_controller_ros2.py` 배포 경로, 기본 config의 `tested_policies/arm_moving_clock` 참조, 학습 체크포인트·exported 폴더. root BSD-3-Clause이며 모델/가중치/하위 의존성 권리는 추가 확인한다.

소스의 현재 README에는 MuJoCo3.13.0·IsaacLab/rsl-rl 버전 정보가 있다. Ch13 기존 vendor3.12.0과 같다고 가정하지 않는다. 격리된 추론 환경으로 재현하고 기존 환경을 업그레이드해 덮지 않는다. 배포 단계에 Isaac 학습 환경 전체가 정말 필요한지도 먼저 확인한다.

**미확인:** 현재 PC에서 정책 inference 성공, actor/estimator/RMA 파일의 완전성·모델과의 결합, 정확한 팔 모델 변형/기구학, ROS 토픽 입력, RGB-D/LiDAR 및 MoveIt 연결 가능성. README/영상은 이 환경의 PASS가 아니다. LocoPilot의 하드웨어·Docker·Jetson 전체를 교재 의존성으로 가져오지 않는다.

### 차선 후보 B: LeggedManip Lab Go2+Piper

- [공식 코드](https://github.com/zzzJie-Robot/LeggedManip_Lab)
- [공개 정책 파일](https://github.com/zzzJie-Robot/LeggedManip_Lab/tree/master/mujoco/deploy/policy/go2_piper)

Go2+Piper 모델·MuJoCo 배포·실제 `policy.pt`(API 조회 크기1,111,382bytes, blob `eb05bad1ae88b2ce5375fe2c7ed82d290da572b6`)를 확인했다. 존재 확인이지 binary 실행 검증이 아니다. root Apache-2.0, 모델·가중치별 조건은 확인한다. ROS2 연결 추가 비용, 추론 의존성, Flat/WBC별 다리·팔 action 소유권을 먼저 판별한다.

### 기본안으로 쓰지 않을 후보

- legubiao Go2+OCS2: 훌륭한 Jazzy 비교 사례지만 맨몸 정책/모델에 팔을 붙여 적재 검증을 새로 시작하지 않는다.
- CHAMP: 가벼운 gait/IK만으로 기존 실측 접촉·팔 적재 문제 해결을 선언하지 않는다.
- 새 PPO 학습·새 crawl·새 WBC·전체 플랫폼 자체 제작: 본문 범위 밖이다.

**후보 탈락:** 공개 가중치/모델 누락, 재학습 필수, 환경 요구가 현재 자원에 부적합, 팔 구성 불일치, 정책이 팔까지 독점해 후속 팔 제어와 분리 불가, 필수 입출력 의미를 확인할 수 없음. 두 후보가 모두 탈락하면 조용히 자체 보행 개발로 돌아가지 말고 증거·대안·필요한 결정을 제시한다.

## 5. 새 13.5 목차

제목: **네비게이션과 보행의 연동: 공개 통합 플랫폼으로 작업 위치에 접근하기**

| 절 | 내용 | 필수 실습 결과 |
|---|---|---|
| 13.5.1 | 네비게이션과 이동 정책의 역할·플랫폼 선택 | 모델/정책/환경 lock 읽기 |
| 13.5.2 | 공개 Go2+Piper의 MuJoCo 실행 | 기립·속도 입력·정지 |
| 13.5.3 | ROS2 속도·상태·TF·센서 계약 | 단일 명령자·연결된 TF·실제 상태 |
| 13.5.4 | 지도·localization·footprint·Nav2 | 지도상 목표까지 실제 이동 |
| 13.5.5 | 속도 제한·watchdog·수납 조건 | 만료·취소 시 안전 정지 |
| 13.5.6 | 물체 관측에서 접근 목표 계산 | 충돌/도달 가능 후보 선택 |
| 13.5.7 | NavigateToPose 결과·정착·인계 | terminal+실측 정지 후만 팔 단계 허용 |
| 13.5.8 | 장애물·도달 불가·입력 손실 | 실패 원인과 안전 종료 확인 |
| 13.5.9 | 결과·한계·확장 | 본문/확장/미검증 구분 |

min_obstacle_height로 낮은 장애물을 일괄 무시하는 예제는 제거한다. 2D scan 높이 설정은 실제 등반 가능성 증명이 아니다. gait switching은 upstream 지원과 실제 검증이 있을 때만 확장한다. 접근 거리0.4m와 footprint 예시값을 그대로 복사하지 않고 실제 팔 mount/IK·수납/보행 envelope로 계산한다.

## 6. 기존 장과의 경계

13.1~13.4의 모델·실습·evidence를 보존한다. 새 플랫폼을 이전 장의 동일 로봇으로 표현하지 않는다. 13.5 도입에 ‘여기부터 공개 통합 플랫폼으로 전환한다’는 연결 설명을 넣는다.

- 기존 재사용: 액션 소유권 원칙, terminal 수신, watchdog, 원본 시각·TF 안전 계약, 실행기 정리, 제한된 evidence/설치 감사.
- 새로 대조: 관절 순서/단위/한계, base/optical TF, arm mount·Piper 변형, gripper, 카메라 내·외부 파라미터, 수납 자세, 정책 입력.
- 13.4 비전 코어를 재사용하더라도 새 카메라/TF에서 별도 회귀한다. 예전 RMS 성공을 새 플랫폼 성공으로 재사용하지 않는다.
- 13.6은 선택한 팔의 interface/MoveIt 설정에 맞춰 연결 계획을 후속 작성한다. 이번에 물리 파지·MoveIt·전신 동시 최적화를 확장하지 않는다.

Ch13 독립 실행은 ‘Ch05~12 빌드 없이 실행’이다. upstream 의존성이 없어야 한다는 뜻은 아니다. 필요한 외부 자산은 고정 커밋·해시·라이선스·설치 방법을 Ch13에서 재현 가능하게 기록한다. 전부 최신 main으로 자동 다운로드하지 않는다.

## 7. 구성과 인터페이스 제안

아래 경로는 **신규 생성 예정**이며 이미 구현된 것으로 해석하지 않는다. 기존 navigation 패키지에 새 경로를 섞기보다 독립 opt-in 패키지를 우선 제안한다.

```text
Ch13/
  ros2_ws/src/ch13_navigation_reuse/
    package.xml, setup.py, resource/ch13_navigation_reuse
    ch13_navigation_reuse/
      command_gateway.py        # 단일 속도 소유자·만료·정지·모드
      platform_adapter.py       # 확정 upstream 입출력 변환만
      state_adapter.py          # 실제 pose/twist·관절·frame 변환
      readiness.py              # 기립·수납·관측·정착 승인
      approach.py               # 비전 목표·후보·Nav2 소유권
    config/{platform.yaml,nav2_params.yaml}
    launch/{platform.launch.py,navigation.launch.py}
    test/                       # 실제 wire/소유권/만료/결과 시험
  scripts/reuse_13_5/
    reproduce_upstream.py       # 원본 재현; 새 gait 구현 금지
    run_acceptance.py
    verify_acceptance.py
  dependencies/section_13_5_reuse.lock.json
  docs/{SECTION_13_5_REUSE_DESIGN_KO.md,LAB_13_5_REUSE_GUIDE_KO.md,
        SECTION_13_5_REUSE_REPORT_KO.md,REUSE_MANIFEST.md}
  evidence/section_13_5_reuse/<UUID>/
```

upstream 실제 API를 읽기 전에 adapter의 세부 구현/토픽을 추측해 고정하지 않는다. 다음 Ch13 경계는 고정한다.

| 데이터/권한 | 계약 |
|---|---|
| Nav2 출력 | 전용 raw 속도 경로→스무더→안전 게이트→platform adapter. upstream에 직접 보내는 우회 publisher 금지 |
| 정책 입력 | vx/vy/wz의 단위·좌표·지원축·한계·주기를 platform.yaml에 명시. Twist/Stamped 여부는 확정 Jazzy 설정과 일치 |
| 정책 출력 | upstream 다리 소유자만 적용. Ch13 기존 crawl/RL leg publisher와 동시 활성화 금지 |
| 팔 | 이동 중 검증된 수납 상태. 정책이 팔 상태를 관측하는 것과 팔 명령까지 소유하는 것을 구분 |
| 정지 | 계획 속도0→실제 저속/정착 확인. 차단 시 actuator torque0 또는 정책 즉시 종료로 대체하지 않음 |
| 상태 | 실제 engine 관측의 pose/twist/q/qd. 목표를 odometry로 발행하거나 root teleport 금지 |
| TF | map→odom→nav_base/base→arm→camera, 각 edge 단일 소유자. 원본 body 진동을 없앤 TF를 실측으로 위장하지 않음 |
| localization | 초기는 engine ground truth 기반을 명시적으로 허용하는 교육 profile. AMCL/SLAM 실증으로 부르지 않음 |
| 입력 손실 | 원본 stamp·최초 receipt 기준. 고장 latch 후 명시적 재무장, 자동 재개 금지 |
| 센서 | 실제 ray/render 출처. upstream에 없으면 최소 engine sensor 추가를 별도 기록. 장면 정답을 scan/비전 관측으로 위장하지 않음 |

## 8. 단계별 실행 계획

### R0 — 보존·격리·의존성 조사

- [ ] 실제 HEAD/dirty/untracked·AGENTS·원격 상태·소유 실행을 확인한다.
- [ ] 기존 실패와 사용자 파일을 보존한다. staged 전체 commit/clean/reset/강제 push 금지.
- [ ] 새 브랜치 `feat/ch13-section-13-5-reuse`를 제안한다. 동명 원격이 있으면 날짜/고유 접미사로 분리한다. dirty 작업을 잃지 않는 방식으로 격리하고 임의 stash를 하지 않는다.
- [ ] upstream commit, 모델/가중치 SHA, license, Python/MuJoCo/ROS 의존성, CPU/GPU·메모리 요구를 lock에 기록한다. 학습 환경과 추론 환경을 분리한다.

**완료:** 재현할 조합과 실제 파일을 모두 식별했다. 가중치가 공개 폴더에 있다는 사실만으로 추론 가능 판정하지 않는다.

### R1 — upstream 그대로 재현 (최우선 탈락 검사)

- [ ] 모델·actor/estimator/RMA·normalization·joint order/action scale·초기 자세를 맞춘다.
- [ ] 먼저 ROS2/Nav2 없이 원본 MuJoCo 예제를 실행한다. 임의 게인·질량·접촉 변경 금지.
- [ ] 기립/팔 탑재·수납/전진/회전/0명령/정착/정상 종료를 실측한다. 작은 결과·command·hash를 남긴다.
- [ ] 기존 정책의0명령이 정적 STAND인지 제자리 보행인지 구분한다. 후속 조작 가능한 정착을 제공하지 못하면 플랫폼 적합성 문제로 평가한다.
- [ ] 첫 후보가 재학습 또는 새 보행기 설계를 요구하면 R2로 넘기지 않고 탈락 근거를 작성한다. 차선 후보는 최대1개만 추가 비교한다.

**시간 운영 제안:** 자산·격리 환경이 준비된 뒤 원본 재현 판별은 약2~4시간의 한 세션을 목표로 한다. 설치/다운로드/처음 빌드 시간과 활성 진단시간은 별도 기록한다. 이는 성공 보장이나 안전 기한 완화가 아니다. 예산 끝에 끝없는 파라미터 탐색을 하지 않는다.

### R2 — 플랫폼 확정·최소 ROS2 연결

- [ ] R1 PASS 뒤 실제 모델/정책/제어권을 설계서와 platform.yaml에 동결한다.
- [ ] command_gateway/state_adapter의 단위·축·관절 순서·stamp·중복 소유자·미래/만료 입력 RED를 먼저 만든다.
- [ ] upstream 기존 ROS2 실행 경로를 우선 사용하고 필요한 변환만 추가한다. 전체 시뮬레이터 bridge를 다시 쓰지 않는다.
- [ ] GREEN 뒤 실제 DDS·clock pause/rollback·입력 손실·publisher 교체·종료 수명을 검사한다.
- [ ] 설치본 byte/가중치 hash 감사, 실제 짧은 기립·이동·정지로 연결을 확인한다.

**완료:** engine의 실제 상태가 ROS2로 나오고 Ch13 속도 소유자 하나만 정책을 지시한다. 팔 독립 제어 가능성도 확인됐다.

### R3 — Nav2 최소 네비게이션

- [ ] 평지·고정 장애물·지도·실제 scan을 만든다. 기존 카메라를 요구하기 전에 고정 map goal로 이동 경로를 검증한다.
- [ ] 실제 footprint/회전 envelope/지원축과 속도·가속도를 설정한다. 검증하지 않은 Spin/BackUp 복구를 기본 활성화하지 않는다.
- [ ] TF 중복·map/world 변환·Twist 타입·smoother/guard 우회에 대한 RED→GREEN을 확인한다.
- [ ] 경로 생성·장애물 우회·도착·취소·실측 정착·정상 종료를 수행한다.

**완료:** Nav2 status만이 아닌 실제 이동/도착을 입증했다. 이 단계는 아직 비전 목표 접근 성공이 아니다.

### R4 — 13.4 관측과 작업 위치 접근

- [ ] 새 카메라/TF에서 원본 RGB-D·과거 TF·depth/optical axis를 검증한다. source header를 now로 바꾸지 않는다.
- [ ] 실제 물체 관측을 source 식별자와 함께 admission한다. 초기 디버그 ground truth goal은 별도 표기하고 최종 비전 시험으로 세지 않는다.
- [ ] arm mount·수납/도달 범위·충돌·경로 비용으로 접근 후보를 평가한다. 최적 거리0.4m를 보편값으로 고정하지 않는다.
- [ ] 실제 NavigateToPose terminal+실측 위치/방향+정착 뒤 READY_FOR_MANIPULATION을 발행한다. 팔 파지는 다음 절이다.

### R5 — 동결 인수·문서·게시

- [ ] 아래 새 인수 기준의 숫자와 시나리오를 최종 실행 전에 동결한다.
- [ ] source/package/설치hash 검사 뒤 MuJoCo 필수 matrix를 수행한다. 실패하면 해당 결과를 보존하고 영향받은 검사를 새 고정본에서 재실행한다.
- [ ] 한글 원고/가이드/출처·미검증/전환 설명·evidence 요약을 정리한다.
- [ ] 선택 파일만 commit, 새 절 개정 브랜치에 non-force push, local HEAD/실제 remote SHA를 대조한다. main 병합·PR은 별도 지시가 없으면 하지 않는다.

## 9. 개정판 인수 기준

다음은 이번 개정안의 **제안 기준**이다. 원본 정책의 운전 범위를 먼저 확인하고 R2에서 수치를 사전 확정한다. 최종 실패를 본 뒤 수치를 바꾸지 않는다. 기본 목표 도착 허용오차0.10m/0.10rad·정착1wall초는 기존 접근 설계의 교육 기준을 이어받는다.

| 게이트 | 필수 확인 |
|---|---|
| U1 자산 재현 | 정확한 model/policy/config hash·실제 로딩·기립·팔 탑재 유지·정상 종료 |
| U2 운전 | 사전 정의 전진/회전/정지·실측 상태·넘어짐/충돌 없음·명령/관절/힘 한계 준수 |
| U3 Nav2 | 자유 공간 도착·장애물 우회·막힌 경로 실패·goal 취소 |
| U4 비전 접근 | 실제 촬영 목표·유효 과거TF·실제 root 위치/방향·팔 작업영역·정착1초 |
| U5 손실/소유권 | raw·관측 손실, 중복 명령자, 오래된 목표, 시계 역행에 고장·정지·자동 재개 없음 |
| U6 수명 | 액션 result·실측 정지·worker/RX join·정상engine/부모 종료·잔여 없음 |
| U7 배포 | Ch13만의 빌드/설치 절차·소스/설치/가중치 일치·같은 고정본 재현·remote SHA |

필수 시나리오는 고정본에서 각1회 전수 실행한다.3회 반복은 별도 강건성 확장으로 둔다. 실제 stop 시간·속도 제한·관절/토크 cap은 원본 재현과 안전 분석으로 R2에서 사전 명시한다. 서로 다른 로봇에 기존20/30Nm를 기계적으로 적용하지 않는다.

기존13.3/13.4 원본 package의 회귀와 새 플랫폼의 통합 회귀를 분리한다. 새 팔/카메라에 이전 플랫폼의 실제 엔진 PASS를 전이하지 않는다. 새 플랫폼에 의미 없는 독자 QP10ms/32회 검사를 성공으로 체크하지 않고 ‘다른 구현 경로’로 명시한다. 고유 원본 시각·센서 age·단일 소유권·실제 종료 요구를 없애는 근거로 사용하지 않는다.

## 10. 효율·기록·중단 규칙

- 활성 작업/설치대기/실행/분석/중단 시간을 분리 기록한다. 경과기간을 공수로 보고하지 않는다.
- 한 실험은 한 가설을 판별한다. 작은 DDS/수학/물리 부품으로 제거 가능한 후보를 전체 엔진에서 탐색하지 않는다.
- 같은 실패 계열이 두 번의 최소 수정 뒤에도 남으면 전체 재실행을 멈추고 구조를 검토한다.
- source/hash 불변 시험은 범위에 맞게 재사용하고 최종 full matrix는 동결 뒤 수행한다.
- 실행 중 build/pytest/대용량 압축·분석을 병행하지 않는다. 상태 조회는 작고 유계로 한다.
- 기존 evidence 보존 정책을 적용한다. 대표 성공/실패만 상세 원본, 기타는 설정·원인·메트릭·해시·핵심 window. 먼저 pin하고 정리한다.
- 사용자 동의 없는 외부 환경·드라이버·권한 변경 금지. 원본 안내의 sudo/원격 하드웨어 배포 명령을 그대로 실행하지 않는다.

## 11. 새 작업 창의 첫 실행 순서

1. 이 문서와 적용 AGENTS를 읽고 실제 git/작업트리/소유 프로세스 상태를 확인한다.
2. 기존 Task8의 자동 G1/C1 재실행을 새 계획의 첫 작업으로 삼지 않는다. 이미 소유 실행이 있다면 정상 종료/복원 수명을 먼저 처리한다.
3. R0에서 새 브랜치·자산 lock·격리 환경을 확보한다.
4. 첫 실험은 **IIT-DLSLab Go2+Piper 원본 MuJoCo inference의 재현 가능성**이다. 먼저 actor/추정기/설정의 파일 완전성과 모델 일치를 읽기 전용 확인한다.
5. 실제 원본 재현 결과를 얻기 전에 Nav2 YAML·새 gait·새 arm 모델을 대량 작성하지 않는다.

현재 완료된 것은 개정 방향 합의와 이 인계 설계다. 플랫폼 확정·원본 재현·ROS2 연결·Nav2·비전 접근·최종 인수는 모두 후속 작업이다.
