"""Verify or acquire only pinned upstream YOLO files; never load a checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

MODEL_IDS = ('yolov8n', 'yolov8s')
REVISION = 'a335eb8d58ded1464e0ff09b3994fc8ae0e6f8fe'


def resolve_entry(manifest, model_id):
    if model_id not in MODEL_IDS:
        raise ValueError('unapproved model id')
    matches = [e for e in manifest['models'] if e['id'] == model_id]
    if len(matches) != 1:
        raise ValueError('missing or ambiguous manifest entry')
    entry = matches[0]
    url = f'https://huggingface.co/Ultralytics/YOLOv8/resolve/{REVISION}/{model_id}.pt'
    if (entry.get('source_url') != url or entry.get('source_revision') != REVISION or
            not re.fullmatch(r'[0-9a-f]{64}', entry.get('sha256') or '') or
            entry.get('license') != 'AGPL-3.0'):
        raise ValueError('invalid pinned publisher contract')
    return entry


def verify_file(path, expected):
    if path.is_symlink() or not path.is_file():
        raise ValueError('regular model file required')
    with path.open('rb') as f:
        actual = hashlib.file_digest(f, 'sha256').hexdigest()
    if actual != expected:
        raise ValueError(f'model SHA256 mismatch: {path.name}, expected={expected}, actual={actual}')
    return actual


def acquire(entry, cache, *, fetch=False, acknowledged=False):
    path = cache / f"{entry['id']}.pt"
    if path.exists() or path.is_symlink():
        return path, verify_file(path, entry['sha256'])
    if not fetch:
        raise FileNotFoundError(f'model missing: {path}')
    if not acknowledged:
        raise PermissionError('explicit AGPL acknowledgement required; does not establish distribution rights')
    cache.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.ch14-model-', dir=cache) as tmp:
        candidate = Path(tmp) / path.name
        subprocess.run(['curl', '--fail', '--silent', '--show-error', '--location',
                        '--proto', '=https', '--proto-redir', '=https', '--connect-timeout', '20',
                        '--max-time', '180', '--output', str(candidate), entry['source_url']], check=True)
        digest = verify_file(candidate, entry['sha256'])
        # Exclusive creation: never replace an existing model, including concurrent arrivals.
        try:
            import os
            os.link(candidate, path)
        except FileExistsError:
            verify_file(path, entry['sha256'])
    return path, digest


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('model_id', choices=MODEL_IDS)
    p.add_argument('--cache', required=True, type=Path)
    p.add_argument('--fetch', action='store_true')
    p.add_argument('--acknowledge-agpl', action='store_true')
    a = p.parse_args()
    manifest_path = Path(__file__).resolve().parents[1] / 'models/model_manifest.json'
    entry = resolve_entry(json.loads(manifest_path.read_text()), a.model_id)
    path, digest = acquire(entry, a.cache, fetch=a.fetch, acknowledged=a.acknowledge_agpl)
    print(json.dumps(dict(status='HASH_VERIFIED', model_id=a.model_id, path=str(path.resolve()),
                          sha256=digest, checkpoint_loaded=False, release_rights='NOT_APPROVED')))


if __name__ == '__main__':
    main()
