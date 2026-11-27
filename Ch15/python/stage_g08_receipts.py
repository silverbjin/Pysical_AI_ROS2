"""Copy only known textual receipts; never upload source directory or raw bags."""
import hashlib,sys
from pathlib import Path
src,dst=map(Path,sys.argv[1:])
dst.mkdir(exist_ok=False)
allowed={'.json','.jsonl','.csv','.log','.yaml','.txt'}
lines=[];raw=[]
for p in sorted(src.rglob('*')):
    if p.is_symlink():raise ValueError('symlink rejected')
    if p.is_dir():continue
    assert p.is_file()
    rel=p.relative_to(src)
    b=p.read_bytes()
    h=hashlib.sha256(b).hexdigest()
    if p.suffix=='.mcap':
        raw.append(f'{h}  ./{rel.as_posix()}')
        continue
    if p.suffix not in allowed or p.name in ('sha256sums.txt','raw-mcap-sha256.txt'):
        raise ValueError('unexpected receipt '+str(rel))
    b.decode('utf-8')
    q=dst/rel;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    lines.append(f'{h}  ./{rel.as_posix()}')
p=dst/'raw-mcap-sha256.txt';p.write_text('\n'.join(raw)+'\n')
lines.append(f'{hashlib.sha256(p.read_bytes()).hexdigest()}  ./raw-mcap-sha256.txt')
(dst/'sha256sums.txt').write_text('\n'.join(sorted(lines))+'\n')
assert not list(dst.rglob('*.mcap'))
print('STAGED_RECEIPTS',len(lines),'RAW_MCAP_OMITTED',len(raw))
