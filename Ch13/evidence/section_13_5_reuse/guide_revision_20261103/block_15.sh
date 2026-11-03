bash Ch13/scripts/reuse_13_5/env_r2.sh - <<'PY_PARAMS'
from pathlib import Path
import json, yaml
from ament_index_python.packages import get_package_share_directory
share = Path(get_package_share_directory('ch13_navigation_reuse'))
cfg = yaml.safe_load((share/'config/nav2_params.yaml').read_text())
for name in ['global_costmap', 'local_costmap']:
    p = cfg[name][name]['ros__parameters']
    print(name, 'footprint=', p['footprint'])
    print('inflation=', p['inflation_layer'])
print('smoother=', cfg['velocity_smoother']['ros__parameters'])
PY_PARAMS
