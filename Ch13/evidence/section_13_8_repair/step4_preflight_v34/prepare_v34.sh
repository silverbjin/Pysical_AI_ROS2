#!/usr/bin/env bash
set -eo pipefail
repo="$(pwd)"
prep="$repo/../section_13_8_preparation_20261104"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_BUILD_v34.json"
bash Ch13/scripts/reuse_13_8/rebuild.sh
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/audit_install.py "$prep/install_audit_v34.json"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/freeze_runtime.py write Ch13/dependencies/section_13_8_system_v34.json
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/stage_runtime.py --manifest "$repo/Ch13/dependencies/section_13_8_system_v34.json" --output "$prep/runtime_stage_v34.json"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_ENGINE_v34.json"

bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/stage_component_sources.py > "$prep/components_v34.log" 2>&1
