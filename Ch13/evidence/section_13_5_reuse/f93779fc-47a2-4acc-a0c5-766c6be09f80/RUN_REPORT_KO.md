# f93779fc-47a2-4acc-a0c5-766c6be09f80 실행 보고서

- 시나리오: `vision`
- 실제 실행: `FAIL` / 독립 검증: `NOT_RUN`
- terminal: `5` / cancel ACK: `None`
- 실제 목표 오차: `None` m / `None` rad
- terminal 뒤 정착: `None` wall s
- 엔진: `10.112000000000046` sim s / `29.98516580200001` wall s / force-cap ratio `1.0`
- 정상 종료: `True` / RX join: `True` / upstream join: `True`
- 자식 정상 회수: `11/11` / 잔여: `[]` / 후검사: `PASS`

검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.

## 최초 실행 오류

```text
Traceback (most recent call last):
  File "/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_reuse/Ch13/scripts/reuse_13_5/run_navigation_probe.py", line 107, in main
    expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
                                                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('unexpected terminal', 5, {'phase': 'FAULT', 'fault': 'VISION_EXPIRED', 'stamp_ns': 9242000000, 'vx': 0.0, 'wz': 0.0, 'origin': 'generated_zero', 'frames_ready': True, 'vision_capture_ns': 9228000000, 'vision_capture_age_wall_s': 0.32991889300001276, 'vision_fault_record': {'decision_wall': 273.977397398, 'clock_ns': 9242000000, 'sample': [9228000000, 273.667483285], 'fault': 'VISION_EXPIRED'}, 'samples': {'tf': {'stamp_ns': 9240000000, 'receipt_wall': 273.870740583, 'gid': '010fb405e50a92700000000000001703'}, 'scan': {'stamp_ns': 9242000000, 'receipt_wall': 273.953180685, 'gid': '010fb405e50a92700000000000002003'}, 'nav': {'stamp_ns': 9240000000, 'receipt_wall': 273.85666999, 'gid': '010fb405e70a4b120000000000006303'}, 'smooth': {'stamp_ns': 9240000000, 'receipt_wall': 273.889770241, 'gid': '010fb405ea0ab2c20000000000002003'}}}, {'mode': 'ARMED', 'fault': '', 'stamp_ns': 9242000000, 'clock_ns': 9242000000, 'origin': 'source_command', 'decision_wall': 273.982225527, 'source_receipts': {'joints': {'stamp_ns': 9240000000, 'receipt_wall': 273.837977009, 'gid': '010fb405e50a92700000000000001603'}, 'base': {'stamp_ns': 9240000000, 'receipt_wall': 273.838165379, 'gid': '010fb405e50a92700000000000001403'}, 'raw': {'stamp_ns': 9242000000, 'receipt_wall': 273.97968184, 'gid': '010fb405e20ac5d50000000000001303'}}, 'counts': {'clock': 1, 'raw': 1, 'base': 1, 'joints': 1, 'relay': 1}, 'ready_for_arm': False})

```
