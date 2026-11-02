# 예: 실패한 것이 vision인 경우
export RUN_OUT="$VISION_OUT"
bash Ch13/scripts/reuse_13_5/env_r2.sh \
  Ch13/scripts/reuse_13_5/inspect_r2_residuals.py \
  "$RUN_OUT/residual_recheck_$(python3 -c 'import uuid; print(uuid.uuid4().hex[:8])').json"
bash Ch13/scripts/reuse_13_5/env_r2.sh \
  Ch13/scripts/reuse_13_5/write_run_report.py "$RUN_OUT"
tail -n 35 "$RUN_OUT/probe_stdout.log"
