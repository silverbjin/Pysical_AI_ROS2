# eb4cf77b-ae6c-4e27-812f-d54d88f43503 실행 보고서

- 시나리오: `free`
- 실제 실행: `FAIL` / 독립 검증: `NOT_RUN`
- terminal: `5` / cancel ACK: `None`
- 실제 목표 오차: `None` m / `None` rad
- terminal 뒤 정착: `None` wall s
- 엔진: `2.149999999999985` sim s / `3.247171900000005` wall s / force-cap ratio `1.0`
- 정상 종료: `True` / RX join: `True` / upstream join: `True`
- 자식 정상 회수: `10/10` / 잔여: `[]` / 후검사: `PASS`

검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.

## 최초 실행 오류

```text
Traceback (most recent call last):
  File "/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse/Ch13/scripts/reuse_13_5/run_navigation_probe.py", line 107, in main
    expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
                                                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('unexpected terminal', 5, {'phase': 'WAITING', 'fault': '', 'stamp_ns': 2040000000, 'vx': 0.0, 'wz': 0.0, 'origin': 'generated_zero', 'frames_ready': True, 'vision_capture_ns': 0, 'vision_capture_age_wall_s': None, 'vision_fault_record': None, 'samples': {'tf': {'stamp_ns': 2040000000, 'receipt_wall': 36.2141357, 'gid': '010fb405b0047e410000000000001703'}, 'scan': {'stamp_ns': 1908000000, 'receipt_wall': 36.0179333, 'gid': '010fb405b0047e410000000000002003'}}}, {'mode': 'FAULT', 'fault': 'INPUT_OR_CLOCK_TIMEOUT', 'stamp_ns': 2120000000, 'clock_ns': 2120000000, 'origin': 'generated_safety_zero', 'decision_wall': 36.3590995, 'source_receipts': {'raw': {'stamp_ns': 1900000000, 'receipt_wall': 36.0020802, 'gid': '010fb405ae046d060000000000001303'}, 'joints': {'stamp_ns': 2100000000, 'receipt_wall': 36.2922426, 'gid': '010fb405b0047e410000000000001603'}, 'base': {'stamp_ns': 2100000000, 'receipt_wall': 36.2919191, 'gid': '010fb405b0047e410000000000001403'}}, 'counts': {'clock': 1, 'raw': 1, 'base': 1, 'joints': 1, 'relay': 1}, 'ready_for_arm': False})

```
