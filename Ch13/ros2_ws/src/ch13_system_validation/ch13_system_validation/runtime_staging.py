"""Exact-byte native runtime staging with the original shared assets and lock."""
import hashlib,json,uuid
from pathlib import Path,PurePosixPath
from .tools import validate_build


def digest(path):
    result=hashlib.sha256()
    with Path(path).open('rb') as source:
        for chunk in iter(lambda:source.read(1024*1024),b''):result.update(chunk)
    return result.hexdigest()


def relative_path(name):
    path=PurePosixPath(name)
    if not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name:
        raise ValueError('invalid manifest path: '+name)
    return Path(*path.parts)


def stage_runtime(root,manifest,build):
    root=Path(root).resolve(strict=True);manifest=Path(manifest).resolve(strict=True)
    if not manifest.is_relative_to(root):raise ValueError('manifest path outside source root')
    manifest_relative=manifest.relative_to(root);payload=manifest.read_bytes();data=json.loads(payload)
    if not isinstance(data.get('source'),dict) or not data['source']:raise ValueError('empty source manifest')
    assets=(root.parent/'upstream-iit-locomanipulation-d010212').resolve(strict=True)
    lock=(root.parent/'ch13_reuse_engine.lock').resolve(strict=True)
    if not assets.is_dir() or not lock.is_file():raise ValueError('shared asset/lock path invalid')
    sources=[]
    for name,want in data['source'].items():
        relative=relative_path(name);path=root/relative
        if relative==manifest_relative:raise ValueError('manifest path cannot include itself')
        if path.is_symlink() or not path.resolve().is_relative_to(root):raise ValueError('source path symlink/escape')
        if digest(path)!=want:raise ValueError('source hash mismatch: '+name)
        sources.append((relative,want))
    for asset in data['assets']:
        path=assets/relative_path(asset['path'])
        if not path.resolve().is_relative_to(assets) or digest(path)!=asset['sha256']:
            raise ValueError('asset hash/path mismatch: '+asset['path'])
    build=validate_build(build)
    if build==root or build in root.parents or root in build.parents:raise ValueError('build overlaps source path')
    staging=build/('live_source_'+uuid.uuid4().hex);runtime=staging/'repo';runtime.mkdir(parents=True)
    for relative,want in sources:
        target=runtime/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with (root/relative).open('rb') as source,target.open('xb') as destination:
            for chunk in iter(lambda:source.read(1024*1024),b''):destination.write(chunk)
        if digest(target)!=want:raise ValueError('copied source hash mismatch: '+str(relative))
    for name,original in (('upstream-iit-locomanipulation-d010212',assets),('ch13_reuse_engine.lock',lock)):
        link=staging/name;link.symlink_to(original,target_is_directory=original.is_dir())
        if link.resolve(strict=True)!=original:raise ValueError('shared realpath mismatch')
    target=runtime/manifest_relative;target.parent.mkdir(parents=True,exist_ok=True)
    with target.open('xb') as destination:destination.write(payload)
    result=dict(result='PASS',source_root=str(root),runtime_root=str(runtime),source_files=len(sources),
        manifest_relative_path=manifest_relative.as_posix(),source_manifest_sha256=hashlib.sha256(payload).hexdigest(),
        assets=len(data['assets']),assets_realpath=str(assets),shared_lock_realpath=str(lock),
        scope='exact-byte runtime staging only; no engine execution')
    with (staging/'source_stage.json').open('x') as out:out.write(json.dumps(result,indent=2)+'\n')
    return result
