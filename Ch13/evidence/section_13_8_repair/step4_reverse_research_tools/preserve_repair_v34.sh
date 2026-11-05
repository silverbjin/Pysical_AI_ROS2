#!/usr/bin/env bash
set -eo pipefail
repo="$(pwd)"
prep="$repo/../section_13_8_preparation_20261104"
case_dir="$repo/Ch13/evidence/section_13_8_system/9e160887-cc8a-4f1d-a4e7-83aae4f77818"
bash Ch13/scripts/reuse_13_8/env.sh "$prep/preserve_native_case.py" "$case_dir" /home/jinho/ch13_reuse_13_8_build/live_source_e1f5a8d81daa48d2b8337ae08f5253e2/repo source_v34
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/archive_evidence.py "$case_dir"