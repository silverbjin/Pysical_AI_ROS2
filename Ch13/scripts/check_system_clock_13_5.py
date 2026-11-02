#!/usr/bin/env python3
"""Record original SYSTEM/MONOTONIC until one bounded quiet preflight completes.

Run once before a serial native validation session; never use it to retry a
failed engine or clear a receiver's clock-backstep latch. No ROS init occurs.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import time
from integrated_robot_navigation.clock_preflight import ClockStabilityGate


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output-dir',required=True)
    args=parser.parse_args();root=Path(args.output_dir).resolve();root.mkdir()
    gate=ClockStabilityGate()
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    module=Path(importlib.util.find_spec('integrated_robot_navigation.clock_preflight').origin).resolve()
    def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
    metadata=dict(uid=os.getuid(),pid=os.getpid(),boot_id=boot,kernel=platform.release(),
        command=[str(Path(__file__).resolve()),'--output-dir',str(root)],
        script_sha256=digest(Path(__file__)),module=str(module),module_sha256=digest(module),
        clocksource=Path('/sys/devices/system/clocksource/clocksource0/current_clocksource').read_text().strip(),
        writes_system_settings=False,creates_ros_receivers=False,engine_attempts=0)
    (root/'start.json').write_text(json.dumps(metadata,indent=2))
    print(json.dumps(dict(preflight=str(root),**metadata)),flush=True)
    maximum_span=0;samples=0
    with (root/'samples.jsonl').open('x') as output:
        while gate.state=='WAITING':
            before=time.monotonic_ns();system=time.time_ns();after=time.monotonic_ns()
            maximum_span=max(maximum_span,after-before);samples+=1
            result=gate.observe((before+after)//2,system)
            output.write(json.dumps(dict(wall_before_ns=before,system_ns=system,
                wall_after_ns=after,gate=result))+'\n')
            if gate.state=='WAITING':time.sleep(.02)
    same_boot=boot==Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    result=dict(**gate.snapshot(),same_boot=same_boot,samples=samples,max_call_span_ns=maximum_span,
        samples_sha256=digest(root/'samples.jsonl'),passed=gate.state=='READY' and same_boot,
        writes_system_settings=False,creates_ros_receivers=False,engine_attempts=0)
    (root/'result.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
    return 0 if result['passed'] else 1


if __name__=='__main__':raise SystemExit(main())
