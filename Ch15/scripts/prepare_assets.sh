#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# == 2 ]] || { echo 'usage: prepare_assets.sh NEW_LOCAL_TARGET RECEIPT'; exit 2; }
python3 "$here/python/g05_lock.py" "$here"
# Only the approved, exact 94-file closure, never a nested clone or redistribution.
python3 "$here/scripts/prepare_native_assets.py" --target "$1" --receipt "$2"
