"""Archive explicitly named 13.7 cases; preserve raw files and omit models."""
import gzip,hashlib,json,sys,tarfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXCLUDED={'.onnx','.pt','.pth','.mjb','.stl','.obj','.urdf','.srdf'}


def archive(folder):
    folder=Path(folder).resolve()
    if folder.parent!=(ROOT/'Ch13/evidence/section_13_7_bt').resolve() or not folder.is_dir():
        raise ValueError('only explicitly named13.7 evidence folders')
    output=folder/'raw.tar.gz';manifest=folder/'raw_manifest.json'
    if output.exists() or manifest.exists():raise ValueError('archive immutable')
    files=sorted(p for p in folder.rglob('*') if p.is_file());rows=[]
    with output.open('xb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as compressed:
        with tarfile.open(fileobj=compressed,mode='w') as tar:
            for p in files:
                if p.is_symlink():raise ValueError('evidence symlink')
                name=p.relative_to(folder).as_posix();publish=p.suffix.lower() not in EXCLUDED and p.name!='planner.yaml'
                rows.append(dict(path=name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size,published=publish))
                if publish:
                    info=tar.gettarinfo(str(p),arcname=name);info.uid=info.gid=0;info.uname=info.gname='';info.mtime=0
                    with p.open('rb') as src:tar.addfile(info,src)
    manifest.write_text(json.dumps(dict(archive=output.name,archive_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),files=rows),indent=2)+'\n')
    relative=folder.relative_to(ROOT).as_posix()
    with (ROOT/'.gitignore').open('a') as target:target.write(f'\n/{relative}/**\n!/{relative}/raw.tar.gz\n!/{relative}/raw_manifest.json\n')
    print(folder.name,len(rows),output.stat().st_size)


if __name__=='__main__':
    for value in sys.argv[1:]:archive(value)
