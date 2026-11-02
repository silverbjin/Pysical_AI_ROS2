"""Post-reap archive sources. Never deletes native originals or changes verdicts."""
import hashlib,json,os,shutil
from pathlib import Path

def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(4*1024*1024),b''):value.update(block)
    return value.hexdigest()

def bounded_original(original,native_base,name):
    original=Path(original);native_base=Path(native_base).resolve(strict=True)
    if (original.is_symlink() or original.resolve(strict=True).parent!=native_base
            or original.name!=name or original.stat().st_uid!=os.getuid()):
        raise RuntimeError('native source outside owned evidence root')
    return original.resolve()

def export_closed(original,destination,native_base,*,archive_large=False,threshold=50_000_000):
    original,destination=Path(original),Path(destination)
    original=bounded_original(original,native_base,destination.name)
    closed=json.loads((original/'teardown.json').read_text())
    result=json.loads((original/'result.json').read_text())
    if (closed.get('parent_reaped') is not True and result.get('engine_started') is not False
            or closed.get('residual_live_pids')!=[]):
        raise RuntimeError('owned cleanup unconfirmed; no export')
    if destination.exists():raise RuntimeError('destination exists; no overwrite')
    paths=sorted(original.rglob('*'))
    if any(p.is_symlink() or not p.resolve().is_relative_to(original) for p in paths):
        raise RuntimeError('native evidence symlink/path escape')
    destination.mkdir();files={};skipped=[]
    for path in paths:
        if not path.is_file():continue
        relative=str(path.relative_to(original));files[relative]=digest(path)
        if archive_large and path.stat().st_size>threshold:
            skipped.append(relative);continue
        copied=destination/relative;copied.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(path,copied)
        if digest(copied)!=files[relative]:raise RuntimeError('copied bytes differ')
    return dict(kind='native_original_and_verified_small_copy_pending_full_archive' if archive_large else
        'byte_exact_copy_native_original_retained',archive_from_native=archive_large,
        native_original=str(original),files=files,not_duplicated=skipped)


def canonical_result(root,native_base):
    """Resolve exact original metadata; the caller still runs full admission.

    A thin publication copy deliberately lacks raw siblings. Never fabricate
    missing artifacts, relax the product validator or treat this pointer as PASS.
    """
    root=Path(root)
    if root.is_symlink():raise RuntimeError('evidence copy path is a symlink')
    ledger=json.loads((root/'storage-copy-ledger.json').read_text())
    if ledger.get('archive_from_native') is not True:
        raise RuntimeError('canonical evidence descriptor required')
    original=bounded_original(Path(ledger['native_original']),native_base,root.name)
    for name in ('result.json','source_manifest.json','install_manifest.json','teardown.json'):
        copied,native=root/name,original/name
        expected=ledger['files'][name]
        if (copied.is_symlink() or native.is_symlink()
                or native.resolve(strict=True).parent!=original
                or digest(copied)!=expected or digest(native)!=expected):
            raise RuntimeError('canonical binding metadata changed: '+name)
    return original/'result.json'

def archive_sources(root,native_base):
    root=Path(root);ledger_path=root/'storage-copy-ledger.json'
    ledger=json.loads(ledger_path.read_text())
    if not ledger.get('archive_from_native'):raise RuntimeError('not an opted-in native archive')
    original=bounded_original(Path(ledger['native_original']),native_base,root.name)
    actual={str(p.relative_to(original)) for p in original.rglob('*') if p.is_file()}
    if actual!=set(ledger['files']):raise RuntimeError('native artifact inventory changed')
    records=[]
    for name,expected in ledger['files'].items():
        path=original/name
        if path.is_symlink() or not path.resolve().is_relative_to(original):raise RuntimeError('artifact path escape')
        copied=root/name
        if copied.exists() and digest(copied)!=expected:raise RuntimeError('small copy changed')
        # Full streaming archive add verifies this expected original SHA.
        records.append((path,name,expected))
    records.append((ledger_path,'storage-copy-ledger.json',digest(ledger_path)))
    return records
