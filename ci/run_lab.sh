#!/usr/bin/env bash
# Bounded CI adapter for a single real guide command sequence.
set -Eeuo pipefail
if (( $# != 3 )); then
  echo "Usage: bash ci/run_lab.sh ChXX section path-to-lab-script" >&2
  exit 2
fi
CHAPTER="$1"
SECTION="$2"
SCRIPT="$3"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="ci-results/$CHAPTER/$SECTION"
mkdir -p "$OUT"
test -f "$SCRIPT"
START="$(date +%s)"
set +e
timeout --signal=TERM --kill-after=15s 20m bash "$SCRIPT" 2>&1 | tee "$OUT/run.log"
RC="$?"
set -e
END="$(date +%s)"
python3 - "$OUT" "$CHAPTER" "$SECTION" "$RC" "$((END - START))" <<'PY'
import json
import os
from pathlib import Path
import sys

out, chapter, section, rc, elapsed = sys.argv[1:]
out = Path(out)
rc = int(rc)
status = "PASS" if rc == 0 else "FAIL"
report = {
    "chapter": chapter,
    "section": section,
    "source_sha": os.environ.get("GITHUB_SHA", "LOCAL_UNCOMMITTED"),
    "guide": chapter + "/docs/LAB_" + section.replace(".", "_") + "_GUIDE_KO.md",
    "verdict": status,
    "runtime_scope": "bounded CI pilot, not entire chapter",
    "exit_code": rc,
    "elapsed_seconds": int(elapsed),
    "evidence_log": "run.log",
}
(out / "result.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
(out / "SUMMARY.md").write_text(
    "# " + chapter + " section " + section + " pilot\n\n"
    + "Verdict: **" + status + "** (exit=" + str(rc) + ")\n\n"
    + "Scope: selected guide commands only; chapter overall **NOT_RUN**.\n\n"
    + "Source: " + report["source_sha"] + "\n"
    + "Elapsed: " + elapsed + " s\n",
    encoding="utf-8",
)
PY
exit "$RC"
