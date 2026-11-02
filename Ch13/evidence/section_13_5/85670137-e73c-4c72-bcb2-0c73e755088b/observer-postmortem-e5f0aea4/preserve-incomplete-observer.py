"""Preserve a failed, incomplete run verbatim; never synthesize teardown/PASS."""
import hashlib,json,os,shutil,subprocess,sys,time,uuid,zipfile
from pathlib import Path

repo=Path(__file__).resolve().parents[3]
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence/native-g2-mujoco-e5f0aea4-bbea-427d-8d25-f020bfbe78fd')
target=base/('incomplete-observer-recovery-'+str(uuid.uuid4()));target.mkdir()
print('RECOVERY',target,flush=True)
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(4*1024*1024),b''):value.update(block)
    return value.hexdigest()
inspection=subprocess.run([sys.executable,str(Path(__file__).with_name('inspect-interrupted-native.py'))],capture_output=True,text=True)
(target/'recovery-inventory.log').write_text(inspection.stdout+inspection.stderr)
assert inspection.returncode==0
assert 'OWNED_RELATED_PROCESSES []' in inspection.stdout
manifest=json.loads((native/'source_manifest.json').read_text())
files={}
def copy(source,relative,expected=None):
    output=target/relative;output.parent.mkdir(parents=True,exist_ok=True)
    assert not output.exists()
    shutil.copyfile(source,output)
    sha=digest(source);assert digest(output)==sha
    assert expected is None or sha==expected,(source,sha,expected)
    files[relative]=dict(size=output.stat().st_size,sha256=sha)
    if output.stat().st_size>50_000_000:print('COPIED',relative,output.stat().st_size,flush=True)
for path in sorted(native.rglob('*')):
    if path.is_file():copy(path,'original/'+str(path.relative_to(native)))
copy(native.parent/'g2-driver-e5f0aea4-bbea-427d-8d25-f020bfbe78fd.log','g2-driver-original.log')
for relative,sha in manifest['files'].items():copy(repo/relative,'sources/'+relative,sha)
test_root=repo/'Ch13/ros2_ws/src/integrated_robot_navigation/test'
for path in sorted(test_root.rglob('*.py')):copy(path,'tests/'+str(path.relative_to(test_root)))
services={key:subprocess.run(['systemctl',key,'systemd-timesyncd.service'],capture_output=True,text=True).stdout.strip() for key in ('is-active','is-enabled')}
report=dict(schema=1,uuid=target.name,created_at=time.time(),source_native=str(native),
    boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
    original_status=json.loads((native/'result.json').read_text())['status'],
    original_teardown_exists=(native/'teardown.json').exists(),
    normal_shutdown_confirmed=False,original_result_promoted=False,
    residual_inventory='recovery-inventory.log',service=services,files=files)
(target/'preservation.json').write_text(json.dumps(report,indent=2))
archive=target.with_suffix('.zip')
with zipfile.ZipFile(archive,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6,allowZip64=True) as output:
    for path in sorted(target.rglob('*')):
        if path.is_file():output.write(path,str(path.relative_to(target)))
with zipfile.ZipFile(archive) as check:
    for relative,identity in files.items():
        sha=hashlib.sha256();size=0
        with check.open(relative) as source:
            for block in iter(lambda:source.read(4*1024*1024),b''):sha.update(block);size+=len(block)
        assert (size,sha.hexdigest())==(identity['size'],identity['sha256']),relative
archive_report=dict(size=archive.stat().st_size,sha256=digest(archive),members_verified=True,parts=[])
if archive.stat().st_size>=95_000_000:
    with archive.open('rb') as source:
        number=0
        while True:
            block=source.read(72_000_000)
            if not block:break
            number+=1;part=archive.with_name(archive.name+f'.part{number:03d}')
            with part.open('xb') as output:output.write(block)
            archive_report['parts'].append(dict(name=part.name,size=len(block),sha256=digest(part)))
    archive_report['original_archive_local_only']=True
target.with_suffix('.json').write_text(json.dumps(archive_report,indent=2))
print(json.dumps(dict(recovery=str(target),archive=archive_report)),flush=True)
