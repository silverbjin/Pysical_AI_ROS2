# 59268844-61a3-4d8e-a21f-c1127788a454 실행 보고서

- 시나리오: `vision`
- 실제 실행: `FAIL` / 독립 검증: `NOT_RUN`
- terminal: `6` / cancel ACK: `None`
- 실제 목표 오차: `None` m / `None` rad
- terminal 뒤 정착: `None` wall s
- 엔진: `22.773999999998257` sim s / `42.24134482100001` wall s / force-cap ratio `1.0`
- 정상 종료: `True` / RX join: `True` / upstream join: `True`
- 자식 정상 회수: `11/11` / 잔여: `[]` / 후검사: `PASS`

검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.

## 최초 실행 오류

```text
Traceback (most recent call last):
  File "/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse/Ch13/scripts/reuse_13_5/run_navigation_probe.py", line 113, in main
    expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
                                                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('unexpected terminal', 6, {'phase': 'ACTIVE', 'fault': '', 'stamp_ns': 22722000000, 'vx': 0.15, 'wz': 0.022328733168512856, 'output_held': False, 'origin': 'controller_source_via_smoother', 'frames_ready': True, 'vision_capture_ns': 22722000000, 'vision_capture_age_wall_s': 0.11541386900000816, 'vision_fault_record': None, 'samples': {'scan': {'stamp_ns': 22740000000, 'receipt_wall': 244.928704957, 'gid': '010fb4059d0a1ec80000000000002003'}, 'tf': {'stamp_ns': 22760000000, 'receipt_wall': 244.994461139, 'gid': '010fb4059d0a1ec80000000000001703'}, 'nav': {'stamp_ns': 22746000000, 'receipt_wall': 244.973649845, 'gid': '010fb4059f0ac1ca0000000000006303'}, 'smooth': {'stamp_ns': 22722000000, 'receipt_wall': 244.970501545, 'gid': '010fb405a20a43b40000000000002003'}}}, {'mode': 'ARMED', 'fault': '', 'stamp_ns': 22722000000, 'clock_ns': 22760000000, 'origin': 'source_command', 'decision_wall': 244.997813738, 'source_receipts': {'joints': {'stamp_ns': 22760000000, 'receipt_wall': 244.987568641, 'gid': '010fb4059d0a1ec80000000000001603'}, 'base': {'stamp_ns': 22760000000, 'receipt_wall': 244.987173141, 'gid': '010fb4059d0a1ec80000000000001403'}, 'raw': {'stamp_ns': 22722000000, 'receipt_wall': 244.977920043, 'gid': '010fb4059a0a61ce0000000000001303'}}, 'counts': {'clock': 1, 'raw': 1, 'base': 1, 'joints': 1, 'relay': 1}, 'ready_for_arm': False})

```
