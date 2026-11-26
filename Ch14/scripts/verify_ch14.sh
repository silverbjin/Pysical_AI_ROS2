#!/usr/bin/env bash
set -Eeuo pipefail
root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
repo="$(dirname "$root")"
check=build; reuse=; source_sha=; headless=0; rights=0; enabled=0
while (($#)); do
 case "$1" in
 --profile) [[ "${2:-}" == cpu ]] || exit 2; shift 2;;
 --headless) headless=1;shift;;
 --check) check="${2:?}";shift 2;;
 --source-sha) source_sha="${2:?}";shift 2;;
 --reuse) reuse="${2:?}";shift 2;;
 --acknowledge-assets) rights=1;shift;;
 --enable-sim-control) enabled=1;shift;;
 *) echo "BLOCKED unsupported option $1" >&2;exit 2;;
 esac
done
[[ "$headless" == 1 && "$source_sha" =~ ^[0-9a-f]{40}$ ]] || { echo 'BLOCKED: explicit --headless and --source-sha required' >&2;exit 2; }
case "$check" in build|perception|mujoco|gazebo|all) ;; *) echo 'BLOCKED unsupported check';exit 2;; esac
actual="$(git -C "$repo" rev-parse HEAD)"
[[ "$actual" == "$source_sha" && -z "$(git -C "$repo" status --porcelain --untracked-files=all)" ]] || { echo 'BLOCKED: SHA drift or dirty tree' >&2;exit 2; }
base="${HOME}/ch14-owner"
mkdir -p "$base"
run="$(mktemp -d "$base/run_$(date -u +%Y%m%dT%H%M%SZ)_XXXXXX")"
out="$run/evidence";mkdir "$out"
container=; stage=preflight; actual=UNKNOWN
host_kind=LINUX_REHEARSAL_ONLY
if grep -qiE "microsoft.*wsl2|wsl2.*microsoft" /proc/sys/kernel/osrelease; then host_kind=WSL2_OWNER_REVIEW_REQUIRED; fi
finish(){
 raw_rc=$?;rc="$raw_rc";trap - EXIT;set +e
 case "$rc" in 0|1|2|130) ;; *) rc=1;; esac
 if [[ -n "$container" ]]; then docker rm -f "$container" >/dev/null 2>&1; fi
 python3 - "$out" "$rc" "$stage" "$source_sha" "$check" "$actual" "$raw_rc" "$host_kind" <<'PY'
import json,sys,pathlib
out,rc,stage,sha,check,actual,raw_rc,host_kind=sys.argv[1:];rc=int(rc)
pathlib.Path(out,"owner-result.json").write_text(json.dumps(dict(status="SCOPED_PASS" if rc==0 else "BLOCKED" if rc==2 else "CANCELLED" if rc==130 else "FAIL",exit_code=rc,stage=stage,source_sha=sha,actual_source_sha=actual,raw_exit_code=int(raw_rc),check=check,level=host_kind,full_release="HOLD",gui="NOT_RUN"),indent=2)+"\n")
PY
 # The asset directory and original model archive are deliberately excluded.
 (cd "$out" && find . -type f ! -name sha256sums.txt -print0 | sort -z | xargs -0 -r sha256sum > sha256sums.txt)
 tar -czf "$run/evidence.tar.gz" -C "$out" . && sha256sum "$run/evidence.tar.gz" > "$run/evidence.tar.gz.sha256" || rc=1
 echo "CH14_OWNER_EVIDENCE=$run/evidence.tar.gz"
 exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT TERM
actual="$(git -C "$repo" rev-parse HEAD)"
printf '%s\n' "$actual" > "$out/source-sha.txt"
[[ "$actual" == "$source_sha" && -z "$(git -C "$repo" status --porcelain --untracked-files=all)" ]] || { echo 'BLOCKED: SHA drift or dirty tree' >&2; exit 2; }
sha256sum "$root/scripts/"{bootstrap,doctor,verify_ch14,run_lab}.sh > "$out/scripts-sha256.txt"
(cd "$repo" && bash "$root/scripts/doctor.sh" --profile cpu) > "$out/host.log" 2>&1 || { cat "$out/host.log"; exit 2; }
python3 "$root/scripts/g09_audit.py" --out "$out/audit.json"
if [[ "$check" == perception || "$check" == all ]]; then
 [[ "$rights" == 1 ]] || { echo 'BLOCKED: external asset terms must be reviewed and acknowledged';exit 2; }
fi
if [[ "$check" == mujoco || "$check" == gazebo || "$check" == all ]]; then
 [[ "$enabled" == 1 && -n "$reuse" ]] || { echo 'BLOCKED: --enable-sim-control and exact G07 ZIP required';exit 2; }
 reuse="$(realpath "$reuse")"
 echo "c8defc1a154c3d0ec92ddd3a7fbd70f8d3b012dc21d375acde9f5c5f9be9641d  $reuse" | sha256sum -c - || exit 2
 mkdir "$run/reuse"
 python3 -m zipfile -e "$reuse" "$run/reuse"
 python3 "$root/scripts/g07_verify_reuse.py" --root "$run/reuse" | tee "$out/reuse.json"
fi
mkdir -p "$base/wheelhouse"
image='ros@sha256:5147d3ae250ce754afd399f6bfec15b33dd4e473ca357e30432a3182031bfad6'
gzimage='ghcr.io/silverbjin/pysical-ai-book-gazebo@sha256:8288028a25df2dee0f8a4980231b0b9594bfd1048cdab9fc8ac49298e079e82f'
run_one(){
 local name="$1" script="$2" img="$3";shift 3
 stage="$name";mkdir "$out/$name"
 container="ch14-owner-$(basename "$run" | tr '[:upper:]' '[:lower:]')-$name"
 echo "$img" > "$out/$name/image.txt"
 timeout --signal=TERM --kill-after=15s 1200s docker run --name "$container" --rm --init --shm-size=1g -v "$root:/ch14:ro" -v "$base/wheelhouse:/wheelhouse" -v "$out/$name:/evidence" "$@" "$img" bash "/ch14/scripts/$script" 2>&1 | tee "$out/$name/run.log"
 container=
 python3 - "$out/$name" <<'PY'
import sys,json,pathlib
p=pathlib.Path(sys.argv[1]);stage=p/"stage.json";result=p/"result.json"
if stage.exists():
 d=json.loads(stage.read_text());assert d["stage"]=="complete" and d["exit_code"]==0,d
if result.exists():
 d=json.loads(result.read_text());assert d["status"]=="PASS",d
else:assert stage.exists()
PY
}
case "$check" in build|all) run_one build g09_clean_build_ci.sh "$image";; esac
case "$check" in perception|all)
 stage=assets
 python3 "$root/scripts/g03_fetch_scene_assets.py" "$run/assets" "$out/scene-receipt.json"
 run_one perception g03_gazebo_ci.sh "$gzimage" -v "$run/assets:/assets:ro";; esac
case "$check" in mujoco|all) run_one mujoco g08_mujoco_ci.sh "$image" -v "$run/reuse:/reuse:ro";; esac
case "$check" in gazebo|all) run_one gazebo g08_gazebo_ci.sh "$image" -v "$run/reuse:/reuse:ro";; esac
stage=complete
