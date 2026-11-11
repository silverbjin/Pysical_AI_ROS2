"""Restore a compacted case to an existing empty directory, never in place.

Usage in WSL: python3 SCRIPT CASE_DIR EMPTY_DESTINATION
"""
import hashlib
import json
import sys
import zipfile
from pathlib import Path, PurePosixPath

if len(sys.argv) not in (3, 4) or (len(sys.argv) == 4 and sys.argv[3] != '--extra'):
    raise SystemExit('usage: SCRIPT CASE_DIR EMPTY_DESTINATION [--extra]')
case = Path(sys.argv[1]).resolve(strict=True)
destination = Path(sys.argv[2]).resolve(strict=True)
if not destination.is_dir() or any(destination.iterdir()) or destination == case or case in destination.parents:
    raise SystemExit('destination must be an existing empty directory outside the case')
receipt_name = 'retained_raw_20261111_extra.json' if len(sys.argv) == 4 else 'retained_raw_20261111.json'
receipt = json.loads((case / receipt_name).read_text(encoding='utf-8'))
archive = case / receipt['archive']
if archive.is_symlink() or archive.resolve(strict=True).parent != case:
    raise SystemExit('unsafe archive')
def digest(f):
    h = hashlib.sha256()
    for block in iter(lambda: f.read(4 * 1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()
with archive.open('rb') as f:
    if digest(f) != receipt['archive_sha256']:
        raise RuntimeError('archive hash mismatch')
with zipfile.ZipFile(archive) as z:
    for row in receipt['removed']:
        name = PurePosixPath(row['member'])
        if name.is_absolute() or '..' in name.parts:
            raise RuntimeError('unsafe member')
        target = destination.joinpath(*name.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        h = hashlib.sha256()
        with z.open(row['member']) as src, target.open('xb') as out:
            for block in iter(lambda: src.read(4 * 1024 * 1024), b''):
                h.update(block)
                out.write(block)
        if target.stat().st_size != row['bytes'] or h.hexdigest() != row['sha256']:
            raise RuntimeError('restored SHA mismatch: ' + str(name))
        print('verified', name, flush=True)
