"""Hash-verified source preservation from the actual immutable native snapshot."""
import gzip,hashlib,io,json,sys,tarfile
from pathlib import Path
from ch13_system_validation.runtime_staging import digest,relative_path
case=Path(sys.argv[1]);runtime=Path(sys.argv[2]);label=sys.argv[3]
manifest=json.loads((case/'source_manifest.json').read_text());target=case/label;target.mkdir()
archive=target/'runtime_source.tar.gz'
with archive.open('xb') as raw,gzip.GzipFile(filename='',fileobj=raw,mode='wb',mtime=0) as compressed:
    with tarfile.open(fileobj=compressed,mode='w') as tar:
        for name,want in sorted(manifest['source'].items()):
            data=(runtime/relative_path(name)).read_bytes();assert hashlib.sha256(data).hexdigest()==want,name
            info=tarfile.TarInfo(name);info.size=len(data);info.mode=0o644;info.mtime=0;tar.addfile(info,io.BytesIO(data))
result=dict(result='PASS',source_files=len(manifest['source']),runtime_root=str(runtime),
    source_manifest_sha256=digest(case/'source_manifest.json'),sha256=digest(archive),
    meaning='hash-matching bytes from actual native source; post-exit preservation, not new execution; models excluded')
with (target/'verification.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
