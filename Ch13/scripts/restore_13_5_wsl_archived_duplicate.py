"""Restore one recorded duplicate to a new file: SCRIPT MEMBER_RELATIVE DEST."""
import json
import sys
import zipfile
from pathlib import Path

namespace = {}
source = Path('Ch13/scripts/restore_13_5_split_evidence.py').read_text(encoding='utf-8')
exec(source.split('ledger=json.loads')[0], namespace)
Parts, sha = namespace['Parts'], namespace['sha']
receipt = json.loads(Path('Ch13/evidence/section_13_5/retention_wsl_archived_duplicates_20261111.json').read_text(encoding='utf-8'))
if len(sys.argv) != 3:
    raise SystemExit('usage: SCRIPT MEMBER_RELATIVE DESTINATION_FILE')
matches = [r for r in receipt['removed'] if r['member'].endswith('/' + sys.argv[1])]
if len(matches) != 1:
    raise SystemExit('Member must identify exactly one removed file')
row = matches[0]
destination = Path(sys.argv[2])
with Parts() as stream:
    if sha(stream) != receipt['archive_sha256']:
        raise RuntimeError('Archive hash mismatch')
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        with archive.open(row['member']) as src, destination.open('xb') as dst:
            import hashlib
            h = hashlib.sha256()
            for block in iter(lambda: src.read(4 * 1024 * 1024), b''):
                h.update(block)
                dst.write(block)
if destination.stat().st_size != row['bytes'] or h.hexdigest() != row['sha256']:
    raise RuntimeError('Restored file mismatch; do not use it')
print('Verified:', destination, h.hexdigest())
