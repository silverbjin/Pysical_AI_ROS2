#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d)"; trap 'rm -rf "$work"' EXIT
export GIT_AUTHOR_NAME=Student GIT_AUTHOR_EMAIL=student@example.invalid GIT_COMMITTER_NAME=Student GIT_COMMITTER_EMAIL=student@example.invalid
git init --bare --initial-branch=main "$work/remote.git"
git clone "$work/remote.git" "$work/a"; cd "$work/a"
printf 'base\n' > contract.txt; git add .; git commit -m baseline; git push origin main
git clone "$work/remote.git" "$work/b"; cd "$work/b"; git switch -c feature/student
printf 'student\n' > contract.txt; git commit -am student
cd "$work/a"; printf 'main\n' > contract.txt; git commit -am main; git push origin main
cd "$work/b"; git fetch origin; if git merge origin/main; then echo 'expected conflict missing'; exit 1; fi
git ls-files -u; grep -q '^<<<<<<<' contract.txt
printf 'main + student\n' > contract.txt; git add contract.txt; git commit -m resolve; git push origin feature/student
git lfs install --local; git lfs track '*.fixture'; printf 'small synthetic fixture\n' > test.fixture; git add .gitattributes test.fixture; git commit -m lfs-fixture
git show HEAD:test.fixture | tee "$work/pointer"; grep -q '^version https://git-lfs.github.com/spec/v1$' "$work/pointer"; grep -q '^oid sha256:' "$work/pointer"; git lfs fsck
echo G05_GIT_CONFLICT_LFS_PASS
