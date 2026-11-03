# vision 실행 보고서

- 시나리오: `vision`
- 실제 실행: `FAIL` / 독립 검증: `NOT_RUN`
- terminal: `5` / cancel ACK: `None`
- 실제 목표 오차: `None` m / `None` rad
- terminal 뒤 정착: `None` wall s
- 엔진: `4.733999999999701` sim s / `10.576370363999999` wall s / force-cap ratio `1.0`
- 정상 종료: `True` / RX join: `True` / upstream join: `True`
- 자식 정상 회수: `11/11` / 잔여: `[]` / 후검사: `NOT_RUN`

검사 결과와 원본 수치는 같은 디렉터리의 JSON/JSONL을 따른다. FAIL을 성공으로 재해석하지 않는다.

## 최초 실행 오류

```text
Traceback (most recent call last):
  File "/mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2_guide_validation_20261103/Ch13/scripts/reuse_13_5/run_navigation_probe.py", line 113, in main
    expected=6 if args.case=='blocked' else (5 if args.case in ['cancel','raw_loss'] else 4);assert terminal.status==expected,('unexpected terminal',terminal.status,boundary,gateway)
                                                                                                    ^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ('unexpected terminal', 5, {'phase': 'FAULT', 'fault': 'VISION_EXPIRED', 'stamp_ns': 3686000000, 'vx': 0.0, 'wz': 0.0, 'output_held': False, 'origin': 'generated_zero', 'frames_ready': True, 'vision_capture_ns': 3658000000, 'vision_capture_age_wall_s': 0.34740576200000817, 'vision_fault_record': {'decision_wall': 82.846433822, 'clock_ns': 3686000000, 'sample': [3658000000, 82.532281187], 'fault': 'VISION_EXPIRED'}, 'samples': {'tf': {'stamp_ns': 3686000000, 'receipt_wall': 82.783197431, 'gid': '010fb405790600ef0000000000001703'}, 'scan': {'stamp_ns': 3688000000, 'receipt_wall': 82.796501482, 'gid': '010fb405790600ef0000000000002003'}, 'nav': {'stamp_ns': 3686000000, 'receipt_wall': 82.782320068, 'gid': '010fb4057b06bb6e0000000000006303'}, 'smooth': {'stamp_ns': 3682000000, 'receipt_wall': 82.7306568, 'gid': '010fb4057c06c2970000000000002003'}}}, {'mode': 'ARMED', 'fault': '', 'stamp_ns': 3682000000, 'clock_ns': 3686000000, 'origin': 'source_command', 'decision_wall': 82.820612387, 'source_receipts': {'joints': {'stamp_ns': 3686000000, 'receipt_wall': 82.758869935, 'gid': '010fb405790600ef0000000000001603'}, 'raw': {'stamp_ns': 3682000000, 'receipt_wall': 82.760100385, 'gid': '010fb40576063fee0000000000001303'}, 'base': {'stamp_ns': 3686000000, 'receipt_wall': 82.759045628, 'gid': '010fb405790600ef0000000000001403'}}, 'counts': {'clock': 1, 'raw': 1, 'base': 1, 'joints': 1, 'relay': 1}, 'safe_watermark_ns': 3682000000, 'ready_for_arm': False})

```
