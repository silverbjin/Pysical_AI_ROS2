# Ch15 G08 FMEA — mock-only scope

| ID | 주입 경계 | 기대 판정 | 추가 검수 |
|---|---|---|---|
| F01 | NAVIGATING / scan_receipt_loss | ABORTED | last_scan_receipt, guard, zero, uuid_terminal |
| F02 | NAVIGATING / obstacle_fixture | BLOCK_OR_REPLAN | blocked, replan_requested |
| F03 | SEARCHING / target_missing | COMPLETED_OR_ABORTED | attempt, fresh_target, original_task_verified |
| F04 | APPROACHING / stale_or_wrong_epoch_target | ABORTED | invalid_target, pick_goals_zero |
| F05 | MANIPULATING / ik_unavailable | BLOCKED | new_goal_zero |
| F06 | MANIPULATING / pick_aborted_false | ABORTED | uuid_terminal, fresh_after_settle, attempt |
| F07 | NAVIGATING / stop_heartbeat_loss | LATCHED | last_heartbeat, blocked, zero, no_resume |
| F08 | ANY_ACTIVE / invalid_tilt_or_height | BLOCKED | hold, self_righting_zero |
| F09 | ANY_ACTIVE / virtual_battery_below20 | ABORTED | blocked, automatic_rth_zero |
| F10 | ANY_ACTIVE / clock_pause_or_rewind | BLOCKED | invalid_epoch, steady_watchdog, no_resume |

모든 run은 별도 UUID와 fixture SHA를 기록. 주입 요청 자체는 증거가 아니며 독립 관측 필요. F01 실제 receipt와 source stale 분리, F07 heartbeat와 zero 관측. G08-1 pure RetryBudget은 prepare 실패 포함 총3회, terminal/settled/fresh/safe 필요, recovery 자체 성공으로 task 완료 금지. 기존 MissionExecutor 아직 연결하지 않음. G08-2 isolated DDS는 실제 설치 노드, fixture만 사용. UUID/MCAP/전체 미션은 후속 검수. 물리 F01 BLOCKED_PHYSICAL_FAULT, 원본 안전 계약 및 G04~07 유지.

## 실제 판정 (2026-11-27)
F01 active mock nav 실제 ABORTED/UUID terminal6, native receipt→guard337.987ms / internal block→zero publish0.067793ms; independent paused receipt timeout and heartbeat no-resume PASS. F03 transient/persistent actual PASS(2/3 attempts). F04 82 invalid observations, pick0, ABORTED. F06 3 exact terminal6 UUID, fresh/settle/terminal3/3, ABORTED. F02/F05/F07/F08/F09/F10 L0 deterministic only (F07 also actual isolated DDS). Physical F01 BLOCKED; Spin/BackUp/Wait installed declaration+library audit only, no motion. [최종 보고서](reports/G08_FINAL_ACCEPTANCE_KO.md).
