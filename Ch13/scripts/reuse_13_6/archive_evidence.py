"""Publish lossless evidence archives; retain raw originals, exclude models."""
import gzip
import hashlib
import json
import sys
import tarfile
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
EXCLUDED={'.onnx','.pt','.pth','.mjb','.stl','.obj','.urdf','.srdf'}


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def archive(folder):
    folder=Path(folder).resolve();allowed=(ROOT/'Ch13/evidence/section_13_6_reuse').resolve()
    assert folder.parent==allowed and folder.is_dir(),'only explicitly named13.6 case folders'
    output=folder/'raw.tar.gz';manifest=folder/'raw_manifest.json'
    if output.exists() or manifest.exists():raise ValueError('archive/manifest immutable; already published')
    files=sorted(p for p in folder.rglob('*') if p.is_file())
    assert all(not p.is_symlink() for p in files),'no evidence symlinks'
    rows=[]
    with output.open('xb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0,compresslevel=6) as compressed:
        with tarfile.open(fileobj=compressed,mode='w',format=tarfile.PAX_FORMAT) as tar:
            for path in files:
                name=path.relative_to(folder).as_posix()
                exclude=path.suffix.lower() in EXCLUDED or path.name=='planner.yaml'
                rows.append(dict(path=name,bytes=path.stat().st_size,sha256=digest(path),local_path=str(path),
                                 published=not exclude,exclusion='model/weights or embedded generated description' if exclude else None))
                if exclude:continue
                info=tar.gettarinfo(str(path),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                with path.open('rb') as source:tar.addfile(info,source)
    value=dict(result='PASS',created_utc=datetime.now(timezone.utc).isoformat(),case=folder.name,
               raw_originals='preserved unchanged locally; no deletion/move',archive=output.name,archive_sha256=digest(output),
               archive_bytes=output.stat().st_size,files=rows)
    manifest.write_text(json.dumps(value,indent=2)+'\n')
    relative=folder.relative_to(ROOT).as_posix();patterns=f'\n/{relative}/**\n!/{relative}/raw.tar.gz\n!/{relative}/raw_manifest.json\n'
    ignore=ROOT/'.gitignore';current=ignore.read_text()
    if f'/{relative}/**' not in current:
        with ignore.open('a') as target:target.write(patterns)
    return dict(case=folder.name,files=len(rows),archive_bytes=output.stat().st_size,sha256=value['archive_sha256'])


if __name__=='__main__':print(json.dumps([archive(folder) for folder in sys.argv[1:]],indent=2))
