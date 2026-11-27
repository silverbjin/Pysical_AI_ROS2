#!/usr/bin/env bash
# Temporary per-instance tracing only. No clock write, service change or package install.
set -euo pipefail
umask 077
seconds=180
out=$(mktemp -d "$HOME/ch15-clock-writer.XXXXXXXX")
inst=
archive="$out.tar.gz"
finish() {
  rc=$?
  trap - EXIT INT TERM
  set +e
  if [[ -n "$inst" ]]; then
    sudo -n sh -c 'echo 0 > "$1/tracing_on"' _ "$inst" 2>>"$out/errors.log"
    sudo -n cat "$inst/trace" >"$out/trace.txt" 2>>"$out/errors.log"
    sudo -n sh -c 'for e in "$1"/events/syscalls/sys_enter_*/enable; do test ! -f "$e" || echo 0 > "$e"; done; rmdir "$1"' _ "$inst" 2>>"$out/errors.log"
    if sudo -n test -d "$inst"; then echo 'TRACE_INSTANCE_REMAINS' >>"$out/errors.log"; rc=1; fi
  fi
  printf 'exit=%s\nacceptance=NOT_EVALUATED\n' "$rc" >"$out/status.txt"
  (cd "$out" && find . -type f ! -name manifest.sha256 -print0 | sort -z | xargs -0 sha256sum >manifest.sha256)
  tar -czf "$archive" -C "$out" .
  sha256sum "$archive" >"$archive.sha256"
  printf '\nTRACE_EVIDENCE=%s\nSHA256=%s.sha256\n' "$archive" "$archive"
  exit "$rc"
}
trap finish EXIT
trap 'exit 130' INT TERM
echo "Read-only clock queries and temporary per-instance kernel syscall tracing."
echo "No time/service configuration changes. Do not run a mission."
sudo -v
base=
for p in /sys/kernel/tracing /sys/kernel/debug/tracing; do
  if sudo -n test -d "$p/instances"; then base=$p; break; fi
done
[[ -n "$base" ]] || { echo 'TRACEFS_NOT_AVAILABLE' >"$out/errors.log"; exit 2; }
candidate="$base/instances/ch15_clock_$(cat /proc/sys/kernel/random/uuid)"
sudo -n mkdir "$candidate"
inst=$candidate
sudo -n sh -c 'echo 0 > "$1/tracing_on"' _ "$inst"
sudo -n cat "$inst/trace_clock" >"$out/trace-clock-before.txt"
if grep -qw mono "$out/trace-clock-before.txt"; then
  sudo -n sh -c 'echo mono > "$1/trace_clock"' _ "$inst"
fi
sudo -n cat "$inst/trace_clock" >"$out/trace-clock.txt"
enabled=0
for syscall in adjtimex clock_adjtime clock_settime settimeofday; do
  for kind in enter exit; do
    e="$inst/events/syscalls/sys_${kind}_$syscall"
    if sudo -n test -f "$e/enable"; then
      sudo -n cat "$e/format" >"$out/sys_${kind}_$syscall.format"
      sudo -n sh -c 'echo 1 > "$1/enable"' _ "$e"
      [[ "$kind" != enter ]] || enabled=$((enabled+1))
    fi
  done
done
[[ "$enabled" -gt 0 ]] || { echo 'SYSCALL_TRACEPOINTS_NOT_AVAILABLE' >"$out/errors.log"; exit 2; }
ps -eo pid,ppid,comm,args >"$out/processes-before.txt"
sudo -n sh -c 'echo 1 > "$1/tracing_on"' _ "$inst"
# Query only: struct timex modes=0, no library/package installation.
python3 - "$seconds" <<'PY' >"$out/samples.jsonl"
import ctypes, json, sys, time
class TV(ctypes.Structure):
    _fields_=[("tv_sec",ctypes.c_long),("tv_usec",ctypes.c_long)]
class Timex(ctypes.Structure):
    _fields_=[("modes",ctypes.c_uint),("offset",ctypes.c_long),("freq",ctypes.c_long),("maxerror",ctypes.c_long),("esterror",ctypes.c_long),("status",ctypes.c_int),("constant",ctypes.c_long),("precision",ctypes.c_long),("tolerance",ctypes.c_long),("time",TV),("tick",ctypes.c_long),("ppsfreq",ctypes.c_long),("jitter",ctypes.c_long),("shift",ctypes.c_int),("stabil",ctypes.c_long),("jitcnt",ctypes.c_long),("calcnt",ctypes.c_long),("errcnt",ctypes.c_long),("stbcnt",ctypes.c_long),("padding",ctypes.c_int*11)]
if ctypes.sizeof(Timex)!=208 or ctypes.sizeof(ctypes.c_long)!=8:
    raise SystemExit("TIMEX_ABI_NOT_SUPPORTED")
libc=ctypes.CDLL(None,use_errno=True)
libc.adjtimex.argtypes=[ctypes.POINTER(Timex)]
libc.adjtimex.restype=ctypes.c_int
end=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)+int(sys.argv[1])*10**9
while time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW)<end:
    tx=Timex()
    a=time.monotonic_ns(); state=libc.adjtimex(ctypes.byref(tx)); b=time.monotonic_ns()
    if state<0: raise OSError(ctypes.get_errno(),"adjtimex read")
    print(json.dumps(dict(m0=a,m1=b,raw_ns=time.clock_gettime_ns(time.CLOCK_MONOTONIC_RAW),realtime_ns=time.time_ns(),tick_us=tx.tick,freq_ppm=tx.freq/65536,state=state,status=tx.status)),flush=True)
    time.sleep(.25)
PY
ps -eo pid,ppid,comm,args >"$out/processes-after.txt"
echo 'TRACE_CAPTURE_COMPLETE_REVIEW_REQUIRED'
