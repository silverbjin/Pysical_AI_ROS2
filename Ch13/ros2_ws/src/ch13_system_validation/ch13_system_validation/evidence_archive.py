"""Lossless case archives compatible with the existing 13.6 hash restorer."""
import fcntl,gzip,json,tarfile,uuid
from pathlib import Path
from .runtime_staging import digest

EXCLUDED={'.onnx','.pt','.pth','.mjb','.stl','.obj','.urdf','.srdf'}


def archive_case(root,folder):
    root=Path(root).resolve(strict=True);requested=Path(folder)
    if requested.is_symlink():raise ValueError('case symlink refused')
    folder=requested.resolve(strict=True);allowed=root/'Ch13/evidence/section_13_8_system'
    if folder.parent!=allowed or not folder.is_dir():raise ValueError('only explicitly named13.8 case paths')
    try:
        if str(uuid.UUID(folder.name))!=folder.name:raise ValueError('noncanonical UUID')
    except ValueError as error:raise ValueError('case UUID path required') from error
    output=folder/'raw.tar.gz';manifest=folder/'raw_manifest.json'
    if output.exists() or manifest.exists():raise ValueError('archive/manifest immutable')
    entries=sorted(folder.rglob('*'))
    if any(p.is_symlink() for p in entries):raise ValueError('evidence symlink refused')
    files=[p for p in entries if p.is_file()];rows=[]
    with (root.parent/'ch13_reuse_engine.lock').open('r+') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError as error:raise ValueError('engine busy; archive after shutdown') from error
        with output.open('xb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0,compresslevel=6) as compressed:
            with tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as archive:
                for path in files:
                    name=path.relative_to(folder).as_posix();published=path.suffix.lower() not in EXCLUDED and path.name!='planner.yaml'
                    checksum=digest(path);size=path.stat().st_size
                    rows.append(dict(path=name,bytes=size,sha256=checksum,published=published))
                    if not published:continue
                    info=archive.gettarinfo(str(path),arcname=name)
                    info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                    with path.open('rb') as source:archive.addfile(info,source)
                    if digest(path)!=checksum:raise ValueError('evidence changed during archive: '+name)
        result=dict(result='PASS',case=folder.name,archive=output.name,archive_sha256=digest(output),
            archive_bytes=output.stat().st_size,files=rows,raw_originals='preserved unchanged locally; no deletion/move')
        with manifest.open('x') as destination:destination.write(json.dumps(result,indent=2)+'\n')
    return result
