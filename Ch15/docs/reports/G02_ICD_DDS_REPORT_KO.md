# G02 ICD·Mock DDS·Readiness 개발 보고서
## 목표 및 계약
C03~C06, IF01~19 중 G02 대상. 2 action/1 service/5 msg, ROS Jazzy 4 신규/진행 패키지 설치 후보. 실제 임무 supervisor/BT는 G03, 전체 6 패키지 build는 G05. 실제 Ch13 연결 금지.
## RED→GREEN
로컬 Python 3.13.5 unittest test_g02_contract: RED import missing (1 error), GREEN 4/4 (pose/frame/quaternion, timeout, readiness 3 consecutive, heartbeat loss and latch/reset). 검증한 pure source blobs 2860a9b758d9a8dfe3bf7145910b4ae961e401cd 및 test 9fd3375e32cb3afe80c6aa2d3ee34d91020ce71a. 실제 ROS build/DDS는 미검증 상태에서 CI로 넘긴다.
## 구현
Mock Action server admits one goal, checks state/pose/timeout, nav actual mock arbiter output samples, pick/place explicit held/placed state transitions; feedback and cancellation. No physical success. Sensor watchdog steady 50ms, source 300ms and receipt 1s, true latch, arbiter sole /cmd_vel 20Hz. Readiness endpoints/sensor/TF/heartbeat/owner plus optional lifecycle query; startup blocked. Reset RPC intentionally rejects until G03/G08 terminal idle witness. TF and scans are mock. G02 launch auto_start=false only, no start service.
## 검수 경계
DDS real action feedback/result/gait and QoS, readiness negatives are required; no claim until logs reviewed. Active lifecycle fixture, full reset, exact UUID supervisor, recovery timing, physical stop remain later tests. G00/G01 prior run successful, do not rerun. Public source only; external asset and publication HOLD; license field TODO pending owner review.
