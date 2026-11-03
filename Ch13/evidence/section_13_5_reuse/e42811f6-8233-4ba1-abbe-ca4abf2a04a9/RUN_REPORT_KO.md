# e42811f6-8233-4ba1-abbe-ca4abf2a04a9 실행 보고서

- 시나리오: `free`
- 실제 실행: `FAIL` / 독립 검증: `NOT_RUN`
- terminal: `6` / cancel ACK: `None`
- 실제 목표 오차: `None` m / `None` rad
- terminal 뒤 정착: `None` wall s
- 엔진: `22.145999999998605` sim s / `32.433945300000005` wall s / force-cap ratio `1.0`
- 정상 종료: `True` / RX join: `True` / upstream join: `True`
- 자식 정상 회수: `10/10` / 잔여: `[]` / 후검사: `PASS`

검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.

## 최초 실행 오류

```text
Traceback (most recent call last):
  File "/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse/Ch13/scripts/reuse_13_5/run_navigation_probe.py", line 113, in main
    expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
                                                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('unexpected terminal', 6, {'phase': 'ACTIVE', 'fault': '', 'stamp_ns': 22100000000, 'vx': 0.135, 'wz': 0.0, 'output_held': False, 'origin': 'controller_source_via_smoother', 'frames_ready': True, 'vision_capture_ns': 0, 'vision_capture_age_wall_s': None, 'vision_fault_record': None, 'samples': {'tf': {'stamp_ns': 22100000000, 'receipt_wall': 58.3073991, 'gid': '010fb405ab0462530000000000001703'}, 'scan': {'stamp_ns': 22110000000, 'receipt_wall': 58.3188585, 'gid': '010fb405ab0462530000000000002003'}, 'nav': {'stamp_ns': 22100000000, 'receipt_wall': 58.3231672, 'gid': '010fb405ad0431380000000000006303'}, 'smooth': {'stamp_ns': 22100000000, 'receipt_wall': 58.3280839, 'gid': '010fb405ae04eb830000000000002003'}}}, {'mode': 'ARMED', 'fault': '', 'stamp_ns': 22100000000, 'clock_ns': 22120000000, 'origin': 'source_command', 'decision_wall': 58.3458345, 'source_receipts': {'base': {'stamp_ns': 22120000000, 'receipt_wall': 58.3301623, 'gid': '010fb405ab0462530000000000001403'}, 'joints': {'stamp_ns': 22120000000, 'receipt_wall': 58.3302569, 'gid': '010fb405ab0462530000000000001603'}, 'raw': {'stamp_ns': 22100000000, 'receipt_wall': 58.3313428, 'gid': '010fb405a904abaf0000000000001303'}}, 'counts': {'clock': 1, 'raw': 1, 'base': 1, 'joints': 1, 'relay': 1}, 'ready_for_arm': False})

```
