#!/usr/bin/env bash
set -Eeuo pipefail
[[ "${1:-}" == "--profile" && "${2:-}" == cpu && $# == 2 ]] || { echo 'Usage: doctor.sh --profile cpu' >&2; exit 2; }
source /etc/os-release
[[ "$ID" == ubuntu && "$VERSION_ID" == 24.04 && "$(uname -m)" == x86_64 ]] || { echo 'BLOCKED: Ubuntu 24.04 x86_64 required' >&2; exit 2; }
for c in git python3 docker timeout sha256sum tar; do command -v "$c" >/dev/null || { echo "BLOCKED missing $c" >&2; exit 2; }; done
[[ "$(python3 -c 'import sys;print(".".join(map(str,sys.version_info[:2])))')" == 3.12 ]] || { echo 'BLOCKED Python 3.12' >&2; exit 2; }
[[ "$PWD" != /mnt/[a-z]/* ]] || { echo 'BLOCKED: use WSL Linux filesystem' >&2; exit 2; }
docker info --format '{{.ServerVersion}}' || exit 2
docker version
uname -a
df -h .
echo 'G09_HOST_PREFLIGHT_PASS (not L3 acceptance)'
