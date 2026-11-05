#!/usr/bin/env bash
set -eo pipefail
repo="$(pwd)"
prep="$repo/../section_13_8_preparation_20261104"
case_dir="$repo/Ch13/evidence/section_13_8_system/02676843-e611-4161-89d0-16d71df94863"
bash Ch13/scripts/reuse_13_8/env.sh "$prep/preserve_native_case.py" "$case_dir" /home/jinho/ch13_reuse_13_8_build/live_source_1c99a02a26604e14974346ea17f02dc7/repo source_v32
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/archive_evidence.py "$case_dir"
bash Ch13/scripts/reuse_13_8/env.sh "$prep/preserve_native_case.py" "$repo/Ch13/evidence/section_13_8_system/9590b5a2-052a-49d3-9d54-e97fe7c1d374" /home/jinho/ch13_reuse_13_8_build/live_source_1c99a02a26604e14974346ea17f02dc7/repo source_v32
bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/archive_evidence.py "$repo/Ch13/evidence/section_13_8_system/9590b5a2-052a-49d3-9d54-e97fe7c1d374"
