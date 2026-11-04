# 13.8 개발 및 검증 보고서

2026-11-04 KST. 단일 작업자. **개발 진행 중이며 전체 원고 인수가 완료된 상태가 아니다.**

## 진행 방식

사용자가 제공한13.8 원고를 확보하고 로컬13.7/v7에서 격리했다. 공식 문서·GitHub의 설치 버전에 맞는 구현을 먼저 확인한 뒤 작은 부품→단일 engine의 가장 불확실한 연속 임무→월드/반복 평가 순서로 진행한다. 방법·근거·실패와 변경 판단은 SECTION_13_8_PROGRESS_KO.md에 계속 기록한다.

## 소스와 환경

- 기준13ecb58d346f38778ac8015d3c2321d20c9971e0에서 work/Pysical_AI_ROS2_13_8, feat/ch13-section-13-8 생성. 최초 구현 checkpoint98a6523f. 원격 push/PR/main 병합 없음.
- 새 ch13_system_validation과 기존 코드의 opt-in hook을 사용한다. 기존13.7/13.6 실행의 기본 동작은 유지하는 방향으로 부품 회귀를 확인했다.
- build /home/jinho/ch13_reuse_13_8_build. 기존 venv·외부94자산과 sibling 공유 engine lock을 재사용한다. 전역 설치·OS/드라이버/시간 설정 변경 없음.
- v1은 최초 preflight source305/asset94 동결. 최초 실제 실행은 v2 source308/asset94, SHA256 7f7a2c7caff92d63eeec33f997790a2462dbf667ee2c3460889e6eb0ce1a8012.

## 현재 검증 결과

| 항목 | 결과와 한계 |
|---|---|
| 원고 확보 | 제목/13.8.1~8 확보, 원본 사본 hash 기록 |
| 분리 build | 기존6+BT1+새1 패키지 성공 |
| 설치/child 감사 | v10 기준 navigation34·manipulation24·BT6 감사 및4개 Python 패키지58모듈 소스 바이트 일치, 외부94자산 hash PASS, 실제 venv child NumPy 우선순위 PASS |
| 부품 회귀 | v10 경계 깊이 검사·747자세 시야·보존/복원까지314 PASS/48.87초. 새 물리 인수와 구분 |
| 최초 연속 engine | UUID a96cd6d7-9805-41ce-9dff-4c13916e4653, v2, FAIL. 파지 물리 PASS 후 귀환 회전 중 원통 부분 가림에 따른 OBSERVATION_EXPIRED. --no-bag 개발 사례. 실제 정상 shutdown·12 child clean exit·worker/rx/upstream join·잔여0·lock free |
| 두 번째 연속 engine | UUID34f5ef1d-8fee-4d81-913b-fa76a3945a47, v4, FAIL. 파지 물리 PASS 후 귀환 navigation VISION_EXPIRED/Nav2 ABORTED. producer 비전 fault 없음·5327관측. 새 camera health 검증과 혼합 native FIFO 반영 사이의 경계를 분석해13.8용 경로 분리. 정상 회수 |
| 세 번째 연속 engine | UUID1499904c-2d19-4010-a499-03919ecdc832, v5, FAIL. pick100.493mm/2.22sim초/접촉100% PASS. Nav2 SUCCEEDED 뒤 base위치(0.01362,-0.01847)m, yaw2.24356rad로 잘못된 자세. PLACE_WAIT fresh3D 가림 만료. quaternion 일부 설정 오류를 수정 중이며 아직 재실행하지 않음.160.496sim초/415.889wall초, CPU46.05%, tilt0.04458rad, bag close/정상 회수 |
| 원고 Level1/2/3 | 개발 fixture와 별개. 실제 인수 미완료 |
| rosbag 실제 기록/재생 | v4 실패 사례의 MCAP131424메시지/필수12토픽 무결성 PASS. 별도domain136 sensor/BT replay reception PASS/16.46wall초. raw RGB-D 전체/비전·Nav2 알고리즘 전체 재생은 아님 |
| 고정 설정10회/목표 성능 | 미완료 |

## 실패와 효율 개선

새 부품 driver의 multiprocessing 재진입을 고쳤다. 이후 Windows mount에서의 전체 시험은269 PASS/3 FAIL, 카메라 한정 재확인은11 PASS/2 FAIL이었다.15초 camera 초기화 예산에 Windows 경로의 child import가 대부분을 사용했다. 기존 timeout/수명을 늘리지 않고 같은 hash 소스를 새 build 안의 WSL native 사본에서 실행해 카메라 시작3개를2.80초에 통과했다. native 전체 첫 실행의277 PASS/1 FAIL은 과거 MoveIt 로그 fixture 사본 누락이었다. 원본을 수정하지 않고 hash 확인 fixture 사본을 포함한 다음278 PASS였다. 실패를 숨기거나 테스트를 skip하지 않았다.

## 채택한 공식 패턴

MoveIt2.12.4 planning scene 서비스·attached/world 객체 처리, Jazzy rclpy의 비동기 send/cancel/result와 사용자 지정 goal UUID, rosbag2 0.26.11의 CDR 기록 구조, Jazzy topic별 QoS override를 참고했다. 출처/ref/파일·기존 코드와의 차이는 진행 기록에 있다. 운반 phase/권한 설계와 사후 물리 판정은 이 프로젝트의 추가 구현이며 upstream 패턴의 존재가 이 로봇의 물리 성공을 보증하지 않는다.

첫 사례는 최소100.016mm lift/2.20sim초 hold/양 접촉100% PASS였다. 귀환 회전14.60sim초 동안 최대 상대 slip4.274mm·양 접촉100%였고, RGB-D 원통의 충분한 높이 가시성 조건이 충족되지 않아3D 관측이 만료됐다. 이를 근거로 fixed-arm 운반과 정지 조작의 관측 권한을 분리하고 새 DDS capture-health와 fresh3D 재획득 시험을 추가했다. 만료된3D point의 원본 timestamp는 유지하며 새 권한으로 쓰지 않는다. v3의 실제 재검증은 아직 완료하지 않았다.

## 주장하지 않는 범위

교재의 콜라 일반 인식, 새로운 WBC·CoM 이동, 실기·SLAM/AMCL·Gazebo 동등 구현,99% 강건성을 검증하지 않았다. 원고120초/CPU70%/3cm/0.1rad는 목표이며 달성 전제로 timeout이나 원본 제어 한도를 완화하지 않는다. 파지 이후 새 engine을 시작하는 것을 연속 운반으로 집계하지 않는다.

## v6 수정 검증

귀환 quaternion 전체 성분을 설정하고, fresh3D 대기 중에도 잘못된 실제 귀환 자세를 별도 거부한다. 부분 원통 추정기의 평면 근거는 부족해 채택하지 않았다.13.8 opt-in 고정 camera를10cm 높이고 아래5도로 기울여 기존 검출 조건을 유지했다. 저장된 실제8개 자세의 렌더링 회귀와 기존 기본 mount 보존을 포함해299 PASS/49.03초.5-package rebuild18.8초, 설치56모듈·외부94자산·실제 venv child 감사 PASS. 정지 렌더링은 새 물리 실행 성공 증거가 아니다.

네 번째 실제 사례13ef4150-a1fc-4a55-8a47-f697f5507449는 시작8wall초 안에 새 관측을 확보하지 못해 이동·파지 전에 FAIL. 비전 accepted/rejected가 모두0, matched camera receipt/health도0이며 renderer192캡처·정상 종료였으므로 fit 가림 실패와 구분한다. trial4.76sim초/11.460wall초, bag close·worker/12 child 회수·잔여0. 추가 전달 경계 진단 중이다.

다섯 번째v7 사례b91a740e-a75f-4acb-b4fe-3cd5f68ad8b6는 실제 관측545개로 시작·이동·준비 action3개를 통과했지만, 다음 개방 요청 전에 heartbeat399.695ms 공백과 MISSION_EXPIRED로 FAIL. trial17.70sim초/41.652wall초·CPU43.734%·tilt0.034776rad·bag close/정상 회수. 동기 Planner 초기화 파일 조회의400ms 지연 시험을 RED로 재현하고 기존 compute worker와 owner polling을 적용했다. 실제 초기화 하위 단계별 소요 시간도 추가 기록한다. 전체300 PASS/43.98초이며 실제 파지/귀환/내려놓기의 인수는 아직 미완료다.

여섯 번째v8 사례e1c738a7-42a2-417b-9e66-4aa445bd9875는 같은 hash의 WSL native 사본/공유 lock으로 실행했다. 초기화·준비 구간을 통과했지만 접근 중간의 가림으로 OBSERVATION_EXPIRED, 전체FAIL.100.56sim초/240.879wall초·CPU44.443%·tilt0.034256rad·bag close/정상 회수.8개 정지 자세 회귀가 전체 접근을 대표하지 못했으므로 저장된 두 궤적의532자세로 회귀를 확대하고 있다. 실제 물체 파지는 시작하지 않았다.

일곱 번째v9 사례f50ddb77-4c68-4e37-8e0c-df8c9fae07a9도 접근 중 OBSERVATION_EXPIRED로FAIL.104.84sim초/239.398wall초·CPU43.223%·tilt0.035119rad·bag close/정상 회수. 실제 raw frame은 위/아래가 모두 보였지만 결합 surface RMS1.50279mm가1.5mm 한도를 넘었다. 예외 표시가 첫 조각의 높이 부족만 남겨 진단을 흐렸다. 분해한 실제 픽셀과 점군을 근거로13.8에만 앞쪽 물체 깊이가 섞인 경계 픽셀을 선별하고, 표면 한도·원본 capture/TF를 유지했다. 단순 mask 전체 erosion은 회귀2개 실패로 제외했다.

## v10 보존과 다음 실제 검증

v10 소스336/외부94자산, manifest SHA256 3e697f62ef429ae82cd4f82d54636898fea055a33f67576eb03d115ed21db832. build14.0초·설치58모듈/child 감사·native 사본 전수 hash/공유 lock realpath 확인 PASS. 기존7개 실제 개발 FAIL을 모델 제외raw.tar.gz/raw_manifest.json으로 압축했고 원본은 남겼다. v9 실제 archive를 새 빈 폴더에41파일 hash 복원해 원래trial/BT/nav/source verdict 바이트와FAIL을 보존했다. 복원은 새 engine 실행이나 성공 증거가 아니다. 현재7개 개발 사례는 고정 설정10회 평가가 아니며 전체 연속 미션 인수는 아직 미완료다.

## v10 연속 실행과 v11 분리 처리 후보

v10 첫 UUID8478db34는 startup FUTURE_SOURCE:joints로 실패했다. 동일 소스 재시도614e67e5는 파지 물리 PASS(최소100.418mm/2.18sim초/접촉100%) 후2.54233m 운반·정착·LOWER·지지·실측 개방까지 도달했다. 팔 후퇴의 Cartesian fraction0으로 전체 FAIL이며 post-release hold는 부족했다. 귀환 오차0.052002m·190.64sim초/397.698wall초로 원고 위치/시간 목표도 미달이다. CPU43.101%·최대 tilt0.039292rad, bag close/12자식 정상 종료/worker join/lock free. 이 개발 fixture는 원고 Level1/2/3 인수가 아니다.

팔에 붙인 장면 모델의 parent는reuse/tcp인데 분리 요청은reuse/link6이었다. 공식 MoveIt2.12.4 source 및 설치 API에서 outer success=true여도 attached가 남는 현상을 재현했다. ID-only 분리·GetPlanningScene 사후 검사·물리 release 후 새 RGB-D 중심 적용을 추가했다. 관련3개와 전체317개 회귀 PASS/48.11초. 별도domain136 설치 API probe PASS/정상 shutdown이지만 새 물리 성공은 아직 확인 전이다. 상세 판단과 자료 경로는 PROGRESS/RESEARCH에 남긴다.
