"""Strict local archive verifier (never extracts). No ROS dependency."""
import argparse,hashlib,io,json,re,sys,tarfile
from pathlib import Path,PurePosixPath
def digest(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()
def valid_name(n):
    p=PurePosixPath(n)
    return bool(n) and n==p.as_posix() and not p.is_absolute() and '..' not in p.parts and '.' not in p.parts and not any(c in n for c in ('\\','\n','\r','\x00'))
def read_manifest(data):
    out={}
    for line in data.decode('utf-8').splitlines():
        h,sep,n=line.partition('  ')
        if not sep or not re.fullmatch('[a-f0-9]{64}',h) or not valid_name(n) or n=='manifest.sha256' or n in out:raise ValueError('invalid manifest entry')
        out[n]=h
    if not out:raise ValueError('empty manifest')
    return out
def verify(archive,sidecar):
    a=Path(archive);s=Path(sidecar)
    expected=s.read_text().strip().split('  ')
    if len(expected)!=2 or expected[1]!=a.name or not re.fullmatch('[a-f0-9]{64}',expected[0]) or digest(a)!=expected[0]:raise ValueError('ARCHIVE_SHA_DRIFT')
    got={};manifest=None;total=0
    with tarfile.open(a,'r:gz') as tar:
        for m in tar:
            if not m.isfile() or not valid_name(m.name) or m.name in got or (m.name=='manifest.sha256' and manifest is not None):raise ValueError('UNSAFE_ARCHIVE_MEMBER')
            total+=m.size
            if total>8*1024**3 or len(got)>20000:raise ValueError('archive budget exceeded')
            f=tar.extractfile(m)
            if m.name=='manifest.sha256':
                if m.size>8*1024**2:raise ValueError('manifest too large')
                manifest=read_manifest(f.read());continue
            h=hashlib.sha256()
            for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
            got[m.name]=h.hexdigest()
    if manifest is None or got!=manifest:raise ValueError('INTERNAL_HASH_OR_MEMBERSHIP_DRIFT')
    for n in ('owner-result.json','source-receipt.json','environment.json','process_audit.json'):
        if n not in got:raise ValueError('MISSING_REQUIRED_RECEIPT:'+n)
    return dict(result='PASS',archive_sha256=expected[0],verified_files=len(got),bytes=total)
def main():
    p=argparse.ArgumentParser();p.add_argument('archive');p.add_argument('sidecar');a=p.parse_args()
    try:print(json.dumps(verify(a.archive,a.sidecar)));return 0
    except Exception as e:print(json.dumps(dict(result='FAIL',reason=str(e))));return 1
if __name__=='__main__':sys.exit(main())
