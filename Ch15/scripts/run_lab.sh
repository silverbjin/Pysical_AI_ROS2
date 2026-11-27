#!/usr/bin/env bash
set -euo pipefail
here="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
[[ $# -ge 1 ]] || exit 2
section="$1";shift
[[ "$section" =~ ^15\.[1-9]$ ]] || exit 2
n="${section#15.}"
profile= bag= scenario= ack=0 gui=0 guide=0
while (( $# )); do
 case "$1" in
  --profile) [[ $# -ge 2 ]] || exit 2;profile="$2";shift 2;;
  --bag) [[ $# -ge 2 ]] || exit 2;bag="$2";shift 2;;
  --scenario) [[ $# -ge 2 ]] || exit 2;scenario="$2";shift 2;;
  --acknowledge-assets) ack=1;shift;;
  --gui) gui=1;shift;;
  --guide) guide=1;shift;;
  *) exit 2;;
 esac
done
if (( guide ));then [[ -z "$profile$bag$scenario" && "$ack$gui" == 00 ]] || exit 2;cat "$here/docs/LAB_15_${n}_GUIDE_KO.md";echo CH15_GUIDE_ONLY_NOT_RUNTIME;exit 0;fi
case "$n:$profile" in
 1:mock) check=design;;
 2:mock) check=icd;;
 3:mock) check=mock;;
 3:physical_basic) check=physical_basic;;
 4:) check=git;;
 5:) check=analysis;[[ -n "$bag" ]] || exit 2;;
 6:) check=markers;;
 7:joint) check=joint;;
 8:mock) check=faults;[[ -n "$scenario" ]] || exit 2;;
 *) echo CH15_LAB_ARGUMENT_BLOCKED;exit 2;;
esac
if (( gui ));then
  [[ "$n" == 6 && -n "$bag" ]] || exit 2
  echo 'CH15_GUI_OWNER_ONLY: use separate WSLg installed overlay; see LAB_15_6_GUIDE_KO.md. GUI not a headless PASS.'
  exit 2
fi
[[ -z "$bag" || "$check" == analysis || "$check" == markers ]] || exit 2
# Marker fixture is not bag playback. Explicit bag runs the typed observation replay first.
if [[ "$check" == markers && -n "$bag" ]]; then
  bash "$here/scripts/verify_ch15.sh" --check analysis --bag "$bag" --headless
fi
args=(--check "$check" --headless)
if [[ "$check" == analysis ]];then args+=(--bag "$bag");fi
if [[ -n "$scenario" ]];then args+=(--scenario "$scenario");fi
if (( ack ));then args+=(--acknowledge-assets);fi
exec bash "$here/scripts/verify_ch15.sh" "${args[@]}"
