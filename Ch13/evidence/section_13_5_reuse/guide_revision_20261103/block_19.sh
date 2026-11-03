export VISION_OUT="$LAB_EVIDENCE/vision"
printf '%s\n' "$VISION_OUT" > "$REUSE_WORK/current_run.txt"
bash Ch13/scripts/reuse_13_5/run_navigation.sh vision "$VISION_OUT" 15
