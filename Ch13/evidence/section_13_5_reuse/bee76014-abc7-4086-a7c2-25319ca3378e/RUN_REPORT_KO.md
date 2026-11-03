# bee76014-abc7-4086-a7c2-25319ca3378e 실행 보고서

- 시나리오: `obstacle`
- 실제 실행: `FAIL` / 독립 검증: `NOT_RUN`
- terminal: `6` / cancel ACK: `None`
- 실제 목표 오차: `None` m / `None` rad
- terminal 뒤 정착: `None` wall s
- 엔진: `22.401999999998463` sim s / `32.00392192700001` wall s / force-cap ratio `1.0`
- 정상 종료: `True` / RX join: `True` / upstream join: `True`
- 자식 정상 회수: `10/10` / 잔여: `[]` / 후검사: `PASS`

검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.

## 최초 실행 오류

```text
Traceback (most recent call last):
  File "/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse/Ch13/scripts/reuse_13_5/run_navigation_probe.py", line 113, in main
    expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
                                                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('unexpected terminal', 6, {'phase': 'ACTIVE', 'fault': '', 'stamp_ns': 22320000000, 'vx': 0.0, 'wz': 0.025, 'output_held': False, 'origin': 'controller_source_via_smoother', 'frames_ready': True, 'vision_capture_ns': 0, 'vision_capture_age_wall_s': None, 'vision_fault_record': None, 'samples': {'tf': {'stamp_ns': 22360000000, 'receipt_wall': 113.591750456, 'gid': '010fb4050b06b43e0000000000001703'}, 'scan': {'stamp_ns': 22346000000, 'receipt_wall': 113.571365042, 'gid': '010fb4050b06b43e0000000000002003'}, 'nav': {'stamp_ns': 22360000000, 'receipt_wall': 113.597635953, 'gid': '010fb4050d06bb430000000000006303'}, 'smooth': {'stamp_ns': 22320000000, 'receipt_wall': 113.572292451, 'gid': '010fb4050e06a1290000000000002003'}}}, {'mode': 'ARMED', 'fault': '', 'stamp_ns': 22320000000, 'clock_ns': 22360000000, 'origin': 'source_command', 'decision_wall': 113.607887068, 'source_receipts': {'joints': {'stamp_ns': 22360000000, 'receipt_wall': 113.586669054, 'gid': '010fb4050b06b43e0000000000001603'}, 'raw': {'stamp_ns': 22320000000, 'receipt_wall': 113.581610155, 'gid': '010fb40509069fe10000000000001303'}, 'base': {'stamp_ns': 22360000000, 'receipt_wall': 113.586487433, 'gid': '010fb4050b06b43e0000000000001403'}}, 'counts': {'clock': 1, 'raw': 1, 'base': 1, 'joints': 1, 'relay': 1}, 'ready_for_arm': False})

```
