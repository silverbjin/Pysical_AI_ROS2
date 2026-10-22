#!/usr/bin/env python3
"""Create an offline-only navigation variant; never marks native validation."""
import argparse
from dataclasses import asdict
import json
from pathlib import Path

import xacro

from integrated_robot_navigation.carry_profile import prepare_profile
from integrated_robot_navigation.geometry import description_dir, navigation_mjcf
from integrated_robot_navigation.model import compile_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True)
    parser.add_argument('--urdf', help='Exact per-engine generated URDF; default is the offline mock variant')
    parser.add_argument('--arm', type=float, nargs=6, default=(0., 1.2, -2., 0., .8, 0.))
    args = parser.parse_args()
    output = Path(args.output_dir).resolve()
    if output.exists():
        parser.error('output directory already exists; refusing overwrite')
    if args.urdf:
        urdf = Path(args.urdf).read_text()
    else:
        urdf = xacro.process_file(str(description_dir()/'urdf/robot_system.urdf.xacro'),
                                 mappings={'hip_mount_y': '0.13'}).toxml()
    model = compile_model(urdf)
    profile = prepare_profile(model, tuple(args.arm))
    output.mkdir(parents=True, exist_ok=False)
    (output/'robot.urdf').write_text(urdf, encoding='utf-8')
    (output/'robot.mjcf').write_text(navigation_mjcf(model), encoding='utf-8')
    (output/'carry_profile.json').write_text(
        json.dumps(asdict(profile), ensure_ascii=False, indent=2, allow_nan=False)+'\n',
        encoding='utf-8')
    (output/'README.md').write_text(
        '# 오프라인 후보\n\n실제 엔진 G1 증거가 없으므로 CRAWL을 허용하지 않습니다.\n',
        encoding='utf-8')
    print(json.dumps(dict(state=profile.state, model_sha256=profile.model_sha256,
                          config_sha256=profile.config_sha256, output=str(output))))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
