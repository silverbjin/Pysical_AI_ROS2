"""Losslessly compact large WSL 13.5 evidence files, one case at a time.

Usage: python3 compact_13_5_wsl_evidence.py [--apply]
Without --apply only lists candidates. Output archives and receipts stay with
each case. Never touches an existing archive, symlink, or other evidence root.
"""
import hashlib
import json
import os
import sys
import time
import zipfile
from pathlib import Path

ROOT = Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
phase2 = '--phase2' in sys.argv[1:]
THRESHOLD = (4 if phase2 else 16) * 1024 * 1024
CHUNK = 4 * 1024 * 1024
ARCHIVE = 'retained_raw_20261111_extra.zip' if phase2 else 'retained_raw_20261111.zip'
RECEIPT = 'retained_raw_20261111_extra.json' if phase2 else 'retained_raw_20261111.json'
args = sys.argv[1:]
apply = '--apply' in args
if len(args) != len(set(args)) or any(x not in ('--apply', '--phase2') for x in args):
    raise SystemExit('use --apply and/or --phase2')
if ROOT.is_symlink() or ROOT.resolve(strict=True) != ROOT:
    raise SystemExit('unsafe root')

def digest(stream):
    h = hashlib.sha256()
    for block in iter(lambda: stream.read(CHUNK), b''):
        h.update(block)
    return h.hexdigest()

def safe_file(p, case):
    return not p.is_symlink() and p.is_file() and p.resolve(strict=True) == p and case in p.parents

def check_open(paths):
    targets = {str(p) for p in paths}
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        try:
            for fd in (proc / 'fd').iterdir():
                try:
                    if os.readlink(fd) in targets:
                        raise RuntimeError('target open by PID ' + proc.name)
                except FileNotFoundError:
                    pass
        except (FileNotFoundError, PermissionError):
            continue

cases = []
for case in sorted(ROOT.iterdir()):
    if case.is_symlink() or not case.is_dir() or case.resolve() != case:
        continue
    if (case / ARCHIVE).exists() or (case / RECEIPT).exists():
        continue
    files = []
    for p in case.rglob('*'):
        if not safe_file(p, case):
            continue
        extra_candidate = (p.name in {'native_command_trace.json', 'frames.json', 'all_frames.json', 'native_controls.json'} or p.suffix.lower() in {'.jsonl', '.pickle', '.capture', '.cdr', '.npy', '.npz', '.bag', '.db3', '.mcap'})
        if p.stat().st_size >= THRESHOLD and (not phase2 or extra_candidate) and p.suffix.lower() not in {'.zip', '.gz', '.xz', '.bz2', '.zst'} and '.zip.part' not in p.name:
            files.append(p)
    if files:
        cases.append((case, sorted(files)))
print('cases', len(cases), 'files', sum(len(f) for _, f in cases),
      'candidate_bytes', sum(p.stat().st_size for _, fs in cases for p in fs), flush=True)
for case, files in cases:
    print(case.name, len(files), sum(p.stat().st_size for p in files), flush=True)
if not apply:
    raise SystemExit(0)

for case, files in cases:
    check_open(files)
    archive = case / ARCHIVE
    receipt = case / RECEIPT
    rows = []
    with archive.open('xb') as output:
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6, allowZip64=True) as z:
            for path in files:
                if not safe_file(path, case):
                    raise RuntimeError('unsafe path ' + str(path))
                st = path.stat()
                name = path.relative_to(case).as_posix()
                h = hashlib.sha256()
                with path.open('rb') as src, z.open(name, 'w', force_zip64=True) as dst:
                    for block in iter(lambda: src.read(CHUNK), b''):
                        h.update(block)
                        dst.write(block)
                rows.append(dict(member=name, bytes=st.st_size, sha256=h.hexdigest(),
                                 inode=st.st_ino, mtime_ns=st.st_mtime_ns))
                print('packed', case.name, name, flush=True)
    with zipfile.ZipFile(archive) as z:
        for row in rows:
            with z.open(row['member']) as f:
                if digest(f) != row['sha256']:
                    raise RuntimeError('archive SHA mismatch: ' + row['member'])
    with archive.open('rb') as f:
        archive_hash = digest(f)
    check_open(files)
    # Verify disk bytes again after archiving; all checks precede any unlink.
    for row in rows:
        path = case / row['member']
        if not safe_file(path, case):
            raise RuntimeError('unsafe target ' + str(path))
        st = path.stat()
        if (st.st_ino, st.st_size, st.st_mtime_ns) != (row['inode'], row['bytes'], row['mtime_ns']):
            raise RuntimeError('target changed: ' + str(path))
        with path.open('rb') as f:
            if digest(f) != row['sha256']:
                raise RuntimeError('target SHA changed: ' + str(path))
    data = dict(version=1, created_ns=time.time_ns(), case=str(case), archive=ARCHIVE,
                archive_bytes=archive.stat().st_size, archive_sha256=archive_hash,
                verified=rows, removed=[])
    with receipt.open('x', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    for row in rows:
        path = case / row['member']
        st = path.stat()
        if not safe_file(path, case) or (st.st_ino, st.st_size, st.st_mtime_ns) != (row['inode'], row['bytes'], row['mtime_ns']):
            raise RuntimeError('target changed before deletion: ' + str(path))
        path.unlink()
        data['removed'].append(row)
        temp = case / (RECEIPT + '.tmp')
        temp.write_text(json.dumps(data, indent=2), encoding='utf-8')
        os.replace(temp, receipt)
    print('complete', case.name, 'removed_bytes', sum(r['bytes'] for r in rows),
          'archive_bytes', archive.stat().st_size, flush=True)
