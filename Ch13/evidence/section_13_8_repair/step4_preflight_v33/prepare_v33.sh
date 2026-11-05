#!/usr/bin/env bash
set -eo pipefail
repo="$(pwd)"
prep="$repo/../section_13_8_preparation_20261104"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_BUILD_v33.json"
bash Ch13/scripts/reuse_13_8/rebuild.sh
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/audit_install.py "$prep/install_audit_v33.json"
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/freeze_runtime.py write Ch13/dependencies/section_13_8_system_v33.json
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/stage_runtime.py --manifest "$repo/Ch13/dependencies/section_13_8_system_v33.json" --output "$prep/runtime_stage_v33.json"
python3 Ch13/scripts/reuse_13_5/inspect_r2_residuals.py "$prep/BEFORE_ENGINE_v33.json"

bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/stage_component_sources.py > "$prep/components_v33.log" 2>&1
