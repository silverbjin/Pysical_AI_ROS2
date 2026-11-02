#!/usr/bin/env python3
"""Explicit, hash-checked asset preparation; never called by a ROS node."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile
from urllib.request import urlopen

from integrated_robot_vision.detectors import verify_asset

TRUSTED_URLS = frozenset((
    'https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt',
    'https://raw.githubusercontent.com/ultralytics/ultralytics/v8.3.221/ultralytics/assets/bus.jpg',
))


def fetch_asset(spec: dict, destination: Path, opener=urlopen) -> Path:
    destination = Path(destination)
    if spec['url'] not in TRUSTED_URLS or not 0 < spec['size_bytes'] <= 32*1024*1024:
        raise ValueError('pinned official URL and bounded byte count required')
    if destination.exists():
        verify_asset(destination, spec['sha256'])
        if destination.stat().st_size != spec['size_bytes']:
            raise ValueError('cached asset size mismatch')
        return destination
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(prefix='vision-download-', dir=destination.parent,
                                          delete=False) as stream:
            temporary = Path(stream.name)
            size = 0
            with opener(spec['url'], timeout=30) as response:
                while True:
                    chunk = response.read(128*1024)
                    if not chunk:
                        break
                    size += len(chunk)
                    if size > spec['size_bytes']:
                        raise ValueError('download exceeds recorded asset size')
                    stream.write(chunk)
        verify_asset(temporary, spec['sha256'])
        if size != spec['size_bytes']:
            raise ValueError('download byte count mismatch')
        # Same-directory atomic hard-link fails rather than overwrites a race's
        # newly created cache entry. Only our own temporary file is removed.
        os.link(temporary, destination)
        return destination
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cache-dir', required=True)
    parser.add_argument('--manifest', default=str(Path(__file__).resolve().parents[1] / 'config/vision_assets.json'))
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    cache = Path(args.cache_dir).resolve()
    results = {}
    for name, spec in manifest['assets'].items():
        if name not in ('yolov8n.pt', 'bus.jpg'):
            raise ValueError('unexpected asset filename')
        path = fetch_asset(spec, cache / name)
        results[name] = dict(path=str(path), sha256=spec['sha256'], size_bytes=path.stat().st_size)
    print(json.dumps({'status': 'PASS', 'assets': results}, indent=2))


if __name__ == '__main__':
    main()
