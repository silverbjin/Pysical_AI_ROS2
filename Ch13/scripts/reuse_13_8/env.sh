#!/usr/bin/env bash
set -eo pipefail
validation_repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
export CH13_REUSE_BUILD=${CH13_REUSE_BUILD:-/home/jinho/ch13_reuse_13_8_build}
/usr/bin/python3 "$validation_repo/Ch13/ros2_ws/src/ch13_system_validation/ch13_system_validation/tools.py" "$CH13_REUSE_BUILD" >/dev/null
exec bash "$validation_repo/Ch13/scripts/reuse_13_7/env.sh" "$@"
