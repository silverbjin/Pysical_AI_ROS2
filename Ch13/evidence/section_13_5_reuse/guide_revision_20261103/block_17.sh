bash Ch13/scripts/reuse_13_5/env_r2.sh - <<'PY_SLEW'
import inspect
from ch13_navigation_reuse.safety import Guard
print(inspect.getsource(Guard.output))
PY_SLEW
bash Ch13/scripts/reuse_13_5/env_r2.sh -m unittest discover \
  -s "$REUSE_PKG/test" -p test_slew_clock.py -v
bash Ch13/scripts/reuse_13_5/env_r2.sh -m unittest discover \
  -s "$REUSE_PKG/test" -p test_safe_handoff.py -v
