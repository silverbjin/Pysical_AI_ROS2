#!/usr/bin/env bash
set -Eeuo pipefail
here="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
root="$(dirname "$here")"
: "${CH14_IMAGE:=ch14-ai:cpu}"
: "${CH14_WHEELHOUSE:=$root/.wheelhouse}"
mkdir -p "$CH14_WHEELHOUSE"
cmp "$root/requirements/cpu.lock.txt" "$here/requirements-cpu.txt"
docker info >/dev/null
DOCKER_BUILDKIT=1 docker build --build-context "wheels=$(realpath "$CH14_WHEELHOUSE")" -f "$here/Dockerfile.cpu" -t "$CH14_IMAGE" "$root"
