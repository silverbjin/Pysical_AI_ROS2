# R3–R5 공개 플랫폼 통합 실행 계획

> 단일 작업자. superpowers:executing-plans로 단계별 실행하며 각 단계 보고서·선택 commit·non-force push·원격 SHA를 기록한다.

**Goal:** 검증된 corrected A 플랫폼에 실제 Nav2 이동과 실제 RGB-D 기반 물체 접근을 연결하고 교재용 MuJoCo 인수·한글 문서를 마친다.
**Architecture:** 원본 정책/보완3개/모터cap/2ms물리는 유지한다. opt-in 장면 profile은 원본 static rough world만 평지·벽·작업물로 교체하며 모델의 몸체·질량·관절·actuator를 보존한다. 실제 mj_ray scan과 Renderer RGB-D를 추가하고 실제상태/TF로 Nav2를 구동한다. engine ground-truth localization임을 표시한다.
**Tech Stack:** 설치 확인된 Jazzy Nav2 1.3.13, MuJoCo3.13, 기존 CPU venv, rclpy/rclcpp. Nav2는시스템실행파일, 정책은기존venv. 새 학습·MoveIt·시스템변경 없음.
**Spec:** HANDOFF_SECTION_13_5_REUSE_REVISION_2026_11_02_KO.md R3–R5, SECTION_13_5_REUSE_EDUCATIONAL_GATES_KO.md, R2 완료 profile. 세부 구현은 이 계획의 판단이며 기존 승인 범위 안에서 진행한다.

## 사전 선택과 경계

- Nav2 controller/planner/bt_navigator/velocity_smoother/lifecycle_manager standalone 프로세스를 사용한다. Navfn + RegulatedPurePursuit, lateral/reverse0, vx최대0.20/wz최대0.20. Spin/BackUp recovery 미활성화. 실제 설치 header에서 enable_stamped_cmd_vel 지원을 확인했으므로 전체TwistStamped를명시한다.
- controller→Nav2 velocity smoother→Ch13 navigation boundary→기존gateway→platform. C++ ingress의 실제GID/최초receipt를 nav/smooth/scan/TF에도 보존한다. navigation boundary는 IDLE의 생성zero와 ACTIVE의원본stamp를구분하며 ACTIVE source/scan/TF손실에latch한다. terminal 이후에만IDLE전환. raw/safe직접우회 및 TF edge복수소유자를검사한다.
- footprint는 기존 실제 R2 관절 snapshot의 collision geometry AABB를 heading좌표에 투영해 측정하고 여유0.04m를 더해동결한다. 모든장애물은map에서보수적으로투영하며2Dscan높이로등반가능성을추정하지않는다.
- scan은 실제body에붙은frame에서 environment group에mj_ray를쏜다. 자기몸체/floor필터를명시하며실제ray결과만LaserScan으로발행한다. map은장면을알고만든prior,scan은실제관측으로구분한다.
- 카메라는base에실제추가한320×240 렌더. capture15simHz, 처리최대10Hz, 원본stamp/최초receipt/optical축/과거TF100ms/age300ms 유지. 기존13.4 pure geometry/contracts를선택빌드해재사용한다. 이실습은붉은작업물의색/깊이검출이며YOLO/일반객체인식으로표현하지않는다.
- 물체중심scene정답은관측노드에주지않는다. RGB/depth를독립수신하고동일capture시간의TF로역투영한다. 접근후보는실제팔mount와position-only IK·jointlimit·mapfootprint·경로비용으로평가한다. 팔파지/실행은범위밖이다.
- 도착은실제NavigateToPose terminal성공+실제root오차0.10m/0.10rad+edu_stop_v2정착 뒤 READY_FOR_MANIPULATION. cancelACK와terminalCANCELED는분리한다.

## Task R3: 실제 센서와 Nav2

Files: scene.py, sensors.py, navigation_boundary.py, nav_contract.py, config/nav2_params.yaml, config/navigate_no_recovery.xml, launch/navigation.launch.py, 기존platform_adapter/ingress/wire, scripts/run_navigation_probe.py.
- [x] RED: flat장면에서도원본robot구조동일, ray가실제장애물hit, 원본stamp/손실/복수TFedge/명령자/우회/미래와latch.
- [x] GREEN: 장면·센서·명령경계 최소구현, 고정footprint 산출, isolated build/install byte audit.
- [x] 실제 DDS→실제 Nav2 action→실제 engine의자유공간/우회/막힌경로/취소·정착·회수 확인. 수명/실패보고서와commit/push.

## Task R4: RGB-D와 작업 위치

Files: vision_approach.py, approach_geometry.py, readiness.py, camera지원, test/test_reuse_vision.py, run_navigation_probe.py vision profile.
- [x] RED: depth축/과거TF/age·미래/원본stamp보존, stale목표/관측손실·candidate도달불가·terminal/cancelACK오인.
- [x] GREEN: 13.4 geometry재사용, 실제RGB-D관측, 팔FK/IK후보평가와Nav2연결. 최신촬영TF와실제body진동보존.
- [x] 실제촬영→관측→goal→terminal→root오차→정착→READY를실행. 팔파지는하지않는다. 보고서·commit/push.

## Task R5: 동결 인수·본문·재현

Files: config/acceptance_v1.json, scripts/run_acceptance.py/verify_acceptance.py, docs/SECTION_13_5_REUSE_DESIGN_KO.md/LAB_13_5_REUSE_GUIDE_KO.md/SECTION_13_5_REUSE_REPORT_KO.md/REUSE_MANIFEST.md, lock.
- [x] 최종실행전 matrix/수치/source·설치hash동결. MuJoCo는순차실행, 빌드/검사동시실행금지.
- [x] physics 시나리오: 자유공간, 장애물우회, 막힌goal, goal취소, 실제vision접근, raw손실. wire부품: 중복/교체/TF우회/미래·만료goal/clockrollback·pause/관측손실. 각필수1회,3회반복은확장.
- [x] 기본도착0.10m/0.10rad, 정착edu_stop_v2, rawexpiry→zero0.35wall초/정착5sim·8wall초. Nav2시나리오예산90sim·240wall초, blocked/cancel은terminalと実測stopを別測定. 원래cap/非有限/넘어짐fail조건유지.
- [x] 소스변경영향별재실행, 원본실패보존. 기존13.3/13.4회귀와새플랫폼회귀분리. 설치단계와knownassetlicense한계를명시한한글본문·가이드·출처작성.
- [x] 단일작업자자체검토후보고서·commit/push·local/remoteSHA대조. main/PR없음.

## 검토 초점

느린sim에서wallfreshness를완화하지않음; Nav2가idle일때와제어원손실의구분; smoother가now로stamp를세탁하지않음; TF다중publisher허용과동일edge복수소유금지; renderer첫워밍업/종료; 관측점과장면정답분리; terminal받기전cancelACK로완료처리하지않음.

## 최종 실행 판정

2026-11-03 v3 고정본 여섯 실제 시나리오 전수/독립 검증 PASS. 신규89/기존관련순수50 PASS. v1/v2와 검증 누락은 보존했다. 실행 중 정착/age 허용치를 확대하지 않았고, 누락한 실제 움직임 증거를 추가했다. 새 OS 전체 재설치·기존전체 engine 회귀·3회 반복·Gazebo/실기는 검증 범위 밖이다. 최종 게시 확인은 R5 게시 보고서에 기록한다.
