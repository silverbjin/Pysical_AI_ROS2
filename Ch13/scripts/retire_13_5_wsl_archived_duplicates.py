"""Verify archived byte-for-byte duplicates before removing WSL copies.

Run from the repository root in WSL: python3 SCRIPT [--apply]. The archive
and all small case metadata are retained. The JSON receipt enables recovery.
"""
import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path

namespace = {}
source = Path('Ch13/scripts/restore_13_5_split_evidence.py').read_text(encoding='utf-8')
exec(source.split('ledger=json.loads')[0], namespace)
Parts, sha = namespace['Parts'], namespace['sha']
case_name = 'native-g2-mujoco-22afb6c3-a9da-4b77-ab32-ad8ec3fd1c65'
case = Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence') / case_name
files = ['observations.jsonl', 'all_frames.json', 'frames.json', 'observations.cdr',
         'native_controls.json', 'mission_probe/observations.jsonl']
expected_archive = 'aa5c1ba6698838effd427d07b799d0316ac5acb6432d1f3e52ec514d288569f6'
receipt = Path('Ch13/evidence/section_13_5/retention_wsl_archived_duplicates_20261111.json')
apply = sys.argv[1:] == ['--apply']
if sys.argv[1:] not in ([], ['--apply']):
    raise SystemExit('Use no arguments or --apply')
if apply and receipt.exists():
    raise SystemExit('Receipt already exists; refusing to overwrite')
case = case.resolve(strict=True)
assert str(case).endswith('/evidence/' + case_name)
rows = []
with Parts() as stream:
    archive_hash = sha(stream)
    if archive_hash != expected_archive:
        raise RuntimeError('Archive hash mismatch')
    stream.seek(0)
    with zipfile.ZipFile(stream) as archive:
        for name in files:
            path = case / name
            if path.is_symlink() or path.resolve(strict=True) != path or not path.is_file():
                raise RuntimeError('Unsafe target: ' + str(path))
            stat = path.stat()
            member = 'evidence/' + case_name + '/' + name
            info = archive.getinfo(member)
            if stat.st_size != info.file_size:
                raise RuntimeError('Size mismatch: ' + name)
            with path.open('rb') as f:
                disk_hash = sha(f)
            with archive.open(info) as f:
                zip_hash = sha(f)  # reading to EOF also checks ZIP CRC
            if disk_hash != zip_hash:
                raise RuntimeError('Content mismatch: ' + name)
            rows.append(dict(path=str(path), member=member, bytes=stat.st_size,
                             sha256=disk_hash, inode=stat.st_ino, mtime_ns=stat.st_mtime_ns))
            print('verified', name, stat.st_size, flush=True)
if not apply:
    print('dry run bytes:', sum(r['bytes'] for r in rows))
    raise SystemExit(0)

# Refuse files held open by any visible process. Do not signal or stop anything.
targets = {r['path'] for r in rows}
for proc in Path('/proc').iterdir():
    if not proc.name.isdigit():
        continue
    try:
        for fd in (proc / 'fd').iterdir():
            try:
                if os.readlink(fd) in targets:
                    raise RuntimeError('Target is open by PID ' + proc.name)
            except FileNotFoundError:
                pass
    except (FileNotFoundError, PermissionError):
        continue
record = dict(created_ns=time.time_ns(), archive_sha256=archive_hash,
              archive_pattern='task8-preflight-pair-g2-mujoco-22afb6c3-*.zip.part[001-008]',
              reason='byte-identical archived duplicates; pinned baseline remains recoverable',
              removed=[], verified=rows)
with receipt.open('x', encoding='utf-8') as f:
    json.dump(record, f, ensure_ascii=False, indent=2)
for row in rows:
    path = Path(row['path'])
    st = path.stat()
    if path.is_symlink() or path.resolve(strict=True) != path or (st.st_ino, st.st_size, st.st_mtime_ns) != (row['inode'], row['bytes'], row['mtime_ns']):
        raise RuntimeError('Target changed after verification: ' + str(path))
    path.unlink()
    record['removed'].append(row)
    temp = receipt.with_suffix('.tmp')
    temp.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, receipt)
    print('removed', row['path'], flush=True)
print('removed bytes:', sum(r['bytes'] for r in record['removed']))
