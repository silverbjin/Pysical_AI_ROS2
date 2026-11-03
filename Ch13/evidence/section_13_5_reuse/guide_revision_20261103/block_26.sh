export MATRIX_OUT="$EVIDENCE_ROOT/student_matrix_$(python3 -c 'import uuid; print(uuid.uuid4())')"
cp Ch13/docs/SECTION_13_5_REUSE_R5_REPORT_KO.md "$LAB_EVIDENCE/published_reference_report.md"
bash Ch13/scripts/reuse_13_5/env_r2.sh \
  Ch13/scripts/reuse_13_5/run_acceptance.py \
  --freeze "$REUSE_REPO/Ch13/dependencies/section_13_5_reuse_acceptance_v3.json" \
  --out "$MATRIX_OUT"
python3 - "$MATRIX_OUT" <<'PY_MATRIX'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
m = json.loads((p/'matrix.json').read_text())
v = json.loads((p/'verification.json').read_text())
print(m['result'], v['result'])
for row in m['cases']:
    print(row['case'], row['uuid'], row['exit_code'], row['post_cleanup_exit_code'])
assert m['result'] == v['result'] == 'PASS' and len(m['cases']) == 6
PY_MATRIX
