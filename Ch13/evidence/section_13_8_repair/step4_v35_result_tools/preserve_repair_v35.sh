#!/usr/bin/env bash
set -eo pipefail
repo="$(pwd)"
prep="$repo/../section_13_8_preparation_20261104"
for id in dfcd2bc6-d8d1-44f3-b0cc-a0634bbba959 272870f5-e785-4d52-8b08-e966cf65d738; do
 case_dir="$repo/Ch13/evidence/section_13_8_system/$id"
 bash Ch13/scripts/reuse_13_8/env.sh "$prep/preserve_native_case.py" "$case_dir" /home/jinho/ch13_reuse_13_8_build/live_source_dafeaa8e75e24d87be97ec20d6c17f96/repo source_v35
 bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/archive_evidence.py "$case_dir"
done
