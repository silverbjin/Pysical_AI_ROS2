# 13.4 completion evidence

Work UUID: f8c0bed5-cdac-43d8-81ff-84ab88360cdb. Starting HEAD:
64f6c0ce91637e90ef44f1dc9c49c7d747adc91f. This directory retains failures,
diagnostics and successive frozen acceptance batches; a later PASS never
rewrites an earlier failed result. See the Korean completion ledger/report.

## Latest evidence (2026-10-22)

Final acceptance is **PASS**. `final-v5/FINAL_ACCEPTANCE_SUMMARY.json` audits all
22 native results and the two passing supplement legacy results, including
every original artifact hash and actual action result. `FINAL_POST_TRIAL_AUDIT.json`
confirms 168 current source files, all 380 unchanged installed files, no live
engine/runtime, and the clean pinned external underlay. The one failed v5 legacy
trial remains explicitly listed; it has not been relabeled or hidden.

`final-v5/` contains all 22 native trials: original 20-case matrix plus two
additional Gazebo tracking reliability trials. Its manifest pins implementation
commit `f2fa0eba4c042b00bb70f15b4066869ed370d84f`, 167 source files and 380 installed
files, with every source byte archived. All 22 native results are PASS; the
first legacy MuJoCo rehearsal failed because the synthetic input was 56ms ahead
of the server's consumed clock. That FAIL and normal shutdown logs are retained.

`legacy-clock-final/` is the affected-test supplement, not a replacement of that
failure. Only `verify_architecture_13_3.py` and its new regression differ from
the native freeze: one 100ms input preparation delay preserves the original
header and sends once. Runtime, native trial scripts and all installed bytes
are unchanged. Its manifest/after-audit must pass, and both real engines must
pass before the combined collector can declare acceptance. Read actual results;
the directory's existence is not a PASS.

`source-final-v5-probe.log/.xml`: 374 source tests passed. The earlier
`source-final-v5` had 373 tests; `package-final-v5-result.log` records 199 package
tests with zero errors/failures/skips. Package results and installed bytes were
not changed by the probe-only supplement.

Exact execution wrappers are archived in `workflow-final-v5/` and
`workflow-final-v5-priority/` (same 22 cases, different priority order). The
supplement helpers are archived in `workflow-legacy-clock-final/`. Actual
ordinary-user WSL invocations from the repository root:

```text
bash .superpowers/sdd/2026-10-21-completion/verify-final-v5.sh
bash .superpowers/sdd/2026-10-21-completion/legacy-clock-final.sh
```

The first invocation stopped at the preserved legacy failure. The second runs
the complete source suite, freezes only the allowed two-file delta, then runs
the original legacy workflow against MuJoCo and Gazebo sequentially. It never
restarts an engine while an owned process remains. The collector invocation is:

```text
python Ch13/evidence/section_13_4/completion-f8c0bed5/collect_final.py Ch13/evidence/section_13_4/completion-f8c0bed5/final-v5 Ch13/evidence/section_13_4/completion-f8c0bed5/legacy-clock-final
```

`collect_final_before_probe_supplement.py` preserves the earlier collector.
The updated collector explicitly includes the failed legacy trial in its
derived summary and proves the supplement changes no runtime or installed byte.
It still requires every native check and every actual command/cancel terminal.
It writes `FINAL_ACCEPTANCE_SUMMARY.json` once and never rewrites verdicts.

## Execution/provenance

`workflow/` is a byte-for-byte archive of the local ignored helpers from
`.superpowers/sdd/2026-10-21-completion/` at final-v3 execution. These helpers
record the actual host-specific workspace/venv/build/install paths, not a
portable installer. The portable build and trial instructions are in
`Ch13/docs/LAB_13_4_GUIDE_KO.md`. A fresh run requires fresh UUID/output/build
paths; never reuse or overwrite these evidence directories.

Actual host invocation (ordinary WSL user jinho, no sudo/admin):

```text
wsl -d Ubuntu-24.04 -u jinho -- bash -lc 'cd /mnt/c/Users/Jinho/.codex/.chatgpt-projects/g-p-6ad1e56cf8f881919fe23e1ab94d2855/work/Pysical_AI_ROS2 && bash .superpowers/sdd/2026-10-21-completion/verify-final-v3.sh'
```

`verify-final-v3.sh` runs source tests, package tests/installation audit, a new
freeze and geometry/tracking/remaining/legacy stages in order. Native commands,
UUIDs, child PIDs, residual checks and results are retained in each batch's
progress/runner logs and each trial's result/source_snapshot/system log.
`frozen-source.json` pins working bytes AND installed files, not just dirty HEAD.
The driver checks these hashes before/after every native trial and stops on
the first FAIL. The original 20 native cases are retained; two additional
Gazebo tracking runs establish three consecutive trials on that engine.

The original unchanged workflow reused by the helpers is
`../egl-424240ff/workflow/native-matrix.py` and `legacy.py`. New helper wrappers
retain those paths in source. Diagnostic `action-trial.sh` alone loads the
ordinary-user RCL forwarding interposer. Frozen acceptance does NOT preload it.
`action_boundary_result_only.c` preserves the initial result-only source hash
recorded in earlier compile logs; `action_boundary.c` adds goal boundaries.
No compiled interposer is required by the product package.

`workflow-final-v4/`, `workflow-final-v4b/`, and `workflow-final-v4c/` preserve
successive exact helper snapshots (including the six-package build). The v4
source gate failed two outdated test assumptions; v4b was intentionally stopped
before any native engine after self-review found the original computed-target
wall TTL missing. These are not completed acceptance batches. The v4c driver
rebuilds the wall-TTL fix, runs source/package/install gates, then freezes a new
`final-v4/` native batch. Read its actual progress/verdict; its existence alone
does not mean acceptance passed. No diagnostic interposer is used by that driver.

## Interpretation

`final/` stopped after the pre-control baseline defect; `final-v2/` stopped at
the first 15Hz response stall. Both remain failures. Intermediate transport,
OpenCV and servo tests are diagnostics, not substitutes for the frozen matrix.
Read each result's status and required_checks rather than counting directories.

`candidate_paths.py` joins original diagnostics/trace/target receipts by capture.
Missing telemetry is explicitly unknown/partial, never inferred callback absence.
`window_analysis.py` and `incident_summary.py` extract selected failure windows.
`collect_final.py` performs an additional read-only acceptance/actual-action-result
audit and writes a new derived summary only if all its assertions hold.
It does not edit native results, exclude failing runs, or relax required checks.

PPO loaded walking, MoveIt, physical grasp, Nav2/13.5 and real hardware are not
tested here. Motion/delay geometry uses the explicit arm-camera motion fixture.
