# 15.4 CI 디버깅 사례 — 실제 PR #207
## 현상 (RED)
PR #206 run 45825072895 job139927013907, earlier 45817052187 same boundary. Book Lab Acceptance unittest discovery failed importing test_ch07_77_target_gate with ModuleNotFoundError: vision_basics.
## 최초 실패 경계
Test inserts Ch07/ros2_ws/src/vision_basics in sys.path and imports vision_basics.mission_target_gate. The two required source files existed on main but non-cone sparse checkout did not include them. Not a ROS runtime failure.
## 수정 후보
Add precisely package __init__.py and mission_target_gate.py to non-cone sparse paths; no test skip or application source change. Actual PR #207, head 6e516e5520915d362be34fc289b33b8d3aa5ce84.
## GREEN
Run 45828900636 / job139940138580 actual SUCCESS, 14/14 units (including six Ch07 target-gate tests), guide inventory/link and 101-guide matrix PASS. Two manual-only runtime pilots skipped. Ch07 §7.7 BLOCKED preserved. No physical rerun.
## 실습
1. 테스트에서 import 경로와 필요한 파일을 추적한다.
2. 파일이 원격에 존재하는 것과 CI checkout에 존재하는 것을 구별한다.
3. 최소 수정으로 테스트를 살리고 원본 실패를 보존한다.
4. 자신의 PR에서 RED/GREEN run과 scope를 기입한다.
- [PR #207](https://github.com/silverbjin/Pysical_AI_ROS2/pull/207)
- [GREEN run](https://github.com/silverbjin/Pysical_AI_ROS2/actions/runs/45828900636)
