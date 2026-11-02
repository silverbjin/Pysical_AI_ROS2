# 13.6 M0 조사 보고서

작성: 2026-11-03 KST. 단일 작업자. 상태: **읽기 전용 환경/API/소스 조사 완료, 설계 검토 대기. 구현·설치·엔진 실행 미수행.**

## 명세와 보존

사용자가 이번 대화에 13.6.1~13.6.7 원고를 제공했다. 기존 인계의 ‘원고 없음’은 당시 기록이며 이번 개발에는 적용되지 않는다. 필수 범위는 MoveIt 계획 장면, 관측 시각 TF 변환, 장애물 회피 pre-grasp, 느린 Cartesian 진입, 실제 그리퍼 파지와 0.10m lift다. 놓기는 필수가 아니다. CoM shift-back, crawl/stand 전환은 기존 정책에 존재한다고 간주하지 않으며 별도 전신제어 개발을 하지 않는다.

상위 프로젝트 AGENTS.md만 발견했다. sources/, Ch01~12, 외부 모델/정책 원본, 기존 13.5 freeze/evidence, SECTION_13_4_DEBUGGING_LESSONS_KO.md를 변경하지 않았다.

## 저장소와 실행 상태

- 작업 위치: `work/Pysical_AI_ROS2_reuse`. 다른 Task8/가이드 검증 checkout을 사용하지 않았다.
- 시작 branch: `feat/ch13-section-13-5-reuse-r2-20261102`, HEAD `68cb78972ebf861d8ed5fd09b2fe062df0d1e908`. 직전 commit은 인계 문서만 추가했다. 초기 `git status --short` 출력 없음.
- 원격 URL 직접 `ls-remote` 조회에서 위 branch SHA가 로컬 HEAD와 일치. `feat/ch13-section-13-6-manipulation` 원격 ref는 반환되지 않았다.
- 기존 linked worktree임을 git-dir/common-dir 차이로 확인했고 superproject 출력 없음. 새 worktree를 중복 생성하지 않고 위 HEAD에서 `feat/ch13-section-13-6-manipulation` branch 생성.
- Windows 프로세스 목록과 WSL 전체 ps에서 조회 시점에 기존 Ch13 engine/renderer/ROS mission 실행을 발견하지 않았다. lock 파일은 존재하지만 WSL lslocks에 해당 lock 소유자가 없었다. 파일 안 PID를 실행 증거로 취급하지 않았고 lock을 삭제하지 않았다. 구현 실행 직전에 다시 확인해야 한다.
- 기본 제한 환경에서는 WSL/CIM 접근 및 GitHub 통신이 실패했다. 읽기 전용 권한 확장 후 조회했다. 확장된 Windows git에서 `origin` 해석이 실패했으므로 실제 URL을 지정해 원격을 확인했다. 시스템 설정은 변경하지 않았다.
- WSL 시작 시 기존 `/etc/wsl.conf`의 `boot.appendWindowsPath` unknown-key 경고가 나왔다. 이번 작업에서 고치지 않았다.

## 모델 계약

실제 통합 모델 `robot_model/go2_piper_l.xml`을 기준으로 한다. 독립 팔 모델 `piper_l/piper_l.xml`은 joint1~6이 unlimited여서 planning 한계의 원본으로 사용할 수 없다.

| 관절 | 실제 통합 모델 한계 | 단위 |
|---|---|---|
| joint1 | -2.618~2.618 | rad |
| joint2 | 0~3.14 | rad |
| joint3 | -2.697~0 | rad |
| joint4 | -1.832~1.832 | rad |
| joint5 | -1.22~1.22 | rad |
| joint6 | -3.14~3.14 | rad |
| joint7 | 0~0.05 | m, slide |
| joint8 | -0.05~0 | m, slide |

joint8 equality는 `q8=-q7`. 독립 joint8 actuator는 없고 gripper motor는 joint7에 연결되어 ±0.5N로 제한된다. 원본 loop는 gripper 위치 PD를 계산해 ctrl[18]에 쓴다. 팔 native PD는 ctrl[12:18]의 위치 목표를 소유한다. gripper 명령은 그 loop의 desired_joint_pos_gripper로 전달해야 하며 ctrl에 경쟁 writer를 추가하지 않는다. 실제 개폐 방향·finger 사이 유효 폭·접촉력/파지 성공은 아직 동역학으로 확인하지 않았다.

팔 mount는 base→link1의 pos `[0.000852257,-0.00011245,0.192997]`, wxyz quat `[0.999994,0.000457118,0.00346448,0]`다. link6 attachment_site z=0.10은 파지 중심으로 검증된 TCP가 아니다. link7/8 collision box의 중심·면으로 새 TCP를 정의하고 FK 대조해야 한다.

원본 94파일과 기존 v3 실행114파일 전부 SHA256 일치. 통합 모델 SHA256 `42befed63bd46a26ea21b32b63201dcdcc5efb5448f5610adf92a23b9e718f5a`. 기존 v3 freeze 파일 SHA256 `c4f40b5d10a9a87b7ae7edc82c45cc77e51696e850c43f72c73c4ff77f73bc6a`. 자산 배포 권리의 미해결 상태를 승계하며 mesh/가중치를 추가 게시하지 않는다.

## 설치와 API

Ubuntu-24.04 WSL에서 dpkg-query 확인:

- MoveIt/MoveItPy/OMPL/kinematics/simple-controller-manager 2.12.4 설치.
- moveit_msgs 2.6.0 설치.
- TRAC-IK plugin/lib 2.0.2 설치.
- 기존 추론 venv에서 MuJoCo 3.13.0 import 확인.

실제 Python introspection에서 PlanningComponent는 plan/set_goal_state 등을 제공하지만 `execute`, `compute_cartesian_path`가 없다. `MoveItPy.execute`가 실행 인터페이스다. `GetCartesianPath.Request`에는 avoid_collisions, max_step, joint jump thresholds, velocity/acceleration scaling 필드가 있다. 원고의 개념 코드를 그대로 실행 파일로 복사하면 실패한다. 정확한 서비스 응답·타이밍·전체 경로 충돌 판정은 M3 부품 시험에서 확인한다.

공식 참고: [MoveIt Python API](https://moveit.picknik.ai/main/doc/examples/motion_planning_python_api/motion_planning_python_api_tutorial.html), [controller 구성](https://moveit.picknik.ai/main/doc/examples/controller_configuration/controller_configuration_tutorial.html). 웹 문서는 Rolling이므로 설치된 Jazzy API 확인을 우선했다.

## 실제 연결 공백과 다음 단계

소스에서 READY 약0.15wall초 후 회수·shutdown, joint1 시험 입력의 매 physics step 덮어쓰기, 팔 속도까지 포함한 정착 판정, 모든 group5 환경-로봇 접촉 차단, 정적 box target을 재확인했다. RGB-D red_point는 표면점이다. 기존 요약 PASS를 새 session 조작 권한이나 물체 중심으로 재사용할 수 없다.

[설계안](SECTION_13_6_REUSE_DESIGN_KO.md)에 실행 경로·모드·권한·부품 시험·제안 수치를 작성했다. M0 조사로 실제 팔 동작 가능 범위나 물리 파지 성공을 입증하지 않았다. 설계 승인 뒤 writing-plans로 세부 구현 계획을 작성하고, 요청한 executing-plans를 적용해 단일 작업자로 M1부터 진행한다.
