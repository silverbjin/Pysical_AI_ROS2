export FREE_OUT="$LAB_EVIDENCE/free"
printf '%s\n' "$FREE_OUT" > "$REUSE_WORK/current_run.txt"
bash Ch13/scripts/reuse_13_5/run_navigation.sh free "$FREE_OUT"
