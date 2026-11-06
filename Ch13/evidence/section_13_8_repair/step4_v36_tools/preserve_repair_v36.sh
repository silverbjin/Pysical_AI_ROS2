#!/usr/bin/env bash
set -eo pipefail
repo="$(pwd)"
prep="$repo/../section_13_8_preparation_20261104"
for id in d0611273-5f74-47a8-b108-12d189dbd523 40299e00-3e7a-4d6c-9311-a0f2b03de912; do
 case_dir="$repo/Ch13/evidence/section_13_8_system/$id"
 bash Ch13/scripts/reuse_13_8/env.sh "$prep/preserve_native_case.py" "$case_dir" /home/jinho/ch13_reuse_13_8_build/live_source_e4daf46330e14c6285d2ad879ca878d3/repo source_v36
 bash Ch13/scripts/reuse_13_8/env.sh Ch13/scripts/reuse_13_8/archive_evidence.py "$case_dir"
done
