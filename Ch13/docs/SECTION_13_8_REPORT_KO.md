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
| 설치/child 감사 | 기존 navigation34·manipulation24·BT6 감사 및 현재4개 Python 패키지53모듈 소스 바이트 일치, 외부94자산 hash PASS, 실제 venv child NumPy 우선순위 PASS |
| 부품 회귀 | 동일 hash WSL native source/fixture 사본에서278 PASS/34.47초 |
| 최초 연속 engine | UUID a96cd6d7-9805-41ce-9dff-4c13916e4653, v2, FAIL. 파지 물리 PASS 후 귀환 회전 중 원통 부분 가림에 따른 OBSERVATION_EXPIRED. --no-bag 개발 사례. 실제 정상 shutdown·12 child clean exit·worker/rx/upstream join·잔여0·lock free |
| 두 번째 연속 engine | UUID34f5ef1d-8fee-4d81-913b-fa76a3945a47, v4, FAIL. 파지 물리 PASS 후 귀환 navigation VISION_EXPIRED/Nav2 ABORTED. producer 비전 fault 없음·5327관측. 새 camera health 검증과 혼합 native FIFO 반영 사이의 경계를 분석해13.8용 경로 분리. 정상 회수 |
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
