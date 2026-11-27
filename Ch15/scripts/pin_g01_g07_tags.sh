#!/usr/bin/env bash
# Run from an authenticated clone. Only the seven approved fixed refs can be created.
set -euo pipefail
case "$(git remote get-url origin)" in
  https://github.com/silverbjin/Pysical_AI_ROS2|https://github.com/silverbjin/Pysical_AI_ROS2.git|git@github.com:silverbjin/Pysical_AI_ROS2.git|ssh://git@github.com/silverbjin/Pysical_AI_ROS2.git) ;;
  *) echo WRONG_ORIGIN >&2; exit 2;;
esac
git fetch --no-tags origin feat/ch15-mission-engineering
pins=$(cat <<'PINS'
ch15-g01-scoped-v1 92f50d6c1dba7814c9952bce74da4e94bb510583
ch15-g02-scoped-v1 1501416d5e399ee308c4ba38b6e4cb78c8e6d185
ch15-g03-mock-v1 30fa2fa012404ba83d110e308e201eeda5bf5d6c
ch15-g04-basic-v1 0f67d0222a9737ddc07c447a35a9be50ed2e761d
ch15-g05-evidence-v1 d4405ebb7d65aecb9d54e3d124da6bb31d699509
ch15-g06-visualization-v1 00e6e2d33b616dcd9e93891e9431e19ed824cfb4
ch15-g07-joint-v1 d05c67b1e88e06e5323722403e459afa6eaa2027
PINS
)
remote="$(git ls-remote --refs --tags origin 'refs/tags/ch15-*')"
specs=()
while read -r tag sha; do
  test "$(git cat-file -t "$sha")" = commit
  git merge-base --is-ancestor "$sha" FETCH_HEAD
  existing="$(awk -v r="refs/tags/$tag" '$2==r{print $1}' <<< "$remote")"
  if [[ -n "$existing" && "$existing" != "$sha" ]]; then
    echo "TAG_DRIFT $tag" >&2; exit 2
  fi
  if [[ -z "$existing" ]]; then specs+=("$sha:refs/tags/$tag"); fi
done <<< "$pins"
if (( ${#specs[@]} )); then git push --atomic origin "${specs[@]}"; fi
remote="$(git ls-remote --refs --tags origin 'refs/tags/ch15-*')"
while read -r tag sha; do
  actual="$(awk -v r="refs/tags/$tag" '$2==r{print $1}' <<< "$remote")"
  test "$actual" = "$sha"
  echo "TAG_VERIFIED $tag $sha"
done <<< "$pins"
echo CH15_FIXED_TAGS_PASS
