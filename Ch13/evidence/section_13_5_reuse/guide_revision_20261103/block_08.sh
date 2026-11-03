export LAB_EVIDENCE="$EVIDENCE_ROOT/student_$(date +%Y%m%d_%H%M%S)_$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])')"
mkdir -p "$LAB_EVIDENCE"
printf '%s\n' "$LAB_EVIDENCE" > "$REUSE_WORK/current_lab.txt"

bash Ch13/scripts/reuse_13_5/build_r2.sh
source "$HOME/physicalai_13_5/lab_env.sh"
bash Ch13/scripts/reuse_13_5/env_r2.sh \
  Ch13/scripts/reuse_13_5/audit_r2_install.py "$LAB_EVIDENCE/install_audit.json"
bash Ch13/scripts/reuse_13_5/test_r2.sh "$LAB_EVIDENCE/tests.log"
