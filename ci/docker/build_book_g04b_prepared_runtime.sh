#!/usr/bin/env bash
# Explicit one-time release, NOT a per-PR action. No image publish by default.
set -Eeuo pipefail
repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
: "${G04B_IMAGE_REPOSITORY:=ghcr.io/silverbjin/pysical-ai-book-gazebo-prepared}"
: "${G04B_IMAGE_TAG:=20261115-candidate}"
image="${G04B_IMAGE_REPOSITORY}:${G04B_IMAGE_TAG}"
command -v docker >/dev/null || { echo G04B_DOCKER_REQUIRED;exit 20; }
test -f "$repo_root/ci/docker/Dockerfile.book-g04b-prepared"
echo "G04B_BUILD_SOURCE_SHA=$(git -C "$repo_root" rev-parse HEAD)"
docker build --pull --file "$repo_root/ci/docker/Dockerfile.book-g04b-prepared" --tag "$image" "$repo_root"
docker run --rm --pull=never --entrypoint bash "$image" /usr/local/bin/check_book_g04b_prepared_runtime.sh
if [[ "${G04B_PUBLISH_PREPARED_IMAGE:-NO}" != "YES" ]];then
  echo "G04B_BUILD_ONLY_NO_PUBLISH image=$image"
  echo 'Set G04B_PUBLISH_PREPARED_IMAGE=YES only after approval and matching CI dependencies.'
  exit 0
fi
docker push "$image"
digest_ref="$(docker image inspect --format '{{index .RepoDigests 0}}' "$image")"
case "$digest_ref" in
  "$G04B_IMAGE_REPOSITORY"@sha256:*) ;;
  *) echo "G04B_DIGEST_NOT_VERIFIED: $digest_ref" >&2;exit 30;;
esac
echo "G04B_PREPARED_RUNTIME_PIN=$digest_ref"
echo 'Do not change the G04B CI pin until full identical-image static+L2/Owner parity evidence is reviewed.'
