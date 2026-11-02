"""Reversible storage compaction: ONLY untracked duplicate copies, originals retained."""
import argparse,hashlib,json,subprocess,time,uuid,zipfile
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
base=repo/'Ch13/evidence/section_13_5/85670137-e73c-4c72-bcb2-0c73e755088b'
native=Path('/home/jinho/ch13_5_completion_85670137-e73c-4c72-bcb2-0c73e755088b/evidence')
parser=argparse.ArgumentParser();parser.add_argument('--apply',action='store_true')
parser.add_argument('--limit-bytes',type=int,default=12_000_000_000);args=parser.parse_args()
def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda:source.read(4*1024*1024),b''):value.update(block)
    return value.hexdigest()
ledgers={}
for path in base.glob('*.json'):
    if path.stat().st_size>8_000_000:continue
    try:value=json.loads(path.read_text())
    except (ValueError,UnicodeError):continue
    if isinstance(value,dict) and all(key in value for key in ('members','archive','trial','sha256')):
        ledgers[value['trial']]=(path,value)
candidates=[]
for trial,(ledger,value) in ledgers.items():
    root=(base/trial).resolve()
    if root.parent!=base or not root.is_dir():continue
    for relative,identity in value['members'].items():
        prefix='evidence/'+trial+'/'
        if not relative.startswith(prefix) or identity['size']<50_000_000:continue
        name=relative[len(prefix):];copy=(root/name).resolve();original=(native/trial/name).resolve()
        if (not copy.is_relative_to(root) or not original.is_relative_to(native/trial)
                or not copy.is_file() or not original.is_file()):continue
        tracked=subprocess.run(['git','ls-files','--error-unmatch','--',str(copy.relative_to(repo))],cwd=repo,capture_output=True)
        if tracked.returncode==0:continue
        candidates.append(dict(copy=str(copy),native_original=str(original),archive=value['archive'],
            archive_sha256=value['sha256'],member=relative,**identity))
candidates.sort(key=lambda row:row['size'],reverse=True)
selected=[];total=0
for row in candidates:
    if total>=args.limit_bytes:break
    selected.append(row);total+=row['size']
candidates=selected
print(json.dumps(dict(mode='apply' if args.apply else 'dry_run',files=len(candidates),bytes=total)),flush=True)
if not args.apply:raise SystemExit(0)
report_path=base/('storage-compaction-'+str(uuid.uuid4())+'.json')
report=dict(scope='untracked_repository_duplicates_only_native_originals_and_archives_retained',
    created_at=time.time(),restoration='Extract the listed archive member; remove its evidence/ prefix to recover the repository-relative path under this evidence directory.',files=[])
verified_archives=set()
for row in candidates:
    archive=(base/row['archive']).resolve(strict=True)
    assert archive.parent==base
    if archive not in verified_archives:
        assert digest(archive)==row['archive_sha256'];verified_archives.add(archive)
    copy=Path(row['copy']);original=Path(row['native_original'])
    assert digest(copy)==digest(original)==row['sha256']
    with zipfile.ZipFile(archive) as source:
        sha=hashlib.sha256();size=0
        with source.open(row['member']) as stream:
            for block in iter(lambda:stream.read(4*1024*1024),b''):sha.update(block);size+=len(block)
        assert (size,sha.hexdigest())==(row['size'],row['sha256'])
    # Record the recovery location BEFORE removing this verified redundant copy.
    report['files'].append(dict(row,verified=True,removed=False))
    report_path.write_text(json.dumps(report,indent=2))
    copy.unlink()
    report['files'][-1]['removed']=True;report_path.write_text(json.dumps(report,indent=2))
    print('COMPACTED',copy.name,row['size'],flush=True)
print('COMPACTION_REPORT',report_path,flush=True)
